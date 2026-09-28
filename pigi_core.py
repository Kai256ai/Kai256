"""PIGI semantic provenance and value-flow core.

The core deliberately stores decisions as an auditable graph rather than silently
turning linguistic associations into facts.  Mutating methods validate provenance
at their boundary, so graph contents remain safe to serialize and inspect.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable
from uuid import uuid4


def _id() -> str:
    return uuid4().hex


def _label(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


class UnitType(str, Enum):
    CLAIM = "claim"
    EVIDENCE = "evidence"
    OBSERVATION = "observation"


class RelationType(str, Enum):
    SUPPORTS = "supports"
    VALIDATES = "validates"
    RELATED_TO = "related_to"


class EpistemicLevel(str, Enum):
    HYPOTHESIS = "hypothesis"
    OBSERVED = "observed"


# A convenient compatibility spelling used by early PIGI drafts.
EpistemicStatus = EpistemicLevel


class GuardDecision(str, Enum):
    ALLOWED = "allowed"
    REQUIRES_CANONICAL_LABEL = "requires_canonical_label"
    REQUIRES_RELATION = "requires_relation"
    REQUIRES_LICENSE_PROVENANCE = "requires_license_provenance"
    REQUIRES_EVIDENCE = "requires_evidence"
    ALLOWED_WITH_RELATION = "allowed_with_relation"


class FlowState(str, Enum):
    PROPOSED = "proposed"
    OBSERVED = "observed"


class ValueType(str, Enum):
    REPUTATION = "reputation"
    LEADS = "leads"
    MONEY = "money"


@dataclass
class Artifact:
    raw_text: str
    id: str = field(default_factory=_id)
    revoked: bool = False
    revocation_reason: str | None = None


@dataclass(frozen=True)
class Provenance:
    artifact_id: str | None
    level: EpistemicLevel = EpistemicLevel.OBSERVED

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", getattr(self.artifact_id, "id", self.artifact_id))
        object.__setattr__(self, "level", EpistemicLevel(self.level))


@dataclass
class InformationUnit:
    content: str
    unit_type: UnitType
    provenance: Provenance
    id: str = field(default_factory=_id)

    def __post_init__(self) -> None:
        self.unit_type = UnitType(self.unit_type)


@dataclass
class Entity:
    name: str
    provenance: Provenance
    id: str = field(default_factory=_id)


@dataclass
class SemanticLicense:
    pair: tuple[str, str]
    provenance: Provenance
    basis: str
    id: str = field(default_factory=_id)
    revoked: bool = False
    revocation_reason: str | None = None

    def __post_init__(self) -> None:
        self.pair = (_label(self.pair[0]), _label(self.pair[1]))


@dataclass
class Relation:
    source_node_id: str
    target_node_id: str
    relation_type: RelationType
    provenance: Provenance
    description: str = ""
    licenses: list[SemanticLicense] = field(default_factory=list)
    id: str = field(default_factory=_id)


@dataclass
class SignalScope:
    activity: str | None = None
    result: str | None = None


@dataclass
class SignalEvent:
    kind: str
    subject_id: str
    provenance: Provenance
    scope: SignalScope | None = None
    id: str = field(default_factory=_id)


@dataclass
class ValueFlow:
    source_node_id: str
    target_node_id: str
    value_type: ValueType
    state: FlowState
    provenance: Provenance
    id: str = field(default_factory=_id)


@dataclass
class FlowCandidate:
    source_node_id: str
    target_node_id: str | None
    value_type: ValueType
    provenance: Provenance
    basis: str
    id: str = field(default_factory=_id)


@dataclass
class Transformation:
    source_node_id: str
    target_node_id: str
    description: str
    provenance: Provenance
    id: str = field(default_factory=_id)


@dataclass
class PIGIGraph:
    artifacts: list[Artifact] = field(default_factory=list)
    units: list[InformationUnit] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    signals: list[SignalEvent] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    value_flows: list[ValueFlow] = field(default_factory=list)
    flow_candidates: list[FlowCandidate] = field(default_factory=list)
    transformations: list[Transformation] = field(default_factory=list)
    entity_resolutions: list[Any] = field(default_factory=list)


class PIGICore:
    """Validated graph for semantic transitions and material value flows."""

    DEFAULT_GUARDS = {("popularity", "evidence"), ("authority", "proof")}
    DEFAULT_LABELS = {item for pair in DEFAULT_GUARDS for item in pair}

    def __init__(self, *, strict_labels: bool = False) -> None:
        self.graph = PIGIGraph()
        self.strict_labels = strict_labels
        self._labels = set(self.DEFAULT_LABELS)
        self._guards = set(self.DEFAULT_GUARDS)
        self._frozen = False

    def _artifact(self, provenance: Provenance) -> Artifact:
        artifact = next((a for a in self.graph.artifacts if a.id == provenance.artifact_id), None)
        if artifact is None:
            raise ValueError("provenance must reference an artifact in this graph")
        if artifact.revoked:
            raise ValueError("provenance artifact has been revoked")
        return artifact

    def _node(self, node_id: str) -> InformationUnit:
        node = next((u for u in self.graph.units if u.id == node_id), None)
        if node is None:
            raise ValueError(f"unknown information unit: {node_id}")
        return node

    def add_artifact(self, artifact: Artifact) -> str:
        if self._frozen:
            raise RuntimeError("the artifact set is frozen")
        if any(a.id == artifact.id for a in self.graph.artifacts):
            raise ValueError("duplicate artifact id")
        self.graph.artifacts.append(artifact)
        return artifact.id

    def register_unit(self, unit: InformationUnit) -> str:
        self._artifact(unit.provenance)
        self.graph.units.append(unit)
        return unit.id

    def register_entity(self, name: str, provenance: Provenance) -> str:
        self._artifact(provenance)
        entity = Entity(name, provenance)
        self.graph.entities.append(entity)
        return entity.id

    def register_label(self, label: str) -> str:
        canonical = _label(label)
        if not canonical:
            raise ValueError("label cannot be empty")
        self._labels.add(canonical)
        return canonical

    def connect(self, source_node_id: str, target_node_id: str,
                relation_type: RelationType, provenance: Provenance, *,
                description: str = "", licenses: Iterable[SemanticLicense] = ()) -> Relation:
        self._node(source_node_id)
        self._node(target_node_id)
        artifact = self._artifact(provenance)
        checked = list(licenses)
        for license_ in checked:
            self._validate_license(license_, artifact.id)
        relation = Relation(source_node_id, target_node_id, RelationType(relation_type),
                            provenance, description, checked)
        self.graph.relations.append(relation)
        return relation

    def _validate_license(self, license_: SemanticLicense, relation_artifact_id: str) -> None:
        artifact = self._artifact(license_.provenance)
        if artifact.id != relation_artifact_id:
            raise ValueError("license provenance must belong to the relation artifact")
        if license_.pair not in self._guards:
            raise ValueError("a license can only address a guarded semantic pair")

    def grant_license(self, relation_id: str, pair: tuple[str, str],
                      provenance: Provenance, basis: str) -> SemanticLicense:
        relation = next((r for r in self.graph.relations if r.id == relation_id), None)
        if relation is None:
            raise ValueError("unknown relation")
        license_ = SemanticLicense(pair, provenance, basis)
        self._validate_license(license_, relation.provenance.artifact_id or "")
        relation.licenses.append(license_)
        return license_

    def revoke_license(self, license_id: str, reason: str) -> None:
        for relation in self.graph.relations:
            for license_ in relation.licenses:
                if license_.id == license_id:
                    license_.revoked, license_.revocation_reason = True, reason
                    return
        raise ValueError("unknown license")

    def revoke_artifact(self, artifact_id: str, reason: str) -> None:
        artifact = next((a for a in self.graph.artifacts if a.id == artifact_id), None)
        if artifact is None:
            raise ValueError("unknown artifact")
        artifact.revoked, artifact.revocation_reason = True, reason
        for relation in self.graph.relations:
            for license_ in relation.licenses:
                if license_.provenance.artifact_id == artifact_id:
                    license_.revoked, license_.revocation_reason = True, reason

    def evaluate_transition(self, source_label: str, target_label: str, *,
                            source_node_id: str | None = None,
                            target_node_id: str | None = None) -> GuardDecision:
        pair = (_label(source_label), _label(target_label))
        if self.strict_labels and any(label not in self._labels for label in pair):
            return GuardDecision.REQUIRES_CANONICAL_LABEL
        if pair not in self._guards:
            return GuardDecision.ALLOWED
        if not source_node_id or not target_node_id or source_node_id == target_node_id:
            return GuardDecision.REQUIRES_RELATION
        relations = [r for r in self.graph.relations
                     if r.source_node_id == source_node_id and r.target_node_id == target_node_id]
        if not relations:
            return GuardDecision.REQUIRES_RELATION
        licenses = [license_ for r in relations for license_ in r.licenses
                    if license_.pair == pair and not license_.revoked]
        licenses = [license_ for license_ in licenses
                    if any(a.id == license_.provenance.artifact_id and not a.revoked
                           for a in self.graph.artifacts)]
        if not licenses:
            return GuardDecision.REQUIRES_LICENSE_PROVENANCE
        if not any(item.provenance.level == EpistemicLevel.OBSERVED for item in licenses):
            return GuardDecision.REQUIRES_EVIDENCE
        return GuardDecision.ALLOWED_WITH_RELATION

    def register_signal(self, signal: SignalEvent) -> str:
        self._artifact(signal.provenance)
        if not any(entity.id == signal.subject_id for entity in self.graph.entities):
            raise ValueError("signal subject must be a registered entity")
        self.graph.signals.append(signal)
        if signal.scope and signal.scope.result:
            self.graph.flow_candidates.append(FlowCandidate(
                signal.subject_id, None, ValueType.REPUTATION, signal.provenance,
                f"signal scope result: {signal.scope.result}"))
        return signal.id

    def add_scope_candidate(self, signal_id: str, scope: SignalScope,
                            provenance: Provenance, basis: str) -> FlowCandidate:
        signal = next((s for s in self.graph.signals if s.id == signal_id), None)
        if signal is None:
            raise ValueError("unknown signal")
        self._artifact(provenance)
        candidate = FlowCandidate(signal.subject_id, None, ValueType.REPUTATION,
                                  provenance, basis + (f" ({scope.result})" if scope.result else ""))
        self.graph.flow_candidates.append(candidate)
        return candidate

    def trace_value(self, source_node_id: str, target_node_id: str, value_type: ValueType,
                    state: FlowState, provenance: Provenance) -> ValueFlow:
        self._node(source_node_id)
        self._node(target_node_id)
        self._artifact(provenance)
        state = FlowState(state)
        if state == FlowState.OBSERVED and provenance.level != EpistemicLevel.OBSERVED:
            raise ValueError("an observed flow requires observed provenance")
        flow = ValueFlow(source_node_id, target_node_id, ValueType(value_type), state, provenance)
        self.graph.value_flows.append(flow)
        return flow

    def add_flow_candidate(self, source_node_id: str, target_node_id: str,
                           value_type: ValueType, provenance: Provenance,
                           basis: str) -> FlowCandidate:
        self._node(source_node_id)
        self._node(target_node_id)
        self._artifact(provenance)
        candidate = FlowCandidate(source_node_id, target_node_id, ValueType(value_type),
                                  provenance, basis)
        self.graph.flow_candidates.append(candidate)
        return candidate

    def add_transformation(self, source_node_id: str, target_node_id: str,
                           description: str, provenance: Provenance) -> Transformation:
        self._node(source_node_id)
        self._node(target_node_id)
        self._artifact(provenance)
        item = Transformation(source_node_id, target_node_id, description, provenance)
        self.graph.transformations.append(item)
        return item

    def freeze(self) -> None:
        if not self.graph.artifacts:
            raise RuntimeError("cannot freeze an empty evidence set")
        self._frozen = True

    def to_dict(self) -> dict[str, Any]:
        return {"version": "0.7.0", "frozen": self._frozen, "graph": asdict(self.graph)}


P = Provenance

__all__ = [name for name in globals() if not name.startswith("_")]
