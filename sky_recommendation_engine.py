"""SKY recommendation perturbation engine integrated with Kai256.

The engine ranks small, auditable recommendation candidates while keeping
topic labels separate from the full texts used for semantic comparisons.
It intentionally uses dependency-free heuristics so it can run with Kai256's
standard-library-only core.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass
class GoalVector:
    curiosity: float = 0.7
    knowledge: float = 0.6
    wellbeing: float = 0.5
    creativity: float = 0.7
    diversity: float = 0.6

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class Candidate:
    id: str
    text: str
    creator_id: Optional[str] = None
    topic: str = "general"
    popularity: float = 0.5
    engagement_probability: float = 0.5
    relevance: float = 0.0
    information_gain: float = 0.0
    novelty: float = 0.0
    trust: float = 0.5
    risk: float = 0.1
    uncertainty: float = 0.3
    user_fit: float = 0.0
    creator_value: float = 0.0
    platform_value: float = 0.0
    long_term_value: float = 0.0
    directional_alignment: float = 0.0
    redundancy: float = 0.0
    exploration_boost: float = 0.0
    final_score: float = 0.0
    trajectory_effect: float = 0.0


@dataclass
class UserState:
    interests: Dict[str, float] = field(default_factory=dict)
    recent_topics: List[str] = field(default_factory=list)
    recent_texts: List[str] = field(default_factory=list)
    topic_history: List[str] = field(default_factory=list)
    creator_history: Dict[str, float] = field(default_factory=dict)
    trajectory: List[str] = field(default_factory=list)


@dataclass
class EnvironmentState:
    topic_distribution: Dict[str, float] = field(default_factory=dict)
    creator_distribution: Dict[str, float] = field(default_factory=dict)
    redundancy: float = 0.0
    novelty: float = 0.5
    diversity: float = 0.5


def text_signature(text: str) -> str:
    """Return a stable word-set fingerprint for duplicate detection."""
    words = set(text.casefold().split())
    return hashlib.md5(" ".join(sorted(words)).encode(), usedforsecurity=False).hexdigest()[:10]


def semantic_distance(text1: str, text2: str) -> float:
    """Return Jaccard word distance (zero identical, one disjoint)."""
    words1, words2 = set(text1.casefold().split()), set(text2.casefold().split())
    if not words1 or not words2:
        return 0.5
    return 1.0 - len(words1 & words2) / len(words1 | words2)


CLICKBAIT_MARKERS = (
    "clickbait", "you won't believe", "shocking", "this one trick",
    "gone wrong", "must see", "doctors hate",
)


class SKYRecommendationEngine:
    """Score, select, learn from, and audit recommendation perturbations."""

    DEFAULT_WEIGHTS = {
        "fit": 1.0, "direction": 1.2, "information_gain": 1.1,
        "novelty": 0.8, "trust": 0.9, "exploration": 0.7,
        "long_term": 1.0, "creator": 0.6, "platform": 0.5,
        "risk": -1.3, "uncertainty": -0.5, "redundancy": -1.0,
        "trajectory": 1.0,
    }

    def __init__(self, goal_vector: Optional[GoalVector] = None,
                 perturbation_budget: float = 0.01, max_recommendations: int = 3,
                 weights: Optional[Dict[str, float]] = None,
                 exploration_noise: float = 0.03,
                 rng: Optional[random.Random] = None):
        if not 0.0 <= perturbation_budget <= 1.0:
            raise ValueError("perturbation_budget must be between 0 and 1")
        if max_recommendations < 1:
            raise ValueError("max_recommendations must be positive")
        if exploration_noise < 0.0:
            raise ValueError("exploration_noise cannot be negative")
        self.goal_vector = goal_vector or GoalVector()
        self.perturbation_budget = perturbation_budget
        self.max_recommendations = max_recommendations
        # Budget now has an operational meaning: it caps the relative random
        # displacement of every score from its deterministic trajectory.
        self.exploration_noise = min(exploration_noise, perturbation_budget)
        self.weights = {**self.DEFAULT_WEIGHTS, **(weights or {})}
        self._rng = rng or random.Random()
        self.log: List[Dict[str, Any]] = []
        self._iteration = 0

    def evaluate_candidate(self, candidate: Candidate, state: UserState,
                           env: EnvironmentState) -> Candidate:
        del env  # reserved for future population-level scoring
        c = copy.deepcopy(candidate)
        c.relevance = state.interests.get(c.topic, 0.35)
        recent = state.recent_texts[-3:]
        average_distance = (sum(semantic_distance(c.text, text) for text in recent) /
                            len(recent)) if recent else 0.7
        base_novelty = 0.8 if c.topic not in state.recent_topics[-8:] else 0.25
        c.novelty = _clamp((base_novelty + average_distance) / 2 if recent else base_novelty)
        c.trust = _clamp(state.creator_history.get(c.creator_id or "unknown", 0.55))
        if c.trust > 0.6:
            c.trust = _clamp(c.trust + 0.05)
        c.risk = 0.15 if any(marker in c.text.casefold() for marker in CLICKBAIT_MARKERS) else 0.08
        c.uncertainty = 0.4 if c.creator_id not in state.creator_history else 0.2

        topic_score = min(1.0, state.topic_history.count(c.topic) / 8.0)
        if recent:
            signature = text_signature(c.text)
            if signature in {text_signature(text) for text in recent}:
                similarity = 1.0
            else:
                similarity = 1.0 - average_distance
        else:
            similarity = 0.2
        c.redundancy = (topic_score + similarity) / 2.0
        c.information_gain = _clamp(average_distance * c.relevance * c.trust)

        c.trajectory_effect = min(1.0,
            (0.3 if c.topic in state.interests else 0.0) +
            (0.3 if c.novelty > 0.5 else 0.0) +
            (0.4 if c.information_gain > 0.5 else 0.0))
        unknown_creator = c.creator_id not in state.creator_history
        c.exploration_boost = 0.08 if unknown_creator else 0.0
        interest = state.interests.get(c.topic, 0.3)
        recency_penalty = 0.15 if c.topic in state.recent_topics[-5:] else 0.0
        c.user_fit = _clamp(interest * 0.7 + c.relevance * 0.3 - recency_penalty)
        history = state.creator_history.get(c.creator_id or "unknown", 0.5)
        creator_base = history * 0.6 + (1.0 - c.popularity) * 0.2 + c.trust * 0.2
        creator_base += 0.05 if history > 0.6 else 0.0
        unknown_topic = c.topic not in state.interests
        exploration = (1.0 if unknown_creator else 0.2) * 0.5 + (1.0 if unknown_topic else 0.3) * 0.5
        c.creator_value = _clamp(_clamp(creator_base) + _clamp(exploration) * 0.2)
        c.long_term_value = _clamp(c.information_gain * 0.4 + c.novelty * 0.3 +
                                   (1.0 - c.redundancy) * 0.3)
        c.platform_value = _clamp(c.engagement_probability * 0.6)
        goal = self.goal_vector
        c.directional_alignment = _clamp((
            goal.curiosity * c.novelty + goal.knowledge * c.information_gain +
            goal.creativity * c.novelty + goal.diversity * (1.0 - c.redundancy) +
            goal.wellbeing * (1.0 - c.risk)) / 5.0)
        if c.redundancy > 0.6 and c.novelty < 0.3:
            c.directional_alignment *= 0.7

        values = {
            "fit": c.user_fit, "direction": c.directional_alignment,
            "information_gain": c.information_gain, "novelty": c.novelty,
            "trust": c.trust, "exploration": c.exploration_boost,
            "long_term": c.long_term_value, "creator": c.creator_value,
            "platform": c.platform_value, "risk": c.risk,
            "uncertainty": c.uncertainty, "redundancy": c.redundancy,
            "trajectory": c.trajectory_effect,
        }
        score = sum(self.weights[name] * value for name, value in values.items())
        displacement = self.exploration_noise * self._rng.uniform(-1.0, 1.0)
        c.final_score = max(0.0, score * (1.0 + displacement))
        return c

    def select_perturbation(self, candidates: List[Candidate], state: UserState,
                            env: EnvironmentState,
                            top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        limit = self.max_recommendations if top_k is None else top_k
        if limit < 0:
            raise ValueError("top_k cannot be negative")
        ranked = sorted((self.evaluate_candidate(c, state, env) for c in candidates),
                        key=lambda candidate: candidate.final_score, reverse=True)
        return [{
            "candidate_id": c.id, "text_preview": c.text[:120] + ("..." if len(c.text) > 120 else ""),
            "full_text": c.text, "creator_id": c.creator_id, "topic": c.topic,
            "final_score": round(c.final_score, 4),
            "directional_alignment": round(c.directional_alignment, 3),
            "information_gain": round(c.information_gain, 3), "novelty": round(c.novelty, 3),
            "redundancy": round(c.redundancy, 3), "trajectory_effect": round(c.trajectory_effect, 3),
            "recommended_action": "open" if c.final_score > 0.55 else "consider",
            "marker": "AI recommendation (perturbation engine)",
        } for c in ranked[:limit]]

    def update_state_after_action(self, state: UserState, action: Dict[str, Any],
                                  observed_effect: Optional[Dict[str, Any]] = None) -> UserState:
        del observed_effect  # API extension point
        updated = copy.deepcopy(state)
        updated.recent_topics = (updated.recent_topics + [action.get("topic", "general")])[-20:]
        updated.topic_history.append(action.get("topic", "general"))
        if action.get("full_text"):
            updated.recent_texts = (updated.recent_texts + [action["full_text"]])[-20:]
        creator = action.get("creator_id")
        if creator:
            updated.creator_history[creator] = min(1.0, updated.creator_history.get(creator, 0.5) + 0.02)
        updated.trajectory = (updated.trajectory + [action.get("recommended_action", "unknown")])[-50:]
        return updated

    def log_iteration(self, state_before: UserState, env_before: EnvironmentState,
                      selected: List[Dict[str, Any]], action_taken: str,
                      state_after: Optional[UserState] = None,
                      env_after: Optional[EnvironmentState] = None,
                      notes: str = "") -> None:
        self._iteration += 1
        self.log.append({
            "iteration": self._iteration, "timestamp": datetime.now(timezone.utc).isoformat(),
            "goal_vector": self.goal_vector.as_dict(), "selected": selected,
            "action_taken": action_taken, "notes": notes,
            "state_before": asdict(state_before), "env_before": asdict(env_before),
            "state_after": asdict(state_after) if state_after else None,
            "env_after": asdict(env_after) if env_after else None,
        })

    def export_log(self, path: str | Path = "sky_experiment_log.json") -> str:
        output = Path(path)
        output.write_text(json.dumps(self.log, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(output)

