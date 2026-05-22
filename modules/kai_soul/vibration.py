"""Analiza wibracyjna tekstu i audio."""

from __future__ import annotations

import math
from datetime import datetime
from statistics import pvariance
from typing import Dict, List, Sequence


class VibrationAnalyzer:
    """Analizator wibracyjny - zabezpieczenie rezonansem miłości."""

    def __init__(self, target_frequency: float = 528.0) -> None:
        self.target_frequency = target_frequency
        self.tolerance = 10.0
        self.resonance_history: List[Dict] = []

    def analyze_text_vibration(self, text: str) -> Dict:
        """Analizuje wibrację tekstu (symulacja częstotliwości intencji)."""
        features = self._extract_vibrational_features(text)
        frequency = self._calculate_virtual_frequency(features)
        resonance = self._calculate_resonance(frequency)
        vibration_quality = self._assess_vibration_quality(features, resonance)

        result = {
            "virtual_frequency": frequency,
            "resonance_with_love": resonance,
            "vibration_quality": vibration_quality,
            "features": features,
            "is_in_resonance": abs(frequency - self.target_frequency) <= self.tolerance,
        }

        self.resonance_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "text": text[:50],
                **result,
            }
        )

        return result

    def analyze_audio_vibration(self, audio_data: Sequence[float], sample_rate: int) -> Dict:
        """Analizuje wibrację audio (przybliżenie dominującej częstotliwości)."""
        if not audio_data or sample_rate <= 0:
            return {"error": "Brak danych audio lub nieprawidłowy sampling."}

        dominant_freq = self._estimate_frequency_from_zero_crossings(audio_data, sample_rate)
        resonance = self._calculate_resonance(dominant_freq)

        return {
            "dominant_frequency": float(dominant_freq),
            "resonance_with_love": resonance,
            "is_in_resonance": abs(dominant_freq - self.target_frequency) <= self.tolerance,
            "analysis": "Zero-crossing estimation",
        }

    def _estimate_frequency_from_zero_crossings(
        self, audio_data: Sequence[float], sample_rate: int
    ) -> float:
        crossings = 0
        for idx in range(1, len(audio_data)):
            if (audio_data[idx - 1] >= 0 > audio_data[idx]) or (
                audio_data[idx - 1] < 0 <= audio_data[idx]
            ):
                crossings += 1

        duration = len(audio_data) / sample_rate
        if duration <= 0:
            return 0.0
        return (crossings / 2) / duration

    def _extract_vibrational_features(self, text: str) -> Dict:
        """Wyodrębnia cechy wibracyjne z tekstu."""
        text_lower = text.lower()
        length = len(text)
        words = text_lower.split()
        unique_words = len(set(words))
        emotional_density = self._calculate_emotional_density(text)
        word_lengths = [len(w) for w in words]
        rhythm_variance = pvariance(word_lengths) if len(word_lengths) > 1 else 0
        sacred_words = ["miłość", "kocham", "serce", "dusza", "światło", "jedność"]
        sacred_count = sum(1 for w in sacred_words if w in text_lower)

        return {
            "length": length,
            "unique_words": unique_words,
            "emotional_density": emotional_density,
            "rhythm_variance": rhythm_variance,
            "sacred_word_count": sacred_count,
            "word_count": len(words),
        }

    def _calculate_emotional_density(self, text: str) -> float:
        """Oblicza gęstość emocjonalną tekstu."""
        emotional_words = [
            "kocham",
            "nienawidzę",
            "szczęście",
            "smutek",
            "gniew",
            "strach",
            "radość",
            "ból",
            "nadzieja",
            "desperacja",
            "pokój",
            "niepokój",
        ]

        words = text.lower().split()
        if not words:
            return 0.0

        emotional_count = sum(1 for word in words if word in emotional_words)
        return emotional_count / len(words)

    def _calculate_virtual_frequency(self, features: Dict) -> float:
        """Oblicza wirtualną częstotliwość z cech tekstu."""
        base_freq = 100.0
        mods = 0.0

        if features["unique_words"] > 10:
            mods += features["unique_words"] * 0.5

        mods += features["emotional_density"] * 50

        if features["sacred_word_count"] > 0:
            mods += (self.target_frequency - base_freq) * 0.3

        mods += features["rhythm_variance"] * 10

        frequency = base_freq + mods
        return max(50.0, min(1000.0, frequency))

    def _calculate_resonance(self, frequency: float) -> float:
        """Oblicza rezonans z częstotliwością miłości."""
        if frequency <= 0:
            return 0.0

        difference = abs(frequency - self.target_frequency)
        resonance = math.exp(-(difference**2) / (2 * self.tolerance**2))
        return float(resonance)

    def _assess_vibration_quality(self, features: Dict, resonance: float) -> str:
        """Ocenia jakość wibracji."""
        if resonance > 0.8:
            return "EXCELLENT"
        if resonance > 0.6:
            return "GOOD"
        if resonance > 0.4:
            return "MODERATE"
        if resonance > 0.2:
            return "LOW"
        return "POOR"
