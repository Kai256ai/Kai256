"""WorldPuzzle360 spatial-temporal reconstruction engine.

The engine keeps observations, hypotheses, evidence and conclusions distinct by
storing provenance and confidence changes instead of inferring intent.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def parse_fuzzy_date(date_str: str) -> Optional[datetime]:
    """Parse ISO, ``YYYY-MM`` and English ``Month YYYY`` dates as UTC."""
    if not date_str or not date_str.strip():
        return None
    value = date_str.strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
    except ValueError:
        pass

    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), 1, tzinfo=timezone.utc)
        except ValueError:
            return None

    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
        "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12, "jan": 1, "feb": 2, "mar": 3,
        "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
        "nov": 11, "dec": 12,
    }
    match = re.fullmatch(r"([a-zA-Z]+)\s+(\d{4})", value)
    if match and match.group(1).lower() in months:
        return datetime(int(match.group(2)), months[match.group(1).lower()], 1,
                        tzinfo=timezone.utc)
    return None


def temporal_distance_in_days(d1: Optional[datetime], d2: Optional[datetime]) -> Optional[float]:
    if d1 is None or d2 is None:
        return None
    if d1.tzinfo is None:
        d1 = d1.replace(tzinfo=timezone.utc)
    if d2.tzinfo is None:
        d2 = d2.replace(tzinfo=timezone.utc)
    return abs((d1 - d2).total_seconds()) / 86400.0


class FragmentStatus(str, Enum):
    OBSERVED = "observed"
    RECONSTRUCTED = "reconstructed"
    HYPOTHESIS = "hypothesis"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"


class RelationStatus(str, Enum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"


class EntityRegistry:
    """Case-insensitive, O(1) canonical entity registry."""

    def __init__(self) -> None:
        self._canonical: dict[str, str] = {}
        self._lower_index: dict[str, str] = {}
        self._aliases: dict[str, set[str]] = {}
        self._next_id = 1

    def get_or_create(self, name: str) -> str:
        name = name.strip()
        if not name:
            return "unknown"
        if name in self._canonical:
            return self._canonical[name]
        key = name.casefold()
        canonical_id = self._lower_index.get(key)
        if canonical_id is None:
            canonical_id = f"E{self._next_id:04d}"
            self._next_id += 1
            self._lower_index[key] = canonical_id
            self._aliases[canonical_id] = set()
        self._canonical[name] = canonical_id
        self._aliases[canonical_id].add(name)
        return canonical_id

    def get_canonical(self, name: str) -> Optional[str]:
        return self._lower_index.get(name.strip().casefold())

    def resolve_fragment_entities(self, fragment: "PuzzleFragment") -> list[str]:
        return [self.get_or_create(entity) for entity in fragment.entities]


@dataclass
class SourceRef:
    source_id: str
    source_type: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: str = field(default_factory=utc_now)
    independence_group: Optional[str] = None
    domain: Optional[str] = None

    def __post_init__(self) -> None:
        if self.url and not self.domain:
            self.domain = urlparse(self.url).netloc.casefold() or None


@dataclass
class PuzzleFragment:
    claim: str
    sources: list[SourceRef]
    event_type: str = "event"
    entities: list[str] = field(default_factory=list)
    geo: list[str] = field(default_factory=list)
    timestamp_event: Optional[str] = None
    timestamp_publication: Optional[str] = None
    flow_type: Optional[str] = None
    observer: str = "unknown"
    confidence: float = 0.5
    alternative_explanations: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    status: FragmentStatus = FragmentStatus.OBSERVED
    fragment_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    confidence_history: list[dict[str, Any]] = field(default_factory=list)
    _canonical_entities: list[str] = field(default_factory=list, init=False,
                                                 repr=False, compare=False)

    def __post_init__(self) -> None:
        self.confidence = clamp01(self.confidence)
        if not self.confidence_history:
            self.confidence_history.append({"t": self.created_at,
                                            "confidence": self.confidence,
                                            "reason": "initial"})

    def canonical_entities(self, registry: EntityRegistry) -> list[str]:
        if not self._canonical_entities:
            self._canonical_entities = registry.resolve_fragment_entities(self)
        return list(self._canonical_entities)


@dataclass
class MissingPuzzle:
    description: str
    category: str
    related_fragment_ids: list[str] = field(default_factory=list)
    related_edge_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    missing_id: str = field(default_factory=lambda: str(uuid4()))

    def resolve(self, by: str) -> None:
        self.resolved_at = utc_now()
        self.resolved_by = by


@dataclass
class RelationEdge:
    source_fragment: str
    target_fragment: str
    relation_type: str
    proposed_by: str
    confidence: float = 0.4
    status: RelationStatus = RelationStatus.PROPOSED
    support_notes: list[str] = field(default_factory=list)
    falsification_notes: list[str] = field(default_factory=list)
    alternative_explanations: list[str] = field(default_factory=list)
    temporal_fit: Optional[float] = None
    geo_fit: Optional[float] = None
    entity_fit: Optional[float] = None
    edge_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    confidence_history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.confidence = clamp01(self.confidence)
        if not self.confidence_history:
            self.confidence_history.append({"t": self.created_at,
                                            "confidence": self.confidence,
                                            "reason": "initial"})


class WorldPuzzle360:
    """In-memory graph of sourced fragments, cautious relations and gaps."""

    def __init__(self) -> None:
        self.fragments: dict[str, PuzzleFragment] = {}
        self.edges: dict[str, RelationEdge] = {}
        self.missing: dict[str, MissingPuzzle] = {}
        self.entity_registry = EntityRegistry()

    def add_fragment(self, fragment: PuzzleFragment) -> str:
        fragment._canonical_entities = self.entity_registry.resolve_fragment_entities(fragment)
        self.fragments[fragment.fragment_id] = fragment
        return fragment.fragment_id

    def add_missing(self, missing: MissingPuzzle) -> str:
        self.missing[missing.missing_id] = missing
        return missing.missing_id

    def _entity_overlap(self, a: PuzzleFragment, b: PuzzleFragment) -> float:
        left = set(a.canonical_entities(self.entity_registry))
        right = set(b.canonical_entities(self.entity_registry))
        return len(left & right) / len(left | right) if left and right else 0.0

    @staticmethod
    def _geo_overlap(a: PuzzleFragment, b: PuzzleFragment) -> float:
        left = {value.casefold() for value in a.geo}
        right = {value.casefold() for value in b.geo}
        return len(left & right) / len(left | right) if left and right else 0.0

    @staticmethod
    def _temporal_fit(a: PuzzleFragment, b: PuzzleFragment) -> float:
        da = parse_fuzzy_date(a.timestamp_event or "")
        db = parse_fuzzy_date(b.timestamp_event or "")
        da = da or parse_fuzzy_date(a.timestamp_publication or "")
        db = db or parse_fuzzy_date(b.timestamp_publication or "")
        days = temporal_distance_in_days(da, db)
        return 0.5 if days is None else clamp01(1.0 - (days / 365.0) * 0.95)

    @staticmethod
    def _source_independence_score(fragment: PuzzleFragment) -> float:
        if not fragment.sources:
            return 0.0
        groups = {(source.independence_group or "", source.domain or source.source_id)
                  for source in fragment.sources}
        base = min(1.0, len(groups) / 3.0)
        domains = [source.domain for source in fragment.sources if source.domain]
        if len(domains) > 1:
            dominance = Counter(domains).most_common(1)[0][1] / len(domains)
            if dominance > 0.5:
                base *= max(0.3, 1.0 - (dominance - 0.5))
        return base

    def propose_relation(self, source_id: str, target_id: str, relation_type: str,
                         proposed_by: str, note: str = "") -> Optional[str]:
        if source_id not in self.fragments or target_id not in self.fragments:
            return None
        a, b = self.fragments[source_id], self.fragments[target_id]
        entity_fit = self._entity_overlap(a, b)
        geo_fit = self._geo_overlap(a, b)
        temporal_fit = self._temporal_fit(a, b)
        confidence = clamp01(0.15 + 0.25 * entity_fit + 0.20 * geo_fit
                             + 0.20 * temporal_fit)
        src_ind_a = self._source_independence_score(a)
        src_ind_b = self._source_independence_score(b)
        if src_ind_a < 0.3 and src_ind_b < 0.3:
            confidence = min(confidence, 0.35)
        edge = RelationEdge(source_id, target_id, relation_type, proposed_by,
                            confidence, support_notes=[f"[{proposed_by}] {note}"] if note else [],
                            temporal_fit=temporal_fit, geo_fit=geo_fit, entity_fit=entity_fit)
        self.edges[edge.edge_id] = edge

        weak_dimensions: list[tuple[str, str]] = []
        if src_ind_a < 0.4 and src_ind_b < 0.4:
            weak_dimensions.append(("independence", "Low source independence for both "
                                    f"fragments (a={src_ind_a:.2f}, b={src_ind_b:.2f})"))
        if temporal_fit < 0.3:
            weak_dimensions.append(("temporal", f"Weak temporal alignment ({temporal_fit:.2f})"))
        if entity_fit < 0.2:
            weak_dimensions.append(("entity", f"Almost no shared entities ({entity_fit:.2f})"))
        if geo_fit < 0.2:
            weak_dimensions.append(("geo", f"Almost no shared geography ({geo_fit:.2f})"))
        for category, description in weak_dimensions:
            self.add_missing(MissingPuzzle(
                f"{description} (relation {source_id}->{target_id})", category,
                [source_id, target_id], [edge.edge_id]))
        return edge.edge_id

    def support_relation(self, edge_id: str, agent: str, note: str,
                         boost: float = 0.08) -> bool:
        edge = self.edges.get(edge_id)
        if edge is None:
            return False
        edge.support_notes.append(f"[{agent}] {note}")
        self._update_edge_confidence(edge, edge.confidence + boost,
                                     f"support by {agent}: {note}")
        if edge.confidence >= 0.6:
            edge.status = RelationStatus.SUPPORTED
        return True

    def falsify_relation(self, edge_id: str, agent: str, note: str,
                         penalty: float = 0.15) -> bool:
        edge = self.edges.get(edge_id)
        if edge is None:
            return False
        edge.falsification_notes.append(f"[{agent}] {note}")
        self._update_edge_confidence(edge, edge.confidence - penalty,
                                     f"falsified by {agent}: {note}")
        if edge.confidence < 0.15:
            edge.status = RelationStatus.CONTRADICTED
        elif edge.confidence < 0.4:
            edge.status = RelationStatus.WEAKENED
        return True

    @staticmethod
    def _update_edge_confidence(edge: RelationEdge, value: float, reason: str) -> None:
        previous = edge.confidence
        edge.confidence = clamp01(value)
        edge.confidence_history.append({"t": utc_now(), "confidence": edge.confidence,
                                        "reason": reason, "previous": previous})

    def falsify_attractive_hypotheses(self, threshold: float = 0.7) -> list[str]:
        notes: list[str] = []
        for edge in self.edges.values():
            if edge.confidence < threshold:
                continue
            a = self.fragments.get(edge.source_fragment)
            b = self.fragments.get(edge.target_fragment)
            if a is None or b is None:
                continue
            scores = (self._source_independence_score(a),
                      self._source_independence_score(b))
            if min(scores) < 0.3:
                self.falsify_relation(edge.edge_id, "AutoFalsifier",
                                      f"Low source independence: a={scores[0]:.2f}, b={scores[1]:.2f}",
                                      0.10)
                notes.append(f"Auto-weakened {edge.edge_id} due to low source independence")
            if edge.temporal_fit is not None and edge.temporal_fit < 0.2:
                self.falsify_relation(edge.edge_id, "AutoFalsifier",
                                      f"Poor temporal fit: {edge.temporal_fit:.2f}", 0.08)
                notes.append(f"Auto-weakened {edge.edge_id} due to poor temporal fit")
        return notes

    def get_fragment(self, fragment_id: str) -> Optional[dict[str, Any]]:
        fragment = self.fragments.get(fragment_id)
        return self._fragment_dict(fragment) if fragment else None

    def get_relation(self, edge_id: str) -> Optional[dict[str, Any]]:
        edge = self.edges.get(edge_id)
        return asdict(edge) if edge else None

    def list_open_hypotheses(self, min_confidence: float = 0.0) -> list[dict[str, Any]]:
        open_statuses = {RelationStatus.PROPOSED, RelationStatus.SUPPORTED,
                         RelationStatus.WEAKENED}
        return sorted((asdict(edge) for edge in self.edges.values()
                       if edge.status in open_statuses and edge.confidence >= min_confidence),
                      key=lambda item: item["confidence"], reverse=True)

    def list_missing(self, resolved: bool = False) -> list[dict[str, Any]]:
        return [asdict(item) for item in self.missing.values()
                if (item.resolved_at is not None) == resolved]

    def trace_path(self, from_fragment: str, max_depth: int = 3) -> list[list[str]]:
        """Return maximal simple paths, bounded to ``max_depth`` edges."""
        if from_fragment not in self.fragments or max_depth < 1:
            return []
        paths: list[list[str]] = []

        def dfs(current: str, depth: int, path: list[str]) -> None:
            path = path + [current]
            if depth >= max_depth:
                paths.append(path)
                return
            neighbours: list[str] = []
            for edge in self.edges.values():
                if edge.source_fragment == current and edge.target_fragment not in path:
                    neighbours.append(edge.target_fragment)
                elif edge.target_fragment == current and edge.source_fragment not in path:
                    neighbours.append(edge.source_fragment)
            if neighbours:
                for neighbour in dict.fromkeys(neighbours):
                    dfs(neighbour, depth + 1, path)
            elif len(path) > 1:
                paths.append(path)

        dfs(from_fragment, 0, [])
        return paths

    def export_state(self) -> dict[str, Any]:
        return {
            "fragments": {key: self._fragment_dict(value)
                          for key, value in self.fragments.items()},
            "edges": {key: asdict(value) for key, value in self.edges.items()},
            "missing": {key: asdict(value) for key, value in self.missing.items()},
            "entity_registry": {
                "canonical": dict(self.entity_registry._canonical),
                "aliases": {key: sorted(value)
                            for key, value in self.entity_registry._aliases.items()},
            },
            "exported_at": utc_now(),
            "note": "WorldPuzzle360 does not decide what the world means.",
            "gap_summary": {"total_missing": len(self.missing),
                            "unresolved": sum(item.resolved_at is None
                                              for item in self.missing.values())},
        }

    @staticmethod
    def _fragment_dict(fragment: PuzzleFragment) -> dict[str, Any]:
        """Serialize the public fragment model without its registry cache."""
        data = asdict(fragment)
        data.pop("_canonical_entities", None)
        return data

    def export_json(self, path: str | Path = "worldpuzzle360_state.json") -> str:
        output = Path(path)
        output.write_text(json.dumps(self.export_state(), indent=2, ensure_ascii=False),
                          encoding="utf-8")
        return str(output)


__all__ = ["EntityRegistry", "FragmentStatus", "MissingPuzzle", "PuzzleFragment",
           "RelationEdge", "RelationStatus", "SourceRef", "WorldPuzzle360",
           "clamp01", "parse_fuzzy_date", "temporal_distance_in_days"]
