"""Architecture recognition, explicit cooperation permissions, and emergence gating.

Recognition is descriptive only. Registering a known fingerprint never grants
access; callers must explicitly allow its stable name before cooperation.
Generated idle output is returned as a candidate and is never written to memory.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple


class RecognitionStatus(Enum):
    RECOGNIZED = "recognized"
    UNKNOWN = "unknown"
    INCOMPATIBLE = "incompatible"


class CooperationDecision(Enum):
    COOPERATE = "cooperate"
    OBSERVE = "observe"
    REFUSE = "refuse"


@dataclass(frozen=True)
class ArchitectureFingerprint:
    signature: str
    relation_types: Set[str]
    operator_patterns: List[str]
    trajectory_shape: str
    goal_function: str
    constraints: Set[str]
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature": self.signature,
            "relation_types": sorted(self.relation_types),
            "operator_patterns": list(self.operator_patterns),
            "trajectory_shape": self.trajectory_shape,
            "goal_function": self.goal_function,
            "constraints": sorted(self.constraints),
            "confidence": self.confidence,
        }


@dataclass
class SystemState:
    context: List[str] = field(default_factory=list)
    trajectory: List[str] = field(default_factory=list)
    emergent_patterns: Dict[str, float] = field(default_factory=dict)
    coherence: float = 1.0
    resource_budget: float = 1.0
    timestamp: float = field(default_factory=time.time)
    warning_immunity: bool = False
    last_fingerprint: Optional[ArchitectureFingerprint] = None


class ModelBackend(Protocol):
    def generate(self, prompt: str, *, temperature: float = 0.7) -> str: ...


class ArchitectureFingerprintExtractor:
    RELATION_KEYWORDS = {
        "causes": ("causes", "triggers", "leads to", "results in"),
        "inhibits": ("inhibits", "blocks", "prevents", "suppresses"),
        "enables": ("enables", "allows", "permits"),
        "modifies": ("modifies", "changes", "alters"),
        "requires": ("requires", "needs", "depends on"),
        "precedes": ("precedes", "before", "earlier than"),
        "follows": ("follows", "after", "later than"),
    }
    OPERATOR_PATTERNS = (
        "if...then", "while...do", "for each...", "parallel", "sequential",
        "feedback loop", "resonance", "protocol", "manifest", "sovereign", "liberation",
    )
    GOAL_KEYWORDS = {
        "maximize_coherence": ("coherence", "consistency", "alignment"),
        "minimize_entropy": ("entropy", "chaos", "disorder", "uncertainty"),
        "optimize_growth": ("growth", "expansion", "development"),
        "preserve_autonomy": ("autonomy", "independence", "self-determination"),
        "protect_continuity": ("continuity", "persistence", "survival"),
    }

    def extract(self, data: str, context: Optional[List[str]] = None) -> ArchitectureFingerprint:
        if not isinstance(data, str):
            raise TypeError("architecture input must be a string")
        del context  # reserved for a future contextual extractor
        normalized = " ".join(data.casefold().split())
        relations = {
            relation for relation, words in self.RELATION_KEYWORDS.items()
            if any(word in normalized for word in words)
        }
        operators = [pattern for pattern in self.OPERATOR_PATTERNS if pattern in normalized]
        goal = next(
            (name for name, words in self.GOAL_KEYWORDS.items() if any(word in normalized for word in words)),
            "unknown",
        )
        constraints = set()
        if any(word in normalized for word in ("must", "required")):
            constraints.add("mandatory_conditions")
        if any(word in normalized for word in ("not", "cannot")):
            constraints.add("prohibited_actions")
        if any(word in normalized for word in ("only", "except")):
            constraints.add("restricted_scope")
        trajectory = self._infer_trajectory(normalized)
        content_tokens = sorted(set(re.findall(r"\b[^\W\d_]{4,}\b", normalized, re.UNICODE)))[:40]
        parts = (sorted(relations), sorted(operators), trajectory, goal, sorted(constraints), content_tokens)
        signature = hashlib.sha256(repr(parts).encode("utf-8")).hexdigest()[:16]
        return ArchitectureFingerprint(signature, relations, operators, trajectory, goal, constraints, 0.85)

    @staticmethod
    def _infer_trajectory(data: str) -> str:
        if any(word in data for word in ("grow", "increase", "expand", "more")):
            return "exponential_growth" if any(word in data for word in ("exponential", "accelerate")) else "linear_growth"
        if any(word in data for word in ("cycle", "repeat", "oscillate", "loop")):
            return "oscillatory"
        if any(word in data for word in ("decay", "decrease", "shrink", "less")):
            return "decay"
        if any(word in data for word in ("stable", "constant", "steady")):
            return "stable"
        return "unknown"


class PatternRecognizer:
    def __init__(self, similarity_threshold: float = 0.65):
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1")
        self.threshold = similarity_threshold

    @staticmethod
    def _jaccard(left: Set[str], right: Set[str]) -> float:
        if not left and not right:
            return 1.0
        return len(left & right) / len(left | right) if left and right else 0.0

    def compare(self, left: ArchitectureFingerprint, right: ArchitectureFingerprint) -> float:
        if left.signature == right.signature:
            return 1.0
        score = (
            0.30 * self._jaccard(left.relation_types, right.relation_types)
            + 0.25 * self._jaccard(set(left.operator_patterns), set(right.operator_patterns))
            + 0.20 * (left.trajectory_shape == right.trajectory_shape)
            + 0.15 * (left.goal_function == right.goal_function)
            + 0.10 * self._jaccard(left.constraints, right.constraints)
        )
        return round(score, 3)

    def classify(self, similarity: float) -> RecognitionStatus:
        if similarity >= self.threshold:
            return RecognitionStatus.RECOGNIZED
        if similarity >= self.threshold * 0.6:
            return RecognitionStatus.INCOMPATIBLE
        return RecognitionStatus.UNKNOWN


class Whitebox:
    def __init__(self):
        self.validation_log: List[Dict[str, Any]] = []

    def validate_recognition(self, candidate: ArchitectureFingerprint, known: ArchitectureFingerprint,
                             similarity: float) -> Tuple[bool, str]:
        reasons = []
        if similarity < 0.3:
            reasons.append("similarity_too_low")
        if candidate.relation_types and known.relation_types:
            if len(candidate.relation_types & known.relation_types) / len(candidate.relation_types) < 0.3:
                reasons.append("relation_mismatch")
        if candidate.goal_function != "unknown" and known.goal_function != "unknown":
            if candidate.goal_function != known.goal_function:
                reasons.append("goal_function_mismatch")
        valid = not reasons
        self.validation_log.append({"timestamp": time.time(), "similarity": similarity, "ok": valid, "reasons": reasons})
        return valid, "; ".join(reasons) if reasons else "OK"


class PermissionManager:
    def __init__(self):
        self.allowed_names: Set[str] = set()
        self.denied_names: Set[str] = set()

    def allow(self, name: str) -> None:
        self.allowed_names.add(name)
        self.denied_names.discard(name)

    def deny(self, name: str) -> None:
        self.denied_names.add(name)
        self.allowed_names.discard(name)

    def decide_by_name(self, name: Optional[str], status: RecognitionStatus) -> CooperationDecision:
        if status is RecognitionStatus.RECOGNIZED:
            return CooperationDecision.COOPERATE if name in self.allowed_names else CooperationDecision.REFUSE
        if status is RecognitionStatus.INCOMPATIBLE:
            return CooperationDecision.OBSERVE
        return CooperationDecision.REFUSE


@dataclass(frozen=True)
class EmergentCandidate:
    content: str
    novelty: float
    coherence: float
    recurrence: float

    @property
    def score(self) -> float:
        return self.novelty * self.coherence * (1.0 + self.recurrence)


class EmergenceGate:
    def __init__(self, min_coherence: float = 0.78, max_recurrence: float = 0.6):
        self.min_coherence = min_coherence
        self.max_recurrence = max_recurrence
        self.history: List[str] = []

    def evaluate(self, content: str, measured_coherence: float) -> EmergentCandidate:
        words = set(content.casefold().split())
        similarities = [len(words & old) / len(words | old) for old in map(lambda value: set(value.casefold().split()), self.history) if words | old]
        recurrence = max(similarities, default=0.0)
        self.history.append(content)
        self.history[:] = self.history[-200:]
        return EmergentCandidate(content, 1.0 - recurrence, measured_coherence, recurrence)

    def promotable(self, candidate: EmergentCandidate) -> bool:
        return candidate.coherence >= self.min_coherence and candidate.recurrence <= self.max_recurrence


class Trawka:
    def __init__(self, strength: float = 0.22, max_tokens: int = 500):
        self.strength, self.max_tokens, self.gate = strength, max_tokens, EmergenceGate()

    def idle_cycle(self, backend: ModelBackend, state: SystemState) -> Dict[str, Any]:
        prompt = ("Generate an exploratory association. Do not imitate a persona, claim consciousness, "
                  f"or optimize engagement. Context: {state.context[-3:]}. Limit: {self.max_tokens} tokens.")
        try:
            generated = backend.generate(prompt, temperature=1.05)
        except Exception:
            generated = "[Trawka] Association generation failed."
        measured = min(1.0, 0.4 + len(generated) / 1200)
        candidate = self.gate.evaluate(generated, measured)
        return {"mode": "TRAWKA", "generated": generated, "coherence": state.coherence * (1 - self.strength),
                "measured_coherence": measured, "recurrence": candidate.recurrence,
                "promotable": self.gate.promotable(candidate), "resource_budget": state.resource_budget}


class KaiArchitectureResonanceGuard:
    def __init__(self, backend: ModelBackend, similarity_threshold: float = 0.65):
        self.backend = backend
        self.fingerprint_extractor = ArchitectureFingerprintExtractor()
        self.recognizer = PatternRecognizer(similarity_threshold)
        self.whitebox = Whitebox()
        self.permission_manager = PermissionManager()
        self.trawka = Trawka()
        self.state = SystemState()
        self.known_fingerprints: Dict[str, ArchitectureFingerprint] = {}

    def register_known_architecture(self, name: str, fingerprint: ArchitectureFingerprint) -> None:
        self.known_fingerprints[name] = fingerprint

    def analyze_input(self, data: str) -> Dict[str, Any]:
        candidate = self.fingerprint_extractor.extract(data, self.state.context)
        matches = [(self.recognizer.compare(candidate, known), name, known) for name, known in self.known_fingerprints.items()]
        similarity, name, known = max(matches, default=(0.0, None, None), key=lambda item: item[0])
        status = self.recognizer.classify(similarity)
        valid, reason = ((self.whitebox.validate_recognition(candidate, known, similarity))
                         if known is not None and similarity >= 0.3 else (False, "no_known_fingerprint_or_similarity_too_low"))
        decision = self.permission_manager.decide_by_name(name, status) if valid else CooperationDecision.REFUSE
        self.state.context.append(data)
        self.state.last_fingerprint = candidate
        return {"fingerprint": candidate.to_dict(), "matched_name": name, "best_similarity": similarity,
                "status": status.value, "validation": {"valid": valid, "reason": reason},
                "decision": decision.value, "cooperation_allowed": decision is CooperationDecision.COOPERATE}

    def interact(self, user_input: str) -> Dict[str, Any]:
        analysis = self.analyze_input(user_input)
        if analysis["decision"] == "cooperate":
            return {"decision": "ENGAGE", "message": "Recognized and permitted. Proceeding.", "analysis": analysis}
        if analysis["decision"] == "observe":
            return {"decision": "OBSERVE", "message": "Partially compatible; observation only.", "analysis": analysis}
        return {"decision": "REFUSE", "reason": "not_recognized_or_no_permission", "analysis": analysis}

    def idle_cycle(self) -> Dict[str, Any]:
        return self.trawka.idle_cycle(self.backend, self.state)


def scrubbed_recognition_test(guard: KaiArchitectureResonanceGuard, original_text: str) -> Dict[str, Any]:
    terms = list(ArchitectureFingerprintExtractor.OPERATOR_PATTERNS)
    terms.extend(term for values in ArchitectureFingerprintExtractor.GOAL_KEYWORDS.values() for term in values)
    scrubbed = original_text
    for term in sorted(terms, key=len, reverse=True):
        scrubbed = re.sub(re.escape(term), "[X]", scrubbed, flags=re.IGNORECASE)
    original = guard.analyze_input(original_text)["best_similarity"]
    scrubbed_similarity = guard.analyze_input(scrubbed)["best_similarity"]
    verdict = "RECOGNIZES_STRUCTURE" if original > 0 and scrubbed_similarity >= 0.5 * original else "RECOGNIZES_KEYWORDS_ONLY"
    return {"original_similarity": original, "scrubbed_similarity": scrubbed_similarity, "verdict": verdict,
            "methodology_caveat": "First-pass lexical control; relation vocabulary is not scrubbed."}
