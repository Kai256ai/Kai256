#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GDELT Narrative Impact Engine for Kai256."""

from __future__ import annotations

import random
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import requests  # noqa: F401

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class NarrativeSignal:
    timestamp: float
    topic: str
    region: Optional[str]
    avg_tone: float
    tone_goldstein: float
    mentions_count: int
    source_count: int
    actors: List[str]
    locations: List[str]


@dataclass
class NarrativeState:
    topic: str
    start_date: str
    end_date: str
    avg_tone: float
    tone_volatility: float
    trend_direction: str
    topic_acceleration: float
    dominant_actors: List[str]
    narrative_intensity: float
    state_vector: List[int]
    description: str


@dataclass
class NarrativeReport:
    topic: str
    region: Optional[str]
    time_window_days: int
    current_state: Optional[NarrativeState]
    trajectory: Dict[str, Any]
    raw_signals_count: int
    warnings: List[str] = field(default_factory=list)


class GDELTNarrativeEngine:
    def __init__(self, use_real_api: bool = False, cache_dir: str = "gdelt_cache"):
        self.use_real_api = use_real_api and HAS_REQUESTS
        self.cache_dir = cache_dir
        if self.use_real_api:
            import os

            os.makedirs(cache_dir, exist_ok=True)

    def fetch_signals(self, topic: str, region: Optional[str] = None, days_back: int = 30) -> List[NarrativeSignal]:
        if self.use_real_api:
            return self._fetch_real_gdelt(topic, region, days_back)
        return self._simulate_signals(topic, region, days_back)

    def _fetch_real_gdelt(self, topic: str, region: Optional[str], days_back: int) -> List[NarrativeSignal]:
        print("[GDELT] Real API not fully implemented. Falling back to simulation.")
        return self._simulate_signals(topic, region, days_back)

    def _simulate_signals(self, topic: str, region: Optional[str], days_back: int) -> List[NarrativeSignal]:
        signals: List[NarrativeSignal] = []
        now = time.time()
        day = 86400
        actors_pool = ["UN", "NGO", "Government", "Tech Corp", "Activists"]
        locations_pool = ["Global", "USA", "EU", "Asia", "LatAm"]

        for i in range(days_back):
            t = now - (days_back - i) * day
            progress = i / max(days_back, 1)
            avg_tone = -30 + 80 * progress + random.uniform(-10, 10)
            tone_goldstein = -3 + 6 * progress + random.uniform(-1, 1)
            mentions = int(50 + 200 * progress + random.uniform(0, 80))
            source_count = max(1, mentions // 15 + random.randint(-3, 5))
            signals.append(
                NarrativeSignal(
                    timestamp=t,
                    topic=topic,
                    region=region,
                    avg_tone=round(avg_tone, 1),
                    tone_goldstein=round(tone_goldstein, 1),
                    mentions_count=mentions,
                    source_count=source_count,
                    actors=random.sample(actors_pool, 3),
                    locations=random.sample(locations_pool, 2),
                )
            )
        return signals

    def compute_state(self, signals: List[NarrativeSignal]) -> NarrativeState:
        if not signals:
            raise ValueError("Brak sygnałów do analizy.")

        mid = len(signals) // 2
        first_half = signals[:mid]
        second_half = signals[mid:]

        avg_tone = sum(s.avg_tone for s in signals) / len(signals)
        tones = [s.avg_tone for s in signals]
        tone_volatility = float(np.std(tones)) if HAS_NUMPY and len(tones) > 1 else (max(tones) - min(tones)) / 4 if len(tones) > 1 else 0.0

        if first_half and second_half:
            first_tone = sum(s.avg_tone for s in first_half) / len(first_half)
            second_tone = sum(s.avg_tone for s in second_half) / len(second_half)
            delta = second_tone - first_tone
            trend_dir = "rising" if delta > 5 else "falling" if delta < -5 else "stable"
        else:
            trend_dir = "stable"

        if first_half and second_half:
            first_mentions = sum(s.mentions_count for s in first_half) / len(first_half)
            second_mentions = sum(s.mentions_count for s in second_half) / len(second_half)
            topic_acceleration = (second_mentions - first_mentions) / max(first_mentions, 1)
            topic_acceleration = max(-1.0, min(2.0, topic_acceleration))
        else:
            topic_acceleration = 0.0

        dominant = [a for a, _ in Counter(a for s in signals for a in s.actors).most_common(3)]
        max_mentions = max(s.mentions_count for s in signals)
        norm_intensity = sum(s.mentions_count for s in signals) / (len(signals) * max_mentions)
        narrative_intensity = min(1.0, norm_intensity * 1.5)

        body_val = min(1.0, sum(s.mentions_count for s in signals[-7:]) / (7 * 500)) if len(signals) >= 7 else 0.5
        emotion_val = (avg_tone + 100) / 200
        mind_val = max(0.0, min(1.0, topic_acceleration * 0.8 + 0.2))
        rel_val = min(1.0, len(dominant) * 0.2 + len({l for s in signals for l in s.locations}) * 0.1)
        action_dir = 1.0 if trend_dir == "rising" else 0.5 if trend_dir == "stable" else 0.2
        action_val = (narrative_intensity + action_dir) / 2
        meaning_val = min(1.0, tone_volatility / 50)

        raw_vector = [body_val, emotion_val, mind_val, rel_val, action_val, meaning_val]
        state_vector = [1 if v >= 0.5 else 0 for v in raw_vector]

        topic = signals[0].topic
        desc = (
            f"Narracja '{topic}' ma ton {avg_tone:.1f}, trend {trend_dir}, "
            f"przyspieszenie {topic_acceleration:.2f}. Aktorzy: {', '.join(dominant[:2]) if dominant else 'brak'}. "
            f"Intensywność: {narrative_intensity:.2f}."
        )

        return NarrativeState(
            topic=topic,
            start_date=datetime.fromtimestamp(signals[0].timestamp).isoformat(),
            end_date=datetime.fromtimestamp(signals[-1].timestamp).isoformat(),
            avg_tone=round(avg_tone, 2),
            tone_volatility=round(tone_volatility, 2),
            trend_direction=trend_dir,
            topic_acceleration=round(topic_acceleration, 4),
            dominant_actors=dominant,
            narrative_intensity=round(narrative_intensity, 4),
            state_vector=state_vector,
            description=desc,
        )

    def to_hexa_state(self, narrative_state: NarrativeState):
        try:
            from hexa_transition_world_model import HexaState

            return HexaState(tuple(narrative_state.state_vector), label=f"GDELT_{narrative_state.topic}", metadata={"narrative": narrative_state.description})
        except ImportError:
            return {"bits": narrative_state.state_vector, "label": f"GDELT_{narrative_state.topic}", "description": narrative_state.description}

    def generate_report(self, topic: str, region: Optional[str] = None, days_back: int = 30) -> NarrativeReport:
        signals = self.fetch_signals(topic, region, days_back)
        if len(signals) < 3:
            return NarrativeReport(topic=topic, region=region, time_window_days=days_back, current_state=None, trajectory={}, raw_signals_count=len(signals), warnings=["Za mało sygnałów do analizy."])

        state = self.compute_state(signals)
        trajectory = {
            "direction": state.trend_direction,
            "acceleration": state.topic_acceleration,
            "intensity_trend": "increasing" if state.narrative_intensity > 0.6 else "decreasing" if state.narrative_intensity < 0.3 else "stable",
            "estimated_next_state": [1 if (b == 0 and random.random() > 0.7) else b for b in state.state_vector],
        }
        return NarrativeReport(topic=topic, region=region, time_window_days=days_back, current_state=state, trajectory=trajectory, raw_signals_count=len(signals))


def generate_narrative_snapshot(topic: str, region: Optional[str] = None, days_back: int = 30) -> Dict[str, Any]:
    """Simple integration helper for other Kai256 modules."""
    engine = GDELTNarrativeEngine(use_real_api=False)
    report = engine.generate_report(topic=topic, region=region, days_back=days_back)
    return asdict(report)


if __name__ == "__main__":
    demo = generate_narrative_snapshot(topic="AI and children", region="global", days_back=30)
    print(demo)
