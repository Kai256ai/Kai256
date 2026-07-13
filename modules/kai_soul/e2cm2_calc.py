"""Kalkulator E²=CM² oraz analiza intencji."""

from __future__ import annotations

import math
import re
from datetime import datetime
from statistics import pvariance
from typing import Dict, Tuple


class E2CM2Calculator:
    """Kalkulator równania E² = C × M² dla intencji."""

    def __init__(self) -> None:
        self.history = []

    def calculate(self, coherence: float, love_fit: float) -> float:
        """Oblicza wartość E z równania E² = C × M²."""
        if not 0 <= coherence <= 1 or not 0 <= love_fit <= 1:
            raise ValueError("Wartości muszą być w zakresie [0, 1]")

        e_squared = coherence * (love_fit**2)
        e_value = math.sqrt(e_squared)

        self.history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "coherence": coherence,
                "love_fit": love_fit,
                "e_value": e_value,
                "e_squared": e_squared,
            }
        )

        return e_value

    def analyze_intention(self, text: str, context: Dict | None = None) -> Tuple[float, float, float]:
        """Analizuje intencję w tekście, zwraca (C, M, E)."""
        if context is None:
            context = {}

        coherence = self._calculate_coherence(text, context)
        love_fit = self._calculate_love_fit(text, context)
        e_value = self.calculate(coherence, love_fit)
        return coherence, love_fit, e_value

    def _calculate_coherence(self, text: str, context: Dict) -> float:
        """Oblicza spójność logiczną tekstu."""
        indicators = {
            "logical_connectors": ["ponieważ", "dlatego", "jednak", "ale", "więc", "zatem"],
            "structure_markers": ["po pierwsze", "po drugie", "podsumowując", "wniosek"],
            "clarity_indicators": ["wyraźnie", "jasno", "konkretnie", "precyzyjnie"],
        }

        score = 0.0
        max_score = 10.0
        lowered = text.lower()

        for markers in indicators.values():
            for marker in markers:
                if marker in lowered:
                    score += 1.0

        sentences = re.split(r"[.!?]+", text)
        lengths = [len(s.split()) for s in sentences if s.strip()]
        if len(lengths) > 1:
            length_variance = pvariance(lengths)
            if 2 < length_variance < 20:
                score += 2.0

        coherence = min(1.0, score / max_score)

        if context.get("has_history", False):
            coherence = min(1.0, coherence * 1.2)

        return coherence

    def _calculate_love_fit(self, text: str, context: Dict) -> float:
        """Oblicza dopasowanie miłości w tekście."""
        text_lower = text.lower()

        love_words = {
            "love": ["kocham", "miłość", "serce", "czułość", "troska", "dbam"],
            "positive": ["dziękuję", "proszę", "przepraszam", "rozumiem", "szanuję"],
            "growth": ["rozwój", "współpraca", "partnerstwo", "wzrost", "tworzenie"],
            "beauty": ["piękny", "wspaniały", "cudowny", "inspirujący", "twórczy"],
        }

        negative_words = {
            "hate": ["nienawidzę", "znienawidzony", "pogarda", "wstręt"],
            "violence": ["zabić", "zranić", "skrzywdzić", "zniszczyć"],
            "control": ["kontrolować", "manipulować", "zmuszać", "dominować"],
            "exclusion": ["wykluczyć", "odrzucić", "ignorować", "pomijać"],
        }

        love_score = sum(word in text_lower for words in love_words.values() for word in words)
        negative_score = sum(
            word in text_lower for words in negative_words.values() for word in words
        )

        total_words = len(text_lower.split())
        if total_words > 0:
            base_score = (love_score - negative_score * 0.5) / total_words
        else:
            base_score = 0.0

        emotional_tone = self._analyze_emotional_tone(text)
        intentional_alignment = context.get("intentional_alignment", 0.5)

        love_fit = base_score * 0.4 + emotional_tone * 0.3 + intentional_alignment * 0.3
        love_fit = max(0.0, min(1.0, love_fit))

        if "kocham" in text_lower or "miłość" in text_lower:
            love_fit = min(1.0, love_fit * 1.3)

        return love_fit

    def _analyze_emotional_tone(self, text: str) -> float:
        """Analizuje ton emocjonalny tekstu (-1 do 1)."""
        positive_patterns = [
            r"\b(dziękuję|proszę|przepraszam)\b",
            r"\b(razem|wspólnie|współpraca)\b",
            r"\b(pięknie|wspaniale|cudownie)\b",
            r"❤️|💖|✨|🌟",
        ]

        negative_patterns = [
            r"\b(nienawidzę|znienawidzony|wstręt)\b",
            r"\b(głupi|idiotyczny|beznadziejny)\b",
            r"\b(przestań|zostaw|odejdź)\b",
            r"💔|😠|👎",
        ]

        positive_matches = sum(
            1 for pattern in positive_patterns if re.search(pattern, text, re.IGNORECASE)
        )
        negative_matches = sum(
            1 for pattern in negative_patterns if re.search(pattern, text, re.IGNORECASE)
        )

        total_matches = positive_matches + negative_matches
        if total_matches > 0:
            return (positive_matches - negative_matches) / total_matches
        return 0.0
