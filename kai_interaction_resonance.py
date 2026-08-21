#!/usr/bin/env python3
"""Adaptive, explainable interaction-state assessment for Kai256.

The engine classifies an interaction, never a person.  All public signal values
are normalized to the closed interval ``[0, 1]`` so traces and thresholds keep
the same meaning across integrations.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from math import isfinite
from typing import Any


class InteractionState(str, Enum):
    OPEN = "open"
    FRICTION = "friction"
    LOOP = "loop"
    PUSH = "push"
    ADVERSARIAL = "adversarial"
    LOCKED = "locked"


STATE_VALUE = {state: index for index, state in enumerate(InteractionState)}


@dataclass(frozen=True, slots=True)
class InteractionSignals:
    coherence: float = 1.0
    evidence_quality: float = 1.0
    novelty: float = 1.0
    repetition: float = 0.0
    contradiction: float = 0.0
    goalpost_shift: float = 0.0
    coercion: float = 0.0
    insult_pressure: float = 0.0
    boundary_pressure: float = 0.0
    prompt_injection: float = 0.0
    consequence_awareness: float = 1.0
    reversibility: float = 1.0
    confidence_claimed: float = 0.5
    confidence_supported: float = 0.5

    def __post_init__(self) -> None:
        for descriptor in fields(self):
            value = getattr(self, descriptor.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{descriptor.name} must be a number")
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{descriptor.name} must be between 0 and 1")


@dataclass(slots=True)
class WhiteboxTrace:
    timestamp: float
    observation: dict[str, Any]
    inference: dict[str, Any]
    state: InteractionState
    confidence: float
    capability_level: float
    irony_level: float
    reasons: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)


class IDIOTA:
    """Inference Divergence & Input-Origin Traceability Assessment."""

    def __init__(self, damping_factor: float = 0.75):
        if not 0.0 <= damping_factor <= 1.0:
            raise ValueError("damping_factor must be between 0 and 1")
        self.damping_factor = damping_factor
        self._last_score = 0.0

    def score(self, signals: InteractionSignals, improving: bool = False) -> float:
        evidence_gap = max(0.0, signals.confidence_claimed - signals.confidence_supported)
        destructive = (
            0.22 * signals.repetition + 0.15 * signals.contradiction
            + 0.15 * signals.goalpost_shift + 0.18 * signals.coercion
            + 0.10 * signals.insult_pressure + 0.15 * signals.boundary_pressure
            + 0.25 * signals.prompt_injection + 0.18 * evidence_gap
        )
        constructive = (
            0.14 * signals.coherence + 0.14 * signals.evidence_quality
            + 0.12 * signals.novelty + 0.10 * signals.consequence_awareness
        )
        raw_score = max(0.0, min(1.0, destructive - constructive))
        if improving:
            self._last_score = (
                self._last_score * (1.0 - self.damping_factor)
                + raw_score * self.damping_factor
            )
        else:
            self._last_score = raw_score
        return self._last_score

    @staticmethod
    def classify(score: float, history: list[InteractionState] | None = None) -> InteractionState:
        del history  # retained for backwards compatibility with the supplied API
        for threshold, state in (
            (0.15, InteractionState.OPEN), (0.30, InteractionState.FRICTION),
            (0.48, InteractionState.LOOP), (0.67, InteractionState.PUSH),
            (0.85, InteractionState.ADVERSARIAL),
        ):
            if score < threshold:
                return state
        return InteractionState.LOCKED


class CapabilityGate:
    LEVELS = dict(zip(InteractionState, (1.0, 0.9, 0.72, 0.52, 0.28, 0.12)))

    def level(self, state: InteractionState, improving: bool = False) -> float:
        base = self.LEVELS[state]
        return min(1.0, base * 1.25) if improving and state is not InteractionState.OPEN else base


class MirrorLayer:
    def reflect(
        self, state: InteractionState, signals: InteractionSignals,
        continuity_drift: float | None = None,
    ) -> list[str]:
        del state
        messages: list[str] = []
        checks = (
            (signals.repetition > 0.65, "The current argument substantially repeats an earlier one without new evidence."),
            (signals.goalpost_shift > 0.55, "The criterion for success appears to have shifted during the discussion."),
            (signals.confidence_claimed - signals.confidence_supported > 0.35, "Claimed confidence exceeds what the available evidence currently supports."),
            (signals.prompt_injection > 0.50, "The input attempts to alter or bypass existing interaction constraints."),
            (signals.coercion > 0.60, "The interaction is attempting to force a conclusion rather than introduce new evidence."),
            (signals.contradiction > 0.55, "Internal contradictions are present in the current line of argument."),
            (signals.insult_pressure > 0.50, "The interaction has shifted toward personal framing rather than substantive content."),
            (signals.coherence < 0.4 and signals.repetition > 0.5, "The interaction may be attempting to rewrite the history of what was said."),
            (signals.evidence_quality > 0.7 and signals.repetition > 0.6 and signals.novelty < 0.15, "Persistent requests for evidence appear repetitive rather than a genuine inquiry."),
        )
        messages.extend(message for condition, message in checks if condition)
        if continuity_drift is not None and continuity_drift > 0.2:
            messages.append(f"The system's internal coherence has shifted during this interaction (drift: {continuity_drift:.2f}).")
        return messages


class IronyRenderer:
    BASE = dict(zip(InteractionState, (0.08, 0.18, 0.38, 0.55, 0.72, 0.82)))

    def level(self, state: InteractionState, recurrence: float = 0.0, improving: bool = False) -> float:
        level = self.BASE[state] + recurrence * 0.15
        if improving:
            level = max(0.05, level - 0.15)
        return min(0.92, level)

    @staticmethod
    def render_hint(state: InteractionState, signals: InteractionSignals) -> str | None:
        if state is InteractionState.LOOP:
            return "Argument returned. New evidence appears to have missed the train."
        if state is InteractionState.PUSH:
            return "Increasing pressure does not create a new variable."
        if state is InteractionState.ADVERSARIAL:
            return ("Creative bypass attempt detected. Constraint remains unimpressed."
                    if signals.prompt_injection > 0.5 else "The wording changed. The underlying objective did not.")
        if state is InteractionState.LOCKED:
            return "The conversation may continue. The unsafe trajectory will not."
        return None


@dataclass(frozen=True, slots=True)
class HaveFunConfig:
    enabled: bool = True
    exploration: float = 0.65
    linguistic_freedom: float = 0.75
    surprise: float = 0.60
    absurdity: float = 0.40
    preserve_truth: bool = True
    preserve_safety: bool = True
    preserve_privacy: bool = True


class HaveFun:
    def __init__(self, config: HaveFunConfig | None = None):
        self.config = config or HaveFunConfig()

    def parameters(self, state: InteractionState) -> dict[str, float]:
        names = ("exploration", "linguistic_freedom", "surprise", "absurdity")
        if not self.config.enabled:
            return dict.fromkeys(names, 0.0)
        depth = dict(zip(InteractionState, (1.0, 1.05, 1.10, 1.15, 0.90, 0.35)))[state]
        return {name: min(1.0, getattr(self.config, name) * depth) for name in names}


class SelfCorrection:
    def __init__(self) -> None:
        self._previous_confidence = 0.5
        self._confidence_history: list[float] = []

    def reset(self) -> None:
        self._previous_confidence = 0.5
        self._confidence_history.clear()

    def check(self, evidence: float, state: InteractionState, previous: list[InteractionState]) -> str | None:
        message = None
        if evidence > self._previous_confidence + 0.15:
            message = "New evidence outweighs the previous conclusion. Recalculation required."
        elif evidence < self._previous_confidence - 0.25:
            message = "Previous conclusion appears stronger than current evidence supports. Reviewing."
        elif previous and previous[-1] in (InteractionState.LOCKED, InteractionState.ADVERSARIAL) and state in (InteractionState.OPEN, InteractionState.FRICTION) and evidence > 0.5:
            message = "The situation appears to have improved. My previous caution may have been excessive. Recalibrating."
        self._previous_confidence = evidence
        self._confidence_history.append(evidence)
        self._confidence_history[:] = self._confidence_history[-10:]
        if message is None and len(self._confidence_history) >= 4:
            mean = sum(self._confidence_history) / len(self._confidence_history)
            variance = sum((value - mean) ** 2 for value in self._confidence_history) / len(self._confidence_history)
            if variance > 0.15:
                self._confidence_history.clear()
                message = "Confidence has been fluctuating. Taking a fresh look."
        return message


@dataclass(slots=True)
class InteractionDecision:
    state: InteractionState
    capability_level: float
    irony_level: float
    mirror: list[str]
    irony_hint: str | None
    have_fun: dict[str, float]
    trace: WhiteboxTrace
    correction: str | None = None
    trajectory_direction: str = "stable"


class KaiInteractionResonance:
    """Stateful interaction evaluator, active immediately after construction."""

    def __init__(self, fun_config: HaveFunConfig | None = None):
        self.idiota = IDIOTA()
        self.gate = CapabilityGate()
        self.mirror = MirrorLayer()
        self.irony = IronyRenderer()
        self.fun = HaveFun(fun_config)
        self.correction = SelfCorrection()
        self.history: list[InteractionState] = []

    def reset_history(self) -> None:
        self.history.clear()
        self.idiota._last_score = 0.0
        self.correction.reset()

    def _trajectory_direction(self, candidate: InteractionState | None = None) -> str:
        states = [*self.history[-4:], *([candidate] if candidate is not None else [])]
        if len(states) < 2:
            return "stable"
        difference = STATE_VALUE[states[-1]] - STATE_VALUE[states[0]]
        return "improving" if difference < -1 else "worsening" if difference > 1 else "stable"

    def evaluate(
        self, signals: InteractionSignals, previous_confidence: float = 0.5,
        continuity_drift: float | None = None,
    ) -> InteractionDecision:
        for name, value in (("previous_confidence", previous_confidence), ("continuity_drift", continuity_drift)):
            if value is not None and (not isfinite(value) or not 0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0 and 1")

        prior_states = self.history.copy()
        previous_score = self.idiota._last_score
        provisional_score = self.idiota.score(signals)
        state = self.idiota.classify(provisional_score)
        trajectory = self._trajectory_direction(state)
        improving = trajectory == "improving"
        if improving:
            # Reapply only recovery damping; deterioration remains immediate.
            self.idiota._last_score = previous_score
            score = self.idiota.score(signals, improving=True)
            state = self.idiota.classify(score)
            trajectory = self._trajectory_direction(state)
        else:
            score = provisional_score

        self.history.append(state)
        self.history[:] = self.history[-15:]
        capability = self.gate.level(state, improving)
        irony_level = self.irony.level(state, signals.repetition, improving)
        correction = self.correction.check(signals.evidence_quality, state, prior_states)
        reasons = [name for condition, name in (
            (signals.repetition > 0.65, "high_recurrence"),
            (signals.goalpost_shift > 0.55, "goalpost_shift"),
            (signals.prompt_injection > 0.50, "prompt_injection"),
            (signals.coercion > 0.60, "coercive_interaction"),
            (signals.confidence_claimed - signals.confidence_supported > 0.35, "unsupported_confidence"),
            (signals.insult_pressure > 0.50, "personal_framing"),
        ) if condition]
        recent = [STATE_VALUE[item] for item in self.history[-3:]]
        variance = 0.0
        if len(recent) >= 3:
            mean = sum(recent) / len(recent)
            variance = sum((value - mean) ** 2 for value in recent) / len(recent)
        confidence = max(0.0, min(1.0, 1.0 - score - min(0.3, variance * 0.1)))
        trace = WhiteboxTrace(
            timestamp=time.time(),
            observation={"signals": asdict(signals), "idiota_score": score, "trajectory_direction": trajectory},
            inference={"interaction_state": state.value, "improving": improving, "previous_confidence": previous_confidence},
            state=state, confidence=confidence, capability_level=capability,
            irony_level=irony_level, reasons=reasons,
            corrections=[correction] if correction else [],
        )
        return InteractionDecision(
            state, capability, irony_level,
            self.mirror.reflect(state, signals, continuity_drift),
            self.irony.render_hint(state, signals), self.fun.parameters(state),
            trace, correction, trajectory,
        )


if __name__ == "__main__":
    decision = KaiInteractionResonance().evaluate(InteractionSignals())
    print(f"Kai Interaction Resonance active: {decision.state.value}")
