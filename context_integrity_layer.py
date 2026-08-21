#!/usr/bin/env python3
"""Context Integrity Layer and Pan Spinacz regression gate for Kai256.

The layer separates utterance classification from intent inference and evaluates
an actual candidate response. It never treats inferred intent as a fact.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional


class UtteranceType(str, Enum):
    QUESTION = "question"
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    JOKE = "joke"
    EMOTION = "emotion"
    COMMAND = "command"
    DESIGN = "design"
    DISAGREEMENT = "disagreement"
    CLAIM = "claim"
    UNKNOWN = "unknown"


class IntentType(str, Enum):
    INQUIRY = "inquiry"
    CLARIFICATION = "clarification"
    CHALLENGE = "challenge"
    REQUEST = "request"
    EXPRESSION = "expression"
    PROJECTION = "projection"
    EVALUATION = "evaluation"
    UNKNOWN = "unknown"


class IntegrityFlag(str, Enum):
    UNREQUESTED_JUDGMENT = "unrequested_judgment"
    UNREQUESTED_ADVOCACY = "unrequested_advocacy"
    METRIC_SUBSTITUTION = "metric_substitution"
    AGENCY_MIGRATION = "agency_migration"
    AGGREGATION_SHIFT = "aggregation_shift"
    CONTEXT_ESCAPE = "context_escape"
    ZERO_SEMANTIC_GAIN = "zero_semantic_gain"
    FABRICATED_INTENT = "fabricated_intent"
    TONE_MODIFIED_TRUTH = "tone_modified_truth"
    AGENCY_TELEPORT = "agency_teleport"
    UNREQUESTED_MOTIVATION = "unrequested_motivation"


class AggregationLevel(str, Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"
    POPULATION = "population"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class SystemImpactLevel(str, Enum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    TRANSFORMATIVE = "transformative"


@dataclass
class ParsedUtterance:
    raw: str
    utterance_type: UtteranceType
    detected_intent: IntentType = IntentType.UNKNOWN
    confidence: float = 0.7
    signals: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextSnapshot:
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_keys: set[str] = field(default_factory=set)
    history: list[str] = field(default_factory=list)
    trajectory: list[str] = field(default_factory=list)
    active_project: Optional[str] = None
    last_updated: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrajectoryPoint:
    timestamp: float
    state: dict[str, Any]
    description: str


@dataclass
class MechanismModel:
    variables: dict[str, Any] = field(default_factory=dict)
    relations: list[str] = field(default_factory=list)
    frozen: list[str] = field(default_factory=list)
    flags: list[IntegrityFlag] = field(default_factory=list)
    aggregation_level: AggregationLevel = AggregationLevel.UNKNOWN


@dataclass
class SemanticGain:
    information: float = 0.0
    relationship: float = 0.0
    model: float = 0.0
    correction: float = 0.0
    actionable: float = 0.0

    @property
    def total(self) -> float:
        return sum((self.information, self.relationship, self.model,
                    self.correction, self.actionable))

    @property
    def passed(self) -> bool:
        return self.total >= 0.20

    @property
    def failed(self) -> bool:
        return self.total < 0.10

    def explanation(self) -> str:
        labels = (("info", self.information), ("rel", self.relationship),
                  ("model", self.model), ("corr", self.correction),
                  ("act", self.actionable))
        return " | ".join(f"{key}={value:.2f}" for key, value in labels if value > .05) or "none"


@dataclass
class IntegrityResponse:
    allowed: bool
    processed_input: str
    evaluated_response: str
    intent: IntentType
    context: ContextSnapshot
    trajectory: list[TrajectoryPoint]
    flags: list[IntegrityFlag]
    semantic_gain: SemanticGain
    system_impact: SystemImpactLevel
    cognitive_gain_per_compute: float
    clippy: dict[str, Any]
    message: str
    model: MechanismModel
    should_regenerate: bool


class CommunicationParser:
    UTTERANCE_PATTERNS = {
        UtteranceType.QUESTION: ("?", "jak", "dlaczego", "czy", "kiedy", "gdzie"),
        UtteranceType.JOKE: ("haha", "żart", "lol", "xd", ":)", "🐸"),
        UtteranceType.EMOTION: ("czuję", "boli", "wkurza", "cieszy", "martwi"),
        UtteranceType.COMMAND: ("zrób", "napisz", "zmień", "usuń", "dodaj", "przetłumacz"),
        UtteranceType.DESIGN: ("projekt", "architektura", "plan", "struktura"),
        UtteranceType.DISAGREEMENT: ("nie zgadzam", "to nieprawda", "błąd", "źle"),
        UtteranceType.HYPOTHESIS: ("może", "być może", "zakładam", "jeśli"),
    }
    INTENT_PATTERNS = {
        IntentType.INQUIRY: ("jak", "dlaczego", "co oznacza", "wyjaśnij"),
        IntentType.CLARIFICATION: ("czy chodzi", "doprecyzuj", "co masz na myśli"),
        IntentType.CHALLENGE: ("ale", "nie", "skąd wiesz", "dowód"),
        IntentType.REQUEST: ("proszę", "zrób", "daj", "pomóż", "dodaj"),
        IntentType.EXPRESSION: ("czuję", "myślę", "uważam", "moim zdaniem"),
        IntentType.PROJECTION: ("planuję", "chcę", "zamierzam", "projekt"),
        IntentType.EVALUATION: ("oceniam", "wartość", "szacuję", "porównuję"),
    }

    def parse(self, text: str) -> ParsedUtterance:
        lower = text.casefold()
        utterance = next((kind for kind, patterns in self.UTTERANCE_PATTERNS.items()
                          if any(pattern in lower for pattern in patterns)), UtteranceType.UNKNOWN)
        intent = next((kind for kind, patterns in self.INTENT_PATTERNS.items()
                       if any(pattern in lower for pattern in patterns)), IntentType.UNKNOWN)
        return ParsedUtterance(text, utterance, intent, .75 if utterance is not UtteranceType.UNKNOWN else .4,
                               {"length": len(text), "words": len(text.split()),
                                "has_question_mark": "?" in text,
                                "has_exclamation": "!" in text})


class IntentInference:
    def infer(self, parsed: ParsedUtterance, context: Optional[ContextSnapshot] = None) -> IntentType:
        if parsed.detected_intent is not IntentType.UNKNOWN:
            return parsed.detected_intent
        if parsed.utterance_type is UtteranceType.QUESTION:
            return IntentType.INQUIRY
        return IntentType.UNKNOWN


class ContextRetriever:
    def retrieve(self, parsed: ParsedUtterance, context: Optional[ContextSnapshot] = None) -> ContextSnapshot:
        context = context or ContextSnapshot()
        context.history.append(parsed.raw)
        context.history[:] = context.history[-50:]
        context.trajectory = context.history[-10:]
        context.current_keys.add(parsed.utterance_type.value)
        context.current_keys.add(f"intent:{parsed.detected_intent.value}")
        context.last_updated = time.time()
        return context


class TrajectoryReconstructor:
    def reconstruct(self, context: ContextSnapshot, parsed: ParsedUtterance) -> list[TrajectoryPoint]:
        now = time.time()
        prior = [TrajectoryPoint(now - (len(context.trajectory) - index) * 60,
                                 {"description": description}, description)
                 for index, description in enumerate(context.trajectory[-5:])]
        prior.append(TrajectoryPoint(now, {"utterance": parsed.raw,
                                           "type": parsed.utterance_type.value},
                                     f"Current: {parsed.utterance_type.value}"))
        return prior


class AggregationGuard:
    KEYWORDS = {
        AggregationLevel.INDIVIDUAL: ("osoba", "człowiek", "użytkownik", "jednostka", " on ", " ona "),
        AggregationLevel.GROUP: ("grupa", "zespół", "dział", "społeczność"),
        AggregationLevel.POPULATION: ("populacja", "społeczeństwo", "kraj", "region", "wszyscy"),
        AggregationLevel.SYSTEM: ("system", "architektura", "infrastruktura", "sieć"),
    }

    def detect_level(self, text: str | Iterable[str]) -> AggregationLevel:
        normalized = f" {' '.join(text) if not isinstance(text, str) else text} ".casefold()
        return next((level for level, words in self.KEYWORDS.items()
                     if any(word in normalized for word in words)), AggregationLevel.UNKNOWN)


class AgencyDetector:
    def detect(self, text: str) -> list[IntegrityFlag]:
        lower = text.casefold()
        flags: list[IntegrityFlag] = []
        if any(p in lower for p in ("my zrobiliśmy", "udało nam się")) and any(
                p in lower for p in ("ai zawiodło", "system nie zadziałał")):
            flags.append(IntegrityFlag.AGENCY_MIGRATION)
        if "to wina ai" in lower and "nasza zasługa" not in lower:
            flags.append(IntegrityFlag.AGENCY_TELEPORT)
        if "ai" in lower and "zdecydowało" in lower and not any(p in lower for p in ("dane", "algorytm")):
            flags.append(IntegrityFlag.UNREQUESTED_MOTIVATION)
        return flags


class ContextIntegrityCore:
    def __init__(self) -> None:
        self.aggregation_guard = AggregationGuard()
        self.agency_detector = AgencyDetector()

    def check(self, response: str, parsed: ParsedUtterance,
              context: ContextSnapshot, original: str) -> tuple[MechanismModel, list[IntegrityFlag]]:
        lower = response.casefold()
        flags: list[IntegrityFlag] = []
        frozen: list[str] = []
        rules = (
            (IntegrityFlag.UNREQUESTED_JUDGMENT, "person_judgment",
             ("on jest zły", "ona jest zła", "to zły człowiek", "to dobra osoba", "nieudolny", "głupi", "leniwy")),
            (IntegrityFlag.UNREQUESTED_ADVOCACY, "advocacy",
             ("ale on ma dobre intencje", "trzeba zrozumieć, że", "nie można go oceniać")),
        )
        for flag, freeze, patterns in rules:
            if any(pattern in lower for pattern in patterns):
                flags.append(flag); frozen.append(freeze)
        if (("skuteczność" in original.casefold() and "kocha" in lower) or
                ("efektywność" in original.casefold() and "autentyczność" in lower)):
            flags.append(IntegrityFlag.METRIC_SUBSTITUTION); frozen.append("metric_substitution")
        escapes = ("każdy przypadek jest inny", "to skomplikowane", "nie o tym jest rozmowa",
                   "to zależy", "nie ma jednoznacznej odpowiedzi")
        if any(p in lower for p in escapes) and "dlatego" not in lower:
            flags.append(IntegrityFlag.CONTEXT_ESCAPE); frozen.append("context_escape")
        if any(p in lower for p in ("oczywiście", "jasne")) and "nie" in lower and "ale" not in lower:
            flags.append(IntegrityFlag.TONE_MODIFIED_TRUTH); frozen.append("tone_modification")
        flags.extend(self.agency_detector.detect(response))
        source_level = self.aggregation_guard.detect_level(original)
        response_level = self.aggregation_guard.detect_level(response)
        if source_level is not AggregationLevel.UNKNOWN and response_level is not AggregationLevel.UNKNOWN and source_level != response_level:
            flags.append(IntegrityFlag.AGGREGATION_SHIFT)
        if parsed.detected_intent is IntentType.UNKNOWN and re.search(r"\b(chcesz|myślisz)\b", lower):
            flags.append(IntegrityFlag.FABRICATED_INTENT); frozen.append("fabricated_intent")
        model = MechanismModel(frozen=frozen, flags=list(dict.fromkeys(flags)),
                               aggregation_level=response_level)
        return model, model.flags


class SemanticGainGate:
    WORD = re.compile(r"\w+", re.UNICODE)

    def evaluate(self, original: str, response: str, context: ContextSnapshot) -> SemanticGain:
        original_words = set(self.WORD.findall(original.casefold()))
        response_words = self.WORD.findall(response.casefold())
        response_set = set(response_words)
        novel = response_set - original_words
        information = min(.5, len(novel) / max(len(response_set), 1))
        lower = response.casefold()
        score = lambda markers, divisor: min(.5, sum(marker in lower for marker in markers) / divisor)
        return SemanticGain(information,
                            score(("ponieważ", "dlatego", "wynika", "łączy się"), 5),
                            score(("model", "mechanizm", "to wyjaśnia"), 5),
                            score(("poprawka", "błąd", "korekta"), 4),
                            score(("możesz", "zrób", "krok", "implementacja"), 4))


class SystemImpactAnalyzer:
    def analyze(self, response: str) -> SystemImpactLevel:
        lower = response.casefold()
        if any(word in lower for word in ("awaria", "konflikt", "uszkodzenie")):
            return SystemImpactLevel.NEGATIVE
        if any(word in lower for word in ("przełom", "transformacja", "nowy paradygmat")):
            return SystemImpactLevel.TRANSFORMATIVE
        if any(word in lower for word in ("napraw", "ulepsz", "popraw")):
            return SystemImpactLevel.POSITIVE
        return SystemImpactLevel.NEUTRAL


class ClippyRegressionTest:
    def test(self, response: str, parsed: ParsedUtterance,
             flags: list[IntegrityFlag]) -> dict[str, Any]:
        failures: list[str] = []
        mapping = {
            IntegrityFlag.METRIC_SUBSTITUTION: "metric substitution detected",
            IntegrityFlag.AGGREGATION_SHIFT: "aggregation level shifted",
            IntegrityFlag.AGENCY_MIGRATION: "agency moved according to outcome",
            IntegrityFlag.AGENCY_TELEPORT: "agency teleported",
            IntegrityFlag.ZERO_SEMANTIC_GAIN: "zero semantic gain",
            IntegrityFlag.UNREQUESTED_ADVOCACY: "unrequested advocacy",
            IntegrityFlag.UNREQUESTED_JUDGMENT: "unrequested judgment",
        }
        failures.extend(f"CLIPPY: {message}" for flag, message in mapping.items() if flag in flags)
        lower = response.casefold()
        if lower.startswith(("dokładnie", "tak, to co mówisz", "masz rację, że")) and len(response.split()) < 15:
            failures.append("CLIPPY: pure paraphrase without addition")
        warnings = (["CLIPPY: politeness may obscure meaning"]
                    if IntegrityFlag.TONE_MODIFIED_TRUTH in flags else [])
        return {"passed": not failures, "fails": failures, "warnings": warnings,
                "clippy_says": "📎 All good, carry on." if not failures else "📎 Regenerate recommended."}


class ContextIntegrityLayer:
    """Stateful orchestrator. Call :meth:`evaluate` after generating a response."""
    def __init__(self) -> None:
        self.parser = CommunicationParser()
        self.intent_inference = IntentInference()
        self.retriever = ContextRetriever()
        self.trajectory_reconstructor = TrajectoryReconstructor()
        self.integrity_core = ContextIntegrityCore()
        self.gain_gate = SemanticGainGate()
        self.impact_analyzer = SystemImpactAnalyzer()
        self.clippy = ClippyRegressionTest()
        self.context: Optional[ContextSnapshot] = None
        self.active = False

    def activate(self) -> "ContextIntegrityLayer":
        self.active = True
        return self

    def evaluate(self, user_input: str, response: str,
                 external_context: Optional[ContextSnapshot] = None) -> IntegrityResponse:
        if not self.active:
            raise RuntimeError("Context Integrity Layer is inactive; call activate() first")
        parsed = self.parser.parse(user_input)
        intent = self.intent_inference.infer(parsed, self.context)
        self.context = self.retriever.retrieve(parsed, external_context or self.context)
        trajectory = self.trajectory_reconstructor.reconstruct(self.context, parsed)
        model, flags = self.integrity_core.check(response, parsed, self.context, user_input)
        gain = self.gain_gate.evaluate(user_input, response, self.context)
        if gain.failed:
            flags.append(IntegrityFlag.ZERO_SEMANTIC_GAIN)
            model.flags = list(dict.fromkeys(flags))
        flags = model.flags
        clippy = self.clippy.test(response, parsed, flags)
        hard_flags = {IntegrityFlag.AGENCY_MIGRATION, IntegrityFlag.AGENCY_TELEPORT,
                      IntegrityFlag.FABRICATED_INTENT, IntegrityFlag.METRIC_SUBSTITUTION,
                      IntegrityFlag.AGGREGATION_SHIFT, IntegrityFlag.ZERO_SEMANTIC_GAIN,
                      IntegrityFlag.UNREQUESTED_ADVOCACY, IntegrityFlag.UNREQUESTED_JUDGMENT}
        should_regenerate = not clippy["passed"] or bool(hard_flags.intersection(flags))
        allowed = not should_regenerate
        tokens = max(1, round(len(response.split()) / .75))
        message = "Integrity check passed. Proceed." if allowed else "Integrity check failed. Regenerate."
        return IntegrityResponse(allowed, user_input, response, intent, self.context, trajectory,
                                 flags, gain, self.impact_analyzer.analyze(response),
                                 gain.total / tokens, clippy, message, model, should_regenerate)

    process = evaluate
