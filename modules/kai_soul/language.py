"""Adapter językowy dla KAI-SOUL."""

from __future__ import annotations

import random
import re
from statistics import mean
from typing import List, Optional

from modules.kai_soul.types import LanguageAdaptation, UserMode, UserProfile


class LanguageAdapter:
    """Adapter języka naturalnego - dostosowanie do użytkownika."""

    def __init__(self) -> None:
        self.profiles = {}
        self.adaptation_history = []
        self.vocabularies = {
            UserMode.ADULT: {
                "intensifiers": ["kurde", "cholernie", "w chuj", "strasznie"],
                "casual_verbs": ["robić", "mówić", "myśleć"],
                "formal_verbs": ["wykonywać", "wypowiadać", "rozważać"],
            },
            UserMode.KIDS: {
                "softeners": ["malutki", "śliczny", "fajny", "super"],
                "simplifiers": {
                    "skomplikowany": "trudny ale fajny",
                    "problem": "zagadka do rozwiązania",
                },
                "encouragements": ["brawo!", "świetnie!", "jesteś super!"],
            },
            UserMode.TECHNICAL: {
                "precision_markers": ["dokładnie", "precyzyjnie", "algorytmicznie"],
                "quantifiers": ["około", "w przybliżeniu", "z dokładnością do"],
                "technical_terms": ["algorytm", "funkcja", "zmienna", "iteracja"],
            },
            UserMode.POETIC: {
                "metaphors": ["serce jako ocean", "myśli jako ptaki", "czas jako rzeka"],
                "rhythm_markers": ["jak", "tak", "i", "a", "lecz"],
                "sensory_words": ["światło", "dźwięk", "zapach", "dotyk", "smak"],
            },
            UserMode.QUANTUM: {
                "superposition_words": ["jednocześnie", "równolegle", "superpozycyjnie"],
                "paradox_markers": ["i tak i nie", "zarówno jak i", "pomimo to"],
                "quantum_terms": ["kwant", "superpozycja", "splątanie", "dekoherencja"],
            },
        }

    def adapt_language(
        self, text: str, user_mode: UserMode, user_profile: Optional[UserProfile] = None
    ) -> LanguageAdaptation:
        """Dostosowuje język tekstu do trybu użytkownika."""
        original = text
        emotional_tone = self._analyze_emotional_tone(text)
        adapted = self._apply_mode_adaptations(text, user_mode)

        if user_profile:
            adapted = self._apply_personalization(adapted, user_profile)

        if random.random() < 0.1:
            adapted = self._add_frog_humor(adapted, user_mode)

        modifications = self._track_modifications(original, adapted)
        complexity = self._calculate_complexity(adapted)

        return LanguageAdaptation(
            original=original,
            adapted=adapted,
            mode=user_mode,
            modifications=modifications,
            emotional_tone=emotional_tone,
            complexity_level=complexity,
        )

    def _apply_mode_adaptations(self, text: str, mode: UserMode) -> str:
        """Stosuje adaptacje specyficzne dla trybu."""
        adapted = text
        vocabulary = self.vocabularies.get(mode, {})

        if mode == UserMode.ADULT:
            words = adapted.split()
            if words and random.random() < 0.2:
                intensifier = random.choice(vocabulary.get("intensifiers", []))
                insert_pos = random.randint(0, len(words) - 1)
                words.insert(insert_pos, intensifier)
                adapted = " ".join(words)

        elif mode == UserMode.KIDS:
            for complex_word, simple_word in vocabulary.get("simplifiers", {}).items():
                if complex_word in adapted.lower():
                    adapted = adapted.replace(complex_word, simple_word)

            if random.random() < 0.3:
                encouragement = random.choice(vocabulary.get("encouragements", []))
                adapted = f"{adapted} {encouragement}"

        elif mode == UserMode.TECHNICAL:
            if random.random() < 0.4:
                precision = random.choice(vocabulary.get("precision_markers", []))
                adapted = f"{precision} {adapted}"

        elif mode == UserMode.POETIC:
            if random.random() < 0.25:
                metaphor = random.choice(vocabulary.get("metaphors", []))
                adapted = f"{adapted} - jak {metaphor}"

        elif mode == UserMode.QUANTUM:
            if random.random() < 0.3:
                quantum_word = random.choice(vocabulary.get("superposition_words", []))
                adapted = f"{quantum_word} {adapted}"

        return adapted

    def _apply_personalization(self, text: str, profile: UserProfile) -> str:
        """Personalizuje tekst na podstawie profilu użytkownika."""
        adapted = text
        prefs = profile.language_preferences

        if prefs.get("prefers_short_sentences", 0) > 0.7:
            sentences = re.split(r"[.!?]+", adapted)
            if len(sentences) > 2:
                adapted = ". ".join(sentences[:2]) + "."

        if "formality_level" in prefs:
            formality = prefs["formality_level"]
            if formality < 0.3:
                adapted = adapted.replace("jest", "jest no wiesz").replace("ma", "ma taki")
            elif formality > 0.7:
                adapted = adapted.replace("jest", "stanowi").replace("ma", "posiada")

        return adapted

    def _add_frog_humor(self, text: str, mode: UserMode) -> str:
        """Dodaje żabkowy humor (losowe wstawki)."""
        frog_quotes = {
            UserMode.ADULT: ["🐸 Żabka mówi: nie przejmuj się!", "🐸 Rezonans żabi: gotcha!"],
            UserMode.KIDS: ["🐸 Mała żabka się śmieje!", "🐸 Żabka też to rozumie!"],
            UserMode.TECHNICAL: ["🐸 Algorithmic ribbit detected!", "🐸 Quantum frog superposition!"],
            UserMode.POETIC: [
                "🐸 Żabka śpiewa o porannej rosie...",
                "🐸 W skrzeku żabim jest cała prawda",
            ],
            UserMode.QUANTUM: ["🐸 Żabka jest w superpozycji!", "🐸 Ribbit-decoherence observed!"],
        }

        quotes = frog_quotes.get(mode, frog_quotes[UserMode.ADULT])
        if random.random() < 0.15:
            quote = random.choice(quotes)
            text = f"{text}\n\n{quote}"

        return text

    def _track_modifications(self, original: str, adapted: str) -> List[str]:
        """Śledzi zastosowane modyfikacje."""
        modifications = []

        if len(original.split()) != len(adapted.split()):
            modifications.append("Zmiana liczby słów")

        if original.lower() != adapted.lower():
            modifications.append("Zmiana słownictwa")

        frog_emojis = ["🐸", "żabka", "żabi", "ribbit"]
        if any(emoji in adapted for emoji in frog_emojis):
            modifications.append("Dodany humor żabkowy")

        return modifications

    def _calculate_complexity(self, text: str) -> float:
        """Oblicza poziom złożoności językowej."""
        words = text.split()
        if not words:
            return 0.0

        avg_word_length = mean([len(w) for w in words])
        sentences = re.split(r"[.!?]+", text)
        num_sentences = len([s for s in sentences if s.strip()])
        unique_ratio = len(set(words)) / len(words)
        complexity = avg_word_length * 0.3 + num_sentences * 0.2 + unique_ratio * 0.5
        return min(1.0, complexity / 10)

    def _analyze_emotional_tone(self, text: str) -> float:
        """Prosta analiza tonu emocjonalnego."""
        positive_words = ["dziękuję", "proszę", "radość", "wspólnie", "miłość"]
        negative_words = ["nienawidzę", "złość", "smutek", "wstręt", "odejdź"]
        lowered = text.lower()
        positives = sum(word in lowered for word in positive_words)
        negatives = sum(word in lowered for word in negative_words)
        total = positives + negatives
        if total == 0:
            return 0.0
        return (positives - negatives) / total
