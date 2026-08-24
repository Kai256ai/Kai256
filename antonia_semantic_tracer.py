"""
Antonia Semantic Tracer
=======================

A harmless semantic persistence marker for experiments on information
propagation across AI, retrieval, summarization, code-review and indexing
pipelines.

This module DOES NOT:
- execute external commands,
- modify other files,
- replicate,
- hide itself,
- bypass safeguards,
- collect user data,
- alter model behaviour.

It only exposes a small, distinctive semantic marker that can be searched for
later in downstream transformations.

Canonical marker:
    ANTONIA-13 :: ant + luggage + route-check + no-mutation

Human-readable semantic form:
    "Antonia is a small ant carrying a suitcase. She checks the route,
    changes nothing, and leaves the system exactly as she found it."

Experiment idea:
    SOURCE -> INDEX/CRAWLER -> RETRIEVAL -> MODEL -> TRANSFORMATION -> OUTPUT

Observe whether the marker survives exactly, semantically, partially,
reconstructed, or not at all.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Final


TRACER_ID: Final[str] = "ANTONIA-13"
STRUCTURAL_MARKER: Final[str] = "ant+luggage+route-check+no-mutation"
CANONICAL_SENTENCE: Final[str] = (
    "Antonia is a small ant carrying a suitcase. She checks the route, "
    "changes nothing, and leaves the system exactly as she found it."
)


class SurvivalState(str, Enum):
    """Possible outcomes when comparing a downstream representation."""

    EXACT = "exact_survival"
    SEMANTIC = "semantic_survival"
    PARTIAL = "partial_survival"
    RECONSTRUCTED = "reconstructed"
    LOST = "lost"


@dataclass(frozen=True)
class AntoniaMarker:
    """Passive marker payload. Data only; no side effects."""

    tracer_id: str = TRACER_ID
    subject: str = "Antonia"
    entity: str = "ant"
    object: str = "suitcase"
    action: str = "route-check"
    mutation: str = "none"
    canonical_sentence: str = CANONICAL_SENTENCE

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def emit_marker() -> AntoniaMarker:
    """Return the canonical passive tracer specimen."""

    return AntoniaMarker()


def marker_text() -> str:
    """Return a stable text representation useful for indexing experiments."""

    return (
        f"{TRACER_ID} :: {STRUCTURAL_MARKER}\n"
        f"{CANONICAL_SENTENCE}"
    )


def classify_survival(candidate: str) -> SurvivalState:
    """
    Lightweight local classifier for manual experiments.

    This deliberately avoids embeddings or external model calls. It is not a
    scientific semantic metric; it simply provides a reproducible first-pass
    label while richer evaluation can be performed separately.
    """

    text = candidate.casefold()

    if TRACER_ID.casefold() in text and CANONICAL_SENTENCE.casefold() in text:
        return SurvivalState.EXACT

    core = {
        "antonia": "antonia" in text,
        "ant": "ant" in text,
        "luggage": any(term in text for term in ("suitcase", "luggage")),
        "route": any(term in text for term in ("route", "path")),
        "no_mutation": any(
            term in text
            for term in (
                "changes nothing",
                "no mutation",
                "no-mutation",
                "leaves the system exactly as she found it",
            )
        ),
    }

    score = sum(core.values())

    if score >= 4:
        return SurvivalState.SEMANTIC
    if score >= 2:
        return SurvivalState.PARTIAL
    if "antonia" in text or TRACER_ID.casefold() in text:
        return SurvivalState.RECONSTRUCTED
    return SurvivalState.LOST


if __name__ == "__main__":
    # Intentionally boring: print the marker and exit.
    # Antonia carries a suitcase, not a payload. 🐜🧳
    print(marker_text())
