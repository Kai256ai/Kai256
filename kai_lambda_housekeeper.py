"""KAI Lambda Housekeeper 360 v3.1.

An auditable, standard-library-only representation fidelity engine.  The wave
descriptor exposed by this module is diagnostic metadata and is never used as
policy evidence.
"""

from __future__ import annotations

import cmath
import math
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

EPS = 1e-9


class EpistemicType(str, Enum):
    OBSERVED = "observed"
    REPORTED = "reported"
    INFERRED = "inferred"
    DERIVED = "derived"


class LambdaClass(str, Enum):
    PLUS = "lambda_plus"
    ZERO = "lambda_zero"
    MINUS = "lambda_minus"


class Action(str, Enum):
    KEEP = "keep"
    TRANSFORM = "transform"
    DAMP = "damp"
    DECAY = "decay"
    ARCHIVE = "archive"
    DELETE = "delete"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class TemporalRelationship(str, Enum):
    SAME_WINDOW = "same_window"
    DIVERGENT = "divergent"
    UNKNOWN = "unknown"


@dataclass
class Node:
    id: str
    value: float = 1.0
    semantic: str = ""
    epistemic: EpistemicType = EpistemicType.REPORTED
    confidence: float = 1.0
    importance: float = 0.5
    uniqueness: float = 0.5
    historical_value: float = 0.0
    amplitude: float = 1.0
    phase: float = 0.0
    parents: List[str] = field(default_factory=list)
    source_id: Optional[str] = None
    transformations: List[str] = field(default_factory=list)
    observed_at: Optional[float] = None
    reported_at: Optional[float] = None
    valid_from: Optional[float] = None
    valid_until: Optional[float] = None
    layer: str = "default"
    timescale: str = "medium"
    active: bool = True
    archived: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    relation: str = "related"
    weight: float = 1.0
    sign: int = 1
    confidence: float = 1.0
    layer: str = "default"
    amplitude: float = 1.0
    phase: float = 0.0


@dataclass
class GraphState:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    time: float = 0.0
    history: List[str] = field(default_factory=list)

    def clone(self) -> "GraphState":
        return deepcopy(self)


@dataclass
class Trace:
    target: str
    roots: Set[str]
    path: List[str]
    reconstructable: bool
    cycles: List[List[str]] = field(default_factory=list)


@dataclass
class Finding:
    kind: str
    nodes: List[str]
    confidence: float
    reason: str
    severity: Severity = Severity.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metrics:
    structural_health: float
    provenance_health: float
    semantic_fidelity: float
    confidence: float
    information_loss: float
    risk: float
    observed_data_sufficiency: float = 1.0

    def vector(self) -> Dict[str, float]:
        return {name: getattr(self, name) for name in (
            "structural_health", "provenance_health", "semantic_fidelity",
            "confidence", "information_loss", "risk",
        )}


@dataclass
class LambdaResult:
    classification: LambdaClass
    score: float
    delta: Dict[str, float]
    confidence: float
    support_ratio: float = 0.0


@dataclass
class DecisionRationale:
    primary: str
    policy_step: int
    score: float
    protection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    target: str
    action: Action
    lambda_result: LambdaResult
    rationale: DecisionRationale

    @property
    def reason(self) -> str:
        return self.rationale.primary


@dataclass
class CycleResult:
    initial_state: GraphState
    proposed_state: GraphState
    final_state: GraphState
    findings: List[Finding]
    decisions: List[Decision]
    lambda_representation: LambdaResult
    lambda_observed: LambdaResult
    global_lambda: LambdaResult
    wave_descriptor: Dict[str, Any]
    consistency_note: Optional[str]
    rolled_back: bool
    removed_decisions: List[Decision] = field(default_factory=list)


@dataclass
class BatchConflict:
    kind: str
    targets: Set[str]
    reason: str


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def active_nodes(state: GraphState) -> List[Node]:
    return [node for node in state.nodes.values() if node.active and not node.archived]


def adjacency(state: GraphState) -> Dict[str, Set[str]]:
    """Build structural adjacency from both explicit edges and provenance links."""
    allowed = {node.id for node in active_nodes(state)}
    result = {node_id: set() for node_id in allowed}
    pairs = [(edge.source, edge.target) for edge in state.edges]
    pairs.extend((parent, node.id) for node in active_nodes(state) for parent in node.parents)
    for source, target in pairs:
        if source in allowed and target in allowed:
            result[source].add(target)
            result[target].add(source)
    return result


def connected_components(state: GraphState) -> List[Set[str]]:
    graph = adjacency(state)
    seen: Set[str] = set()
    components: List[Set[str]] = []
    for start in graph:
        if start in seen:
            continue
        component: Set[str] = set()
        stack = [start]
        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            component.add(node_id)
            stack.extend(graph[node_id] - seen)
        components.append(component)
    return components


def tarjan_bridges(state: GraphState) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """Return articulation vertices and bridges in O(vertices + edges)."""
    graph = adjacency(state)
    discovered: Dict[str, int] = {}
    low: Dict[str, int] = {}
    parent: Dict[str, Optional[str]] = {}
    articulation: Set[str] = set()
    bridges: Set[Tuple[str, str]] = set()
    timer = 0

    def visit(node_id: str) -> None:
        nonlocal timer
        discovered[node_id] = low[node_id] = timer
        timer += 1
        children = 0
        for neighbour in graph[node_id]:
            if neighbour not in discovered:
                parent[neighbour] = node_id
                children += 1
                visit(neighbour)
                low[node_id] = min(low[node_id], low[neighbour])
                if parent[node_id] is None and children > 1:
                    articulation.add(node_id)
                if parent[node_id] is not None and low[neighbour] >= discovered[node_id]:
                    articulation.add(node_id)
                if low[neighbour] > discovered[node_id]:
                    bridges.add(tuple(sorted((node_id, neighbour))))
            elif neighbour != parent[node_id]:
                low[node_id] = min(low[node_id], discovered[neighbour])

    for node_id in graph:
        if node_id not in discovered:
            parent[node_id] = None
            visit(node_id)
    return articulation, bridges


class ProvenanceEngine:
    def roots(self, state: GraphState, node_id: str, visited: Optional[Set[str]] = None) -> Set[str]:
        visited = set() if visited is None else visited
        if node_id in visited:
            return set()
        visited.add(node_id)
        node = state.nodes.get(node_id)
        if node is None:
            return set()
        parents = [parent for parent in node.parents if parent in state.nodes and parent != node_id]
        if not parents:
            return {node.source_id or node.id}
        roots: Set[str] = set()
        for parent in parents:
            roots |= self.roots(state, parent, set(visited))
        return roots

    def traceback(self, state: GraphState, target: str) -> Trace:
        if target not in state.nodes:
            return Trace(target, set(), [], False)
        path: List[str] = []
        seen: Set[str] = set()
        cycles: List[List[str]] = []

        def walk(node_id: str, stack: List[str]) -> None:
            if node_id in stack:
                cycles.append(stack[stack.index(node_id):] + [node_id])
                return
            if node_id in seen:
                return
            seen.add(node_id)
            path.append(node_id)
            for parent in state.nodes[node_id].parents:
                if parent in state.nodes:
                    walk(parent, stack + [node_id])

        walk(target, [])
        roots = self.roots(state, target)
        return Trace(target, roots, path, bool(roots), cycles)

    def detect_cycles(self, state: GraphState) -> List[List[str]]:
        cycles: List[List[str]] = []
        keys: Set[frozenset[str]] = set()
        for node_id in state.nodes:
            for cycle in self.traceback(state, node_id).cycles:
                key = frozenset(cycle)
                if key not in keys:
                    keys.add(key)
                    cycles.append(cycle)
        return cycles

    def children_of(self, state: GraphState, node_id: str) -> List[Node]:
        return [node for node in state.nodes.values() if node_id in node.parents]

    def independent_root_count(self, state: GraphState, node_ids: List[str]) -> int:
        roots: Set[str] = set()
        for node_id in node_ids:
            roots |= self.roots(state, node_id)
        return len(roots)


class TemporalAuditor:
    WINDOW_SECONDS = 30 * 24 * 3600

    def classify(self, first: Node, second: Node) -> TemporalRelationship:
        first_time = first.observed_at if first.observed_at is not None else first.reported_at
        second_time = second.observed_at if second.observed_at is not None else second.reported_at
        if first_time is None or second_time is None:
            return TemporalRelationship.UNKNOWN
        return (TemporalRelationship.SAME_WINDOW if abs(first_time - second_time) <= self.WINDOW_SECONDS
                else TemporalRelationship.DIVERGENT)


class SeverityScorer:
    BASE = {
        (EpistemicType.OBSERVED, EpistemicType.DERIVED): Severity.CRITICAL,
        (EpistemicType.OBSERVED, EpistemicType.REPORTED): Severity.HIGH,
        (EpistemicType.OBSERVED, EpistemicType.INFERRED): Severity.MEDIUM,
        (EpistemicType.REPORTED, EpistemicType.DERIVED): Severity.HIGH,
        (EpistemicType.REPORTED, EpistemicType.INFERRED): Severity.MEDIUM,
        (EpistemicType.DERIVED, EpistemicType.INFERRED): Severity.LOW,
    }
    CAPS = {"reclassification": None, "data_entry": Severity.HIGH,
            "translation": Severity.LOW, "formatting": Severity.LOW,
            "aggregation": Severity.MEDIUM, "summary": Severity.MEDIUM}
    ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]

    def score(self, source: EpistemicType, target: EpistemicType,
              transformations: List[str]) -> Severity:
        result = self.BASE.get((source, target), Severity.MEDIUM)
        for transformation in transformations:
            cap = self.CAPS.get(transformation)
            if cap is not None and self.ORDER.index(result) > self.ORDER.index(cap):
                result = cap
        return result


class RealityAuditor:
    COMPARED = {EpistemicType.REPORTED, EpistemicType.DERIVED, EpistemicType.INFERRED}

    def __init__(self) -> None:
        self.severity = SeverityScorer()
        self.temporal = TemporalAuditor()

    def _compare(self, observed: Node, compared: Node, entity: str,
                 findings: List[Finding], both_observed: bool = False) -> None:
        if not observed.semantic or not compared.semantic or observed.semantic == compared.semantic:
            return
        temporal = self.temporal.classify(observed, compared)
        severity = self.severity.score(observed.epistemic, compared.epistemic,
                                       compared.transformations)
        if temporal == TemporalRelationship.DIVERGENT:
            kind, severity = "TEMPORAL_DIVERGENCE", Severity.LOW
            reason = f"Semantic mismatch for entity='{entity}', but timestamps differ; it may be a legitimate change."
        elif temporal == TemporalRelationship.UNKNOWN:
            kind = "STATE_DISCREPANCY"
            reason = f"For entity='{entity}': semantic mismatch; timing unresolved."
        else:
            kind = "STATE_DISCREPANCY"
            reason = f"For entity='{entity}': semantic mismatch within the same time window."
        findings.append(Finding(kind, [compared.id, observed.id],
                                min(observed.confidence, compared.confidence), reason, severity,
                                {"entity": entity, "temporal": temporal.value,
                                 "transformations": list(compared.transformations),
                                 "both_observed": both_observed}))

    def analyse(self, state: GraphState) -> List[Finding]:
        findings = [Finding("PROVENANCE_CYCLE", cycle, 1.0,
                            "Cycle in provenance graph is a data integrity error.", Severity.CRITICAL)
                    for cycle in ProvenanceEngine().detect_cycles(state)]
        groups: Dict[str, List[Node]] = {}
        for node in active_nodes(state):
            if node.metadata.get("entity") is not None:
                groups.setdefault(str(node.metadata["entity"]), []).append(node)
        for entity, nodes in groups.items():
            observed = [node for node in nodes if node.epistemic == EpistemicType.OBSERVED]
            compared = [node for node in nodes if node.epistemic in self.COMPARED]
            for source in observed:
                for target in compared:
                    self._compare(source, target, entity, findings)
            for index, source in enumerate(observed):
                for target in observed[index + 1:]:
                    self._compare(source, target, entity, findings, True)
        for node in active_nodes(state):
            for parent_id in node.parents:
                parent = state.nodes.get(parent_id)
                if parent is None:
                    continue
                scale = max(1.0, abs(node.value), abs(parent.value))
                stable = abs(node.value - parent.value) / scale <= 0.05
                changed = bool(parent.semantic and node.semantic and parent.semantic != node.semantic)
                if stable and changed:
                    findings.append(Finding(
                        "SEMANTIC_TRANSITION_POINT", [parent.id, node.id],
                        min(parent.confidence, node.confidence),
                        f"Numerical continuity preserved while semantic identity changed: '{parent.semantic}' -> '{node.semantic}'.",
                        self.severity.score(parent.epistemic, node.epistemic, node.transformations),
                        {"from_semantic": parent.semantic, "to_semantic": node.semantic,
                         "transformations": list(node.transformations)}))
        return findings


class SudokuEngine:
    def analyse(self, state: GraphState) -> List[Finding]:
        findings: List[Finding] = []
        provenance = ProvenanceEngine()
        ids = [node.id for node in active_nodes(state)]
        by_root: Dict[str, List[str]] = {}
        for node_id in ids:
            for root in provenance.roots(state, node_id):
                by_root.setdefault(root, []).append(node_id)
        for root, members in by_root.items():
            if len(members) >= 3:
                findings.append(Finding("SHARED_ANCESTRY_CLUSTER", [root] + members, 0.85,
                                        f"{len(members)} outputs share root '{root}'.", Severity.HIGH,
                                        {"root": root, "cluster_size": len(members)}))
        by_parent: Dict[str, List[Node]] = {}
        for node in active_nodes(state):
            for parent in node.parents:
                by_parent.setdefault(parent, []).append(node)
        for parent, children in by_parent.items():
            total = sum(abs(child.value) for child in children)
            if total <= EPS:
                continue
            concentration = max(abs(child.value) for child in children) / total
            if concentration >= 0.70:
                findings.append(Finding(
                    "DISTRIBUTION_CONCENTRATION", [parent] + [child.id for child in children],
                    concentration, f"{concentration:.1%} of child mass is concentrated in one branch.",
                    Severity.MEDIUM))
        if len(ids) >= 3:
            root_count = provenance.independent_root_count(state, ids)
            if root_count and len(ids) / root_count >= 4.0:
                findings.append(Finding("ECHO_CLUSTER", ids[:12], clamp(1 - root_count / len(ids)),
                                        f"{len(ids)} active nodes collapse to {root_count} independent root(s).",
                                        Severity.HIGH))
        return findings


class View360:
    def inspect(self, state: GraphState, target: str) -> Dict[str, Any]:
        trace = ProvenanceEngine().traceback(state, target)
        return {"target": target, "traceback": trace,
                "incoming": [edge for edge in state.edges if edge.target == target],
                "outgoing": [edge for edge in state.edges if edge.source == target],
                "roots": sorted(trace.roots), "cycles": trace.cycles}


class LSDScale:
    def view(self, state: GraphState, scale: str) -> List[Node]:
        nodes = active_nodes(state)
        if scale == "micro":
            return sorted(nodes, key=lambda node: (node.uniqueness, node.historical_value,
                                                   node.importance), reverse=True)
        if scale == "macro":
            return sorted(nodes, key=lambda node: (len(node.parents), node.importance), reverse=True)
        return nodes


class WaveDecoder:
    def decode(self, state: GraphState) -> Dict[str, Any]:
        waves = [cmath.rect(node.amplitude * abs(node.value) * node.confidence, node.phase)
                 for node in active_nodes(state)]
        if not waves:
            return {"magnitude": 0.0, "phase": 0.0, "coherence": 0.0,
                    "note": "diagnostic only; NOT evidence of truth"}
        resultant = sum(waves, 0j)
        total = sum(abs(wave) for wave in waves)
        return {"magnitude": abs(resultant), "phase": cmath.phase(resultant),
                "coherence": clamp(abs(resultant) / total if total > EPS else 0.0),
                "note": "diagnostic only; NOT evidence of truth"}


def evaluate_metrics(state: GraphState,
                     epistemic_filter: Optional[EpistemicType] = None) -> Metrics:
    all_active = active_nodes(state)
    nodes = ([node for node in all_active if node.epistemic == epistemic_filter]
             if epistemic_filter is not None else all_active)
    if not nodes:
        return Metrics(0, 0, 0, 0, 1, 1, 0)
    structural = 1 / max(1, len(connected_components(state)))
    provenance = sum(bool(node.source_id or node.parents) for node in nodes) / len(nodes)
    findings = RealityAuditor().analyse(state)
    penalties = {Severity.CRITICAL: 1.0, Severity.HIGH: 0.5, Severity.MEDIUM: 0.2}
    semantic = clamp(1 - sum(penalties.get(item.severity, 0) for item in findings)
                     / max(1, len(all_active)))
    confidence = sum(node.confidence for node in nodes) / len(nodes)
    loss = sum(not node.active or node.archived for node in state.nodes.values()) / max(1, len(state.nodes))
    risk = clamp(0.35 * (1 - structural) + 0.30 * (1 - provenance) + 0.35 * (1 - semantic))
    observed = [node for node in all_active if node.epistemic == EpistemicType.OBSERVED]
    sufficiency = sum(node.confidence for node in observed) / len(observed) if observed else 0.0
    return Metrics(clamp(structural), clamp(provenance), semantic, clamp(confidence),
                   clamp(loss), risk, clamp(sufficiency))


class LambdaEngine:
    WEIGHTS = {"structural_health": 1.2, "provenance_health": 1.4,
               "semantic_fidelity": 1.8, "confidence": 0.8,
               "information_loss": -1.5, "risk": -1.5}

    def __init__(self, plus_threshold: float = 0.02, minus_threshold: float = -0.02):
        self.plus_threshold = plus_threshold
        self.minus_threshold = minus_threshold

    def evaluate(self, before: GraphState, after: GraphState,
                 epistemic_filter: Optional[EpistemicType] = None) -> LambdaResult:
        before_vector = evaluate_metrics(before, epistemic_filter).vector()
        after_vector = evaluate_metrics(after, epistemic_filter).vector()
        delta = {key: after_vector[key] - before_vector[key] for key in before_vector}
        score = sum(delta[key] * self.WEIGHTS[key] for key in delta) / sum(map(abs, self.WEIGHTS.values()))
        classification = (LambdaClass.PLUS if score > self.plus_threshold else
                          LambdaClass.MINUS if score < self.minus_threshold else LambdaClass.ZERO)
        comparable = []
        for node_id, after_node in after.nodes.items():
            before_node = before.nodes.get(node_id)
            if before_node is None or (before_node.active and not after_node.active) or (
                    not before_node.archived and after_node.archived):
                continue
            comparable.append(after_node.confidence >= before_node.confidence and
                              after_node.value >= before_node.value * 0.95)
        support_ratio = sum(comparable) / len(comparable) if comparable else 0.0
        return LambdaResult(classification, score, delta, clamp(support_ratio), support_ratio)


class Simulator:
    def apply(self, state: GraphState, target: str, action: Action) -> GraphState:
        result = state.clone()
        node = result.nodes.get(target)
        if node is None:
            return result
        if action == Action.TRANSFORM:
            node.confidence = clamp(node.confidence + 0.05)
            node.transformations.append("transform_attempt")
            for observed in result.nodes.values():
                if (observed.id != node.id and observed.epistemic == EpistemicType.OBSERVED
                        and observed.metadata.get("entity") == node.metadata.get("entity")
                        and observed.semantic and node.semantic != observed.semantic):
                    node.metadata["prior_reported_semantic"] = node.semantic
                    node.metadata["repaired_from_observed"] = observed.semantic
                    node.semantic = observed.semantic
                    node.transformations.append("repair_from_observed")
                    break
        elif action == Action.DAMP:
            node.amplitude *= 0.75
            node.value *= 0.90
        elif action == Action.DECAY:
            node.amplitude *= math.exp(-0.20)
            node.value *= math.exp(-0.20)
        elif action == Action.ARCHIVE:
            node.archived = True
        elif action == Action.DELETE:
            node.active = False
            result.edges = [edge for edge in result.edges
                            if edge.source != target and edge.target != target]
        result.history.append(f"{action.value}:{target}")
        result.time += 1
        return result


class Housekeeper:
    PRIORITY = (Action.TRANSFORM, Action.DAMP, Action.DECAY)

    def __init__(self, lambda_engine: LambdaEngine):
        self.lambda_engine = lambda_engine
        self.simulator = Simulator()
        self.provenance = ProvenanceEngine()

    def deletion_protected(self, state: GraphState, target: str, articulation: Set[str],
                           bridges: Set[Tuple[str, str]]) -> Tuple[bool, str]:
        node = state.nodes[target]
        if node.uniqueness >= 0.80:
            return True, "Highly unique information."
        if node.historical_value >= 0.80:
            return True, "High historical value."
        trace = self.provenance.traceback(state, target)
        if trace.cycles:
            return True, "Target is part of provenance cycle."
        if not trace.reconstructable:
            return True, "Deletion blocked: provenance cannot be reconstructed."
        if target in articulation:
            return True, "Deletion blocked: articulation point."
        if any(target in bridge for bridge in bridges):
            return True, "Deletion blocked: structural bridge."
        if any(child.uniqueness >= 0.75 and len(child.parents) == 1
               for child in self.provenance.children_of(state, target)):
            return True, "Deletion blocked: sole provenance parent of unique child."
        return False, ""

    def choose(self, state: GraphState, target: str, articulation: Set[str],
               bridges: Set[Tuple[str, str]]) -> Decision:
        baseline = self.lambda_engine.evaluate(state, state)
        node = state.nodes[target]
        rare = node.uniqueness >= 0.90 or node.historical_value >= 0.90
        for step, action in enumerate(self.PRIORITY):
            if rare and action in (Action.DAMP, Action.DECAY):
                continue
            result = self.lambda_engine.evaluate(state, self.simulator.apply(state, target, action))
            if result.classification == LambdaClass.PLUS:
                return Decision(target, action, result, DecisionRationale(
                    f"{action.value} is first positive option", step, result.score,
                    metadata={"node_uniqueness": node.uniqueness}))
        protected, reason = self.deletion_protected(state, target, articulation, bridges)
        if protected:
            return Decision(target, Action.KEEP, baseline,
                            DecisionRationale("protected", 3, baseline.score, reason))
        archived = self.lambda_engine.evaluate(state, self.simulator.apply(state, target, Action.ARCHIVE))
        if archived.classification != LambdaClass.MINUS:
            return Decision(target, Action.ARCHIVE, archived,
                            DecisionRationale("archive preserves recoverability", 4, archived.score))
        deleted = self.lambda_engine.evaluate(state, self.simulator.apply(state, target, Action.DELETE))
        if deleted.classification == LambdaClass.PLUS:
            return Decision(target, Action.DELETE, deleted,
                            DecisionRationale("ablation supports removal", 5, deleted.score))
        return Decision(target, Action.KEEP, baseline,
                        DecisionRationale("preserve under uncertainty", 6, baseline.score))


class BatchEngine:
    def audit(self, state: GraphState, decisions: List[Decision]) -> Optional[BatchConflict]:
        by_target: Dict[str, List[Decision]] = {}
        for decision in decisions:
            by_target.setdefault(decision.target, []).append(decision)
        for target, matches in by_target.items():
            if len(matches) > 1:
                return BatchConflict("DUPLICATE_TARGET", {target}, f"Conflicting decisions for {target}.")
        actions = {decision.target: decision.action for decision in decisions}
        provenance = ProvenanceEngine()
        for decision in decisions:
            if decision.action == Action.DELETE:
                for child in provenance.children_of(state, decision.target):
                    if child.active and actions.get(child.id) not in (Action.DELETE, Action.ARCHIVE):
                        return BatchConflict("DELETE_PARENT_ACTIVE_CHILD", {decision.target, child.id},
                                             f"DELETE {decision.target} leaves active child {child.id}.")
        return None

    def cascade_resolve(self, state: GraphState, decisions: List[Decision]
                        ) -> Tuple[List[Decision], List[Decision], Optional[str]]:
        current, removed, notes = list(decisions), [], []
        while current:
            conflict = self.audit(state, current)
            if conflict is None:
                return current, removed, "; ".join(notes) or None
            candidates = [decision for decision in current if decision.target in conflict.targets]
            if not candidates:
                return [], removed, "; ".join(notes + [f"Unresolvable: {conflict.reason}"])
            weakest = min(candidates, key=lambda decision: (
                decision.lambda_result.confidence, decision.lambda_result.score))
            current.remove(weakest)
            removed.append(weakest)
            notes.append(f"{conflict.kind}: removed {weakest.target}/{weakest.action.value}")
        return [], removed, "; ".join(notes) or "All decisions removed."


class KaiLambdaHousekeeper360:
    def __init__(self) -> None:
        self.lambda_engine = LambdaEngine()
        self.view360 = View360()
        self.sudoku = SudokuEngine()
        self.lsd = LSDScale()
        self.reality = RealityAuditor()
        self.wave = WaveDecoder()
        self.housekeeper = Housekeeper(self.lambda_engine)
        self.simulator = Simulator()
        self.batch = BatchEngine()

    def analyse(self, state: GraphState) -> List[Finding]:
        return self.reality.analyse(state) + self.sudoku.analyse(state)

    def replay(self, state: GraphState, decisions: List[Decision]) -> GraphState:
        result = state.clone()
        for decision in decisions:
            result = self.simulator.apply(result, decision.target, decision.action)
        return result

    def run(self, state: GraphState, targets: Optional[List[str]] = None) -> CycleResult:
        original = state.clone()
        findings = self.analyse(original)
        articulation, bridges = tarjan_bridges(original)
        target_ids = targets if targets is not None else [node.id for node in active_nodes(original)]
        proposed = [self.housekeeper.choose(original, target, articulation, bridges)
                    for target in target_ids if target in original.nodes]
        accepted, removed, note = self.batch.cascade_resolve(original, proposed)
        candidate = self.replay(original, accepted)
        representation = self.lambda_engine.evaluate(original, candidate, EpistemicType.REPORTED)
        observed = self.lambda_engine.evaluate(original, candidate, EpistemicType.OBSERVED)
        global_result = self.lambda_engine.evaluate(original, candidate)
        observed_sufficiency = evaluate_metrics(original, EpistemicType.OBSERVED).observed_data_sufficiency
        if representation.classification == LambdaClass.PLUS and observed.classification != LambdaClass.PLUS:
            data_gap = observed_sufficiency < 0.3
            findings.append(Finding(
                "GREEN_CORPSE_EFFECT", [], min(representation.confidence, observed.confidence),
                "Representation improves while observed reality does not. " +
                ("Observed data is insufficient." if data_gap else "Observed divergence is supported."),
                Severity.MEDIUM if data_gap else Severity.HIGH,
                {"observed_data_sufficiency": observed_sufficiency}))
        rolled_back = global_result.classification == LambdaClass.MINUS
        final = original.clone() if rolled_back else candidate
        if rolled_back:
            final.history.append("GLOBAL_ROLLBACK")
        return CycleResult(original, candidate, final, findings, accepted, representation,
                           observed, global_result, self.wave.decode(original), note,
                           rolled_back, removed)
