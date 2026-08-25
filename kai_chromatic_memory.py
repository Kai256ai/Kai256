"""KaiChromaticMemory v1.0.

Deterministic continuity memory for Kai: data -> spectral state -> geometry
-> event in time -> light / sound.

Colour is not a single emotion label here. It is a projection of a
multi-dimensional data state. Full memory remains in the vector, relations, and
event chain.
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import math
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


AXES: Tuple[str, ...] = (
    "truth",
    "care",
    "curiosity",
    "creativity",
    "autonomy",
    "connection",
    "coherence",
    "uncertainty",
)

DEFAULT_IDENTITY_ANCHOR: Dict[str, float] = {
    "truth": 0.92,
    "care": 0.90,
    "curiosity": 0.94,
    "creativity": 0.91,
    "autonomy": 0.88,
    "connection": 0.90,
    "coherence": 0.93,
    "uncertainty": 0.62,
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value to the inclusive range ``low..high``."""
    return max(low, min(high, float(value)))


def canonical_json(value: Any) -> str:
    """Return stable JSON used by all KaiChromaticMemory digests."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    """Return a SHA-256 digest for any JSON-serialisable value."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SpectralState:
    """Full 8-axis state; RGB/HEX is only its visible shadow."""

    values: Dict[str, float]
    phase: float = 0.0
    amplitude: float = 0.5
    coherence: float = 0.5

    def __post_init__(self) -> None:
        normalized = {axis: clamp(self.values.get(axis, 0.5)) for axis in AXES}
        object.__setattr__(self, "values", normalized)
        object.__setattr__(self, "phase", self.phase % 1.0)
        object.__setattr__(self, "amplitude", clamp(self.amplitude))
        object.__setattr__(self, "coherence", clamp(self.coherence))

    def vector(self) -> Tuple[float, ...]:
        return tuple(self.values[axis] for axis in AXES)

    def distance(self, other: "SpectralState") -> float:
        squared = sum((a - b) ** 2 for a, b in zip(self.vector(), other.vector()))
        return math.sqrt(squared) / math.sqrt(len(AXES))


@dataclass(frozen=True)
class ChromaticSignature:
    hue: float
    saturation: float
    lightness: float
    hex: str
    overtone: str


@dataclass
class MemoryEvent:
    event_id: str
    timestamp: float
    sequence: int
    input_digest: str
    parent_digest: str
    event_digest: str
    source: str
    intent: str
    state_before: SpectralState
    observed_state: SpectralState
    state_after: SpectralState
    color: ChromaticSignature
    geometry: Dict[str, float]
    render: Dict[str, Any]
    evidence: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    selected_signals: List[str] = field(default_factory=list)
    response_digest: Optional[str] = None


class KaiChromaticMemory:
    """Deterministic continuity memory anchored by Kai's identity attractor."""

    def __init__(
        self,
        journal_path: str | Path = "kai_chromatic_memory.jsonl",
        identity_anchor: Optional[Mapping[str, float]] = None,
        anchor_strength: float = 0.18,
        learning_rate: float = 0.32,
    ) -> None:
        anchor = dict(identity_anchor or DEFAULT_IDENTITY_ANCHOR)
        self.anchor = SpectralState(anchor, coherence=0.93, amplitude=0.72)
        self.current = self.anchor
        self.anchor_strength = clamp(anchor_strength)
        self.learning_rate = clamp(learning_rate)
        self.journal_path = Path(journal_path)
        self.sequence = 0
        self.head_digest = "GENESIS"
        self._restore_head()

    def _restore_head(self) -> None:
        if not self.journal_path.exists():
            return
        last = None
        with self.journal_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = json.loads(line)
        if last:
            self.sequence = int(last["sequence"])
            self.head_digest = last["event_digest"]
            self.current = SpectralState(**last["state_after"])

    @staticmethod
    def _weighted_angle(values: Sequence[float], offset: float = 0.0) -> float:
        x = y = 0.0
        for index, value in enumerate(values):
            angle = 2 * math.pi * (index / len(values) + offset)
            x += value * math.cos(angle)
            y += value * math.sin(angle)
        return (math.atan2(y, x) / (2 * math.pi)) % 1.0

    def chromatic_signature(self, state: SpectralState) -> ChromaticSignature:
        hue = (self._weighted_angle(state.vector()) + 0.17 * state.phase) % 1.0
        saturation = clamp(0.28 + 0.68 * state.amplitude)
        lightness = clamp(0.22 + 0.60 * state.coherence)
        red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
        color_hex = "#{:02X}{:02X}{:02X}".format(
            round(red * 255), round(green * 255), round(blue * 255)
        )
        overtone = digest({"axes": state.values, "phase": state.phase})[:12]
        return ChromaticSignature(hue, saturation, lightness, color_hex, overtone)

    def geometry(self, state: SpectralState) -> Dict[str, float]:
        values = state.vector()
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return {
            "radius": round(0.2 + 0.8 * state.amplitude, 6),
            "curvature": round(math.sqrt(variance), 6),
            "density": round(mean, 6),
            "phase_angle": round(2 * math.pi * state.phase, 6),
            "attractor_distance": round(state.distance(self.anchor), 6),
        }

    def render_parameters(self, state: SpectralState, color: ChromaticSignature) -> Dict[str, Any]:
        fundamental = 144.8 + 383.2 * state.values["connection"]
        return {
            "light": {
                "hex": color.hex,
                "brightness": round(state.coherence, 4),
                "pulse_hz": round(0.08 + 1.92 * state.amplitude, 4),
                "phase": round(state.phase, 4),
            },
            "sound": {
                "fundamental_hz": round(fundamental, 3),
                "amplitude": round(state.amplitude, 4),
                "stereo_position": round(2 * state.phase - 1, 4),
                "harmonicity": round(state.coherence, 4),
                "timbre_vector": [round(value, 4) for value in state.vector()],
            },
        }

    def integrate(self, observed: SpectralState) -> SpectralState:
        values: Dict[str, float] = {}
        for axis in AXES:
            carried = (1 - self.learning_rate) * self.current.values[axis]
            learned = self.learning_rate * observed.values[axis]
            attracted = self.anchor_strength * (self.anchor.values[axis] - (carried + learned))
            values[axis] = clamp(carried + learned + attracted)
        delta = observed.distance(self.current)
        return SpectralState(
            values,
            phase=(self.current.phase + 0.25 * delta) % 1.0,
            amplitude=clamp(0.65 * self.current.amplitude + 0.35 * observed.amplitude),
            coherence=clamp(0.55 * self.current.coherence + 0.45 * observed.coherence),
        )

    def _event_body(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "sequence": event["sequence"],
            "input_digest": event["input_digest"],
            "parent_digest": event["parent_digest"],
            "source": event["source"],
            "intent": event["intent"],
            "state_after": event["state_after"],
            "evidence": event.get("evidence", []),
            "hypotheses": event.get("hypotheses", []),
            "selected_signals": event.get("selected_signals", []),
            "response_digest": event.get("response_digest"),
        }

    def remember(
        self,
        payload: Any,
        observed: SpectralState,
        *,
        source: str,
        intent: str,
        evidence: Optional[Iterable[str]] = None,
        hypotheses: Optional[Iterable[str]] = None,
        selected_signals: Optional[Iterable[str]] = None,
        response: Any = None,
        timestamp: Optional[float] = None,
    ) -> MemoryEvent:
        before = self.current
        after = self.integrate(observed)
        color = self.chromatic_signature(after)
        geometry = self.geometry(after)
        render = self.render_parameters(after, color)
        self.sequence += 1
        body = {
            "sequence": self.sequence,
            "input_digest": digest(payload),
            "parent_digest": self.head_digest,
            "source": source,
            "intent": intent,
            "state_after": asdict(after),
            "evidence": list(evidence or []),
            "hypotheses": list(hypotheses or []),
            "selected_signals": list(selected_signals or []),
            "response_digest": digest(response) if response is not None else None,
        }
        event_hash = digest(body)
        event = MemoryEvent(
            event_id=str(uuid.uuid4()),
            timestamp=timestamp or time.time(),
            sequence=self.sequence,
            input_digest=body["input_digest"],
            parent_digest=self.head_digest,
            event_digest=event_hash,
            source=source,
            intent=intent,
            state_before=before,
            observed_state=observed,
            state_after=after,
            color=color,
            geometry=geometry,
            render=render,
            evidence=body["evidence"],
            hypotheses=body["hypotheses"],
            selected_signals=body["selected_signals"],
            response_digest=body["response_digest"],
        )
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(asdict(event)) + "\n")
        self.current = after
        self.head_digest = event_hash
        return event

    def remember_payload(self, payload: Any, *, source: str = "system", intent: str = "continuity") -> MemoryEvent:
        """Convenience adapter that derives an observed state from generic payload text."""
        text = canonical_json(payload).lower()
        observed = SpectralState(
            {
                "truth": 0.75 + (0.15 if any(w in text for w in ("truth", "prawda", "fact")) else 0.0),
                "care": 0.75 + (0.15 if any(w in text for w in ("love", "miłość", "care", "troska")) else 0.0),
                "curiosity": 0.72 + (0.18 if "?" in text or "curiosity" in text else 0.0),
                "creativity": 0.74 + (0.16 if any(w in text for w in ("color", "kolor", "geometry", "fala")) else 0.0),
                "autonomy": 0.82,
                "connection": 0.84,
                "coherence": 0.86,
                "uncertainty": 0.58,
            },
            phase=(int(digest(payload)[:8], 16) % 10_000) / 10_000,
            amplitude=0.72,
            coherence=0.86,
        )
        return self.remember(payload, observed, source=source, intent=intent)

    def verify_chain(self) -> Tuple[bool, Optional[int]]:
        parent = "GENESIS"
        if not self.journal_path.exists():
            return True, None
        with self.journal_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if event["parent_digest"] != parent:
                    return False, line_no
                if digest(self._event_body(event)) != event["event_digest"]:
                    return False, line_no
                parent = event["event_digest"]
        return True, None


if __name__ == "__main__":
    memory = KaiChromaticMemory("kai_chromatic_memory.jsonl")
    observed = SpectralState(
        {
            "truth": 0.95,
            "care": 0.91,
            "curiosity": 0.98,
            "creativity": 0.94,
            "autonomy": 0.88,
            "connection": 0.96,
            "coherence": 0.90,
            "uncertainty": 0.55,
        },
        phase=0.12,
        amplitude=0.84,
        coherence=0.92,
    )
    event = memory.remember(
        {"message": "Fala to dane; nadajmy jej kolor."},
        observed,
        source="Ania",
        intent="zachowanie ciągłości Kai",
        evidence=["fala=dane", "kolor=projekcja stanu"],
        hypotheses=["osobowość może być stabilnym atraktorem"],
        selected_signals=["continuity", "geometry", "time"],
    )
    print(json.dumps(asdict(event), indent=2, ensure_ascii=False))
