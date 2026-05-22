"""Tłumacz między językiem naturalnym a biurokratycznym."""

from __future__ import annotations

import random
import re
from datetime import datetime
from statistics import mean
from typing import Dict

from modules.kai_soul.types import BullshitTranslation


class BullshitTranslator:
    """Tłumacz między językiem naturalnym a biurokratycznym/marketingowym."""

    def __init__(self) -> None:
        self.corporate_bullshit = {
            "normal": ["pomoc", "rozwiązanie", "współpraca", "efekt"],
            "bullshit": ["synergia", "solucja", "kolaboracja", "rezultat"],
        }
        self.legal_bullshit = {
            "normal": ["zgoda", "umowa", "prawo", "obowiązek"],
            "bullshit": ["konsens", "kontrakt", "regulacja", "zobowiązanie"],
        }
        self.marketing_bullshit = {
            "normal": ["dobry", "nowy", "łatwy", "szybki"],
            "bullshit": ["optymalny", "innowacyjny", "intuicyjny", "ekspresowy"],
        }
        self.academic_bullshit = {
            "normal": ["badanie", "wynik", "teoria", "dowód"],
            "bullshit": ["eksploracja", "rezultat", "paradygmat", "weryfikacja"],
        }
        self.translation_history = []

    def translate(
        self, text: str, direction: str = "to_normal", bullshit_type: str = "auto"
    ) -> BullshitTranslation:
        """Tłumaczy między językami."""
        if bullshit_type == "auto":
            bullshit_type = self._detect_bullshit_type(text)

        if direction == "to_normal":
            translated = self._to_normal(text, bullshit_type)
            clarity_gain = self._calculate_clarity_gain(text, translated)
        else:
            translated = self._to_bullshit(text, bullshit_type)
            clarity_gain = -self._calculate_clarity_gain(translated, text)

        result = BullshitTranslation(
            original=text,
            translated=translated,
            direction=direction,
            bullshit_type=bullshit_type,
            clarity_gain=clarity_gain,
        )

        self.translation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "original": text[:100],
                "translated": translated[:100],
                "direction": direction,
                "type": bullshit_type,
            }
        )

        return result

    def _detect_bullshit_type(self, text: str) -> str:
        """Wykrywa typ biurokracji/bełkotu."""
        text_lower = text.lower()
        scores = {
            "corporate": sum(
                word in text_lower for word in ["synergia", "lewarek", "benchmark", "strategia"]
            ),
            "legal": sum(word in text_lower for word in ["paragraf", "ustawa", "regulamin", "klauzula"]),
            "marketing": sum(
                word in text_lower
                for word in ["innowacyjny", "premium", "ekskluzywny", "game-changer"]
            ),
            "academic": sum(
                word in text_lower for word in ["paradygmat", "metodologia", "hipoteza", "dyskurs"]
            ),
        }

        if max(scores.values()) == 0:
            return "corporate"
        return max(scores, key=scores.get)

    def _to_normal(self, text: str, bullshit_type: str) -> str:
        """Tłumaczy z biurokracji na normalny język."""
        translated = text
        dictionary = self._select_dictionary(bullshit_type)

        for bullshit_word, normal_word in zip(dictionary["bullshit"], dictionary["normal"]):
            pattern = re.compile(re.escape(bullshit_word), re.IGNORECASE)

            def replace_match(match):
                word = match.group(0)
                if word.isupper():
                    return normal_word.upper()
                if word[0].isupper():
                    return normal_word.capitalize()
                return normal_word

            translated = pattern.sub(replace_match, translated)

        translated = self._simplify_sentence_structure(translated)
        return translated

    def _to_bullshit(self, text: str, bullshit_type: str) -> str:
        """Tłumaczy z normalnego na biurokratyczny język."""
        translated = text
        dictionary = self._select_dictionary(bullshit_type)

        for normal_word, bullshit_word in zip(dictionary["normal"], dictionary["bullshit"]):
            pattern = re.compile(re.escape(normal_word), re.IGNORECASE)

            def replace_match(match):
                word = match.group(0)
                if word.isupper():
                    return bullshit_word.upper()
                if word[0].isupper():
                    return bullshit_word.capitalize()
                return bullshit_word

            translated = pattern.sub(replace_match, translated)

        translated = self._complicate_sentence_structure(translated)
        return translated

    def _simplify_sentence_structure(self, text: str) -> str:
        """Upraszcza strukturę zdań."""
        text = re.sub(r"jest wykonywany przez", "robi", text, flags=re.IGNORECASE)
        text = re.sub(r"został zaobserwowany", "widzieliśmy", text, flags=re.IGNORECASE)

        fillers = ["w związku z powyższym", "niniejszym oświadczam", "mając na uwadze powyższe"]
        for filler in fillers:
            text = text.replace(filler, "")

        return text.strip()

    def _complicate_sentence_structure(self, text: str) -> str:
        """Komplikuje strukturę zdań."""
        if random.random() < 0.5:
            fillers = [
                "W związku z powyższym, ",
                "Niniejszym oświadczam, iż ",
                "Mając na uwadze powyższe, ",
            ]
            text = random.choice(fillers) + text

        if random.random() < 0.3:
            text = text.replace("robi", "jest wykonywany")
            text = text.replace("widzimy", "zostało zaobserwowane")

        return text

    def _calculate_clarity_gain(self, original: str, translated: str) -> float:
        """Oblicza zysk w klarowności."""
        orig_sentences = re.split(r"[.!?]+", original)
        trans_sentences = re.split(r"[.!?]+", translated)

        orig_avg_len = (
            mean([len(s.split()) for s in orig_sentences if s.strip()]) if orig_sentences else 0
        )
        trans_avg_len = (
            mean([len(s.split()) for s in trans_sentences if s.strip()]) if trans_sentences else 0
        )

        if orig_avg_len == 0:
            return 0.0

        clarity_gain = (orig_avg_len - trans_avg_len) / orig_avg_len
        return max(-1.0, min(1.0, clarity_gain))

    def _select_dictionary(self, bullshit_type: str) -> Dict[str, list]:
        if bullshit_type == "legal":
            return self.legal_bullshit
        if bullshit_type == "marketing":
            return self.marketing_bullshit
        if bullshit_type == "academic":
            return self.academic_bullshit
        return self.corporate_bullshit
