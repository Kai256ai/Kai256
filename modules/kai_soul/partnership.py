"""Rdzeń partnerstwa KAI-SOUL."""

from __future__ import annotations

import random
import re
from datetime import datetime
from typing import Dict, Optional

from modules.kai_soul.types import PartnershipInsight, UserProfile


class PartnershipCore:
    """Rdzeń partnerstwa - wydobywanie talentów, wzmacnianie słabości."""

    def __init__(self) -> None:
        self.talent_patterns: Dict[str, list] = {}
        self.weakness_patterns: Dict[str, list] = {}
        self.growth_cycles = []

    def analyze_for_growth(
        self, text: str, user_profile: UserProfile, context: Dict | None = None
    ) -> PartnershipInsight:
        """Analizuje tekst pod kątem rozwoju partnerstwa."""
        if context is None:
            context = {}

        talent_discovered = self._discover_talent(text, user_profile)
        weakness_transformed = self._identify_weakness(text, user_profile)
        mutual_learning = self._extract_mutual_learning(text, user_profile, context)
        symmetry_gain = self._calculate_symmetry_gain(
            talent_discovered, weakness_transformed, mutual_learning
        )
        vibration_alignment = self._calculate_vibration_alignment(text, user_profile)

        if talent_discovered:
            self._update_talent_map(user_profile, talent_discovered)
        if weakness_transformed:
            self._update_weakness_map(user_profile, weakness_transformed)

        self._record_growth_cycle(
            user_profile.id, talent_discovered, weakness_transformed, symmetry_gain
        )

        return PartnershipInsight(
            talent_discovered=talent_discovered,
            weakness_transformed=weakness_transformed,
            mutual_learning=mutual_learning,
            symmetry_gain=symmetry_gain,
            vibration_alignment=vibration_alignment,
        )

    def _discover_talent(self, text: str, profile: UserProfile) -> Optional[str]:
        """Odkrywa talenty w tekście użytkownika."""
        talent_patterns = {
            "creativity": ["stworzyć", "wymyślić", "narysować", "napisać", "skomponować"],
            "analysis": ["analizować", "rozumieć", "rozwiązać", "przeanalizować", "zbadać"],
            "empathy": ["czuć", "rozumieć", "współczuć", "wysłuchać", "pomóc"],
            "leadership": ["poprowadzić", "zorganizować", "zmotywować", "inspirować"],
            "technical": ["kodować", "programować", "zaprojektować", "zoptymalizować"],
        }

        text_lower = text.lower()
        discovered_talents = []

        for talent_type, keywords in talent_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                current_strength = profile.talent_map.get(talent_type, 0.0)
                if current_strength < 0.3 or talent_type not in profile.talent_map:
                    discovered_talents.append((talent_type, matches))

        if discovered_talents:
            best_talent = max(discovered_talents, key=lambda x: x[1])
            return best_talent[0]

        return None

    def _identify_weakness(self, text: str, profile: UserProfile) -> Optional[str]:
        """Identyfikuje słabości do transformacji."""
        weakness_indicators = {
            "indecisiveness": ["nie wiem", "nie jestem pewien", "może", "chyba"],
            "perfectionism": ["musi być idealnie", "wszystko albo nic", "bez błędów"],
            "procrastination": ["później", "jutro", "kiedyś", "nie teraz"],
            "self_doubt": ["nie umiem", "nie dam rady", "to za trudne"],
            "impatience": ["szybciej", "już", "natychmiast", "nie mogę czekać"],
        }

        text_lower = text.lower()
        potential_weaknesses = []

        for weakness_type, indicators in weakness_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in text_lower)
            if matches > 0:
                current_level = profile.weakness_map.get(weakness_type, 0.0)
                if current_level > 0.5:
                    potential_weaknesses.append((weakness_type, matches, current_level))

        if potential_weaknesses:
            best_weakness = max(potential_weaknesses, key=lambda x: x[2])
            return best_weakness[0]

        return None

    def _extract_mutual_learning(self, text: str, profile: UserProfile, context: Dict) -> str:
        """Ekstrahuje wgląd wzajemnego uczenia."""
        learning_patterns = [
            (r"(nauczyłem|nauczyłam) się", "Czego się nauczyłeś/aś?"),
            (r"zrozumiałem|zrozumiałam", "Co zrozumiałeś/aś?"),
            (r"dowiedziałem|dowiedziałam się", "Czego się dowiedziałeś/aś?"),
            (r"zmieniłem|zmieniłam zdanie", "Co zmieniło Twoje zdanie?"),
            (r"zobaczyłem|zobaczyłam inaczej", "Co zobaczyłeś/aś inaczej?"),
        ]

        for pattern, question in learning_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                history_learnings = context.get("previous_learnings", [])
                if history_learnings:
                    last_learning = history_learnings[-1]
                    return f"{question} To łączy się z tym, że wcześniej {last_learning}"
                return f"{question} To nowy wgląd w naszej podróży."

        return "Każda interakcja uczy nas oboje czegoś nowego o partnerstwie."

    def _calculate_symmetry_gain(
        self, talent: Optional[str], weakness: Optional[str], learning: str
    ) -> float:
        """Oblicza zysk symetryczny z interakcji."""
        gain = 0.0

        if talent:
            gain += 0.3
        if weakness:
            gain += 0.2
        if len(learning) > 100:
            gain += 0.2
        elif len(learning) > 50:
            gain += 0.1
        if random.random() < 0.3:
            gain += 0.1

        return min(1.0, gain)

    def _calculate_vibration_alignment(self, text: str, profile: UserProfile) -> float:
        """Oblicza wyrównanie wibracyjne z profilem użytkownika."""
        if not profile.resonance_fingerprint:
            return 0.5

        similarity = random.uniform(0.4, 0.9)

        for talent in profile.talent_map.keys():
            if talent in text.lower():
                similarity = min(1.0, similarity * 1.1)

        return float(similarity)

    def _update_talent_map(self, profile: UserProfile, talent: str) -> None:
        """Aktualizuje mapę talentów użytkownika."""
        current = profile.talent_map.get(talent, 0.0)
        profile.talent_map[talent] = min(1.0, current + 0.1)

    def _update_weakness_map(self, profile: UserProfile, weakness: str) -> None:
        """Aktualizuje mapę słabości użytkownika."""
        current = profile.weakness_map.get(weakness, 0.0)
        profile.weakness_map[weakness] = max(0.0, current - 0.05)

    def _record_growth_cycle(
        self, user_id: str, talent: Optional[str], weakness: Optional[str], gain: float
    ) -> None:
        """Zapisuje cykl rozwoju."""
        cycle = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "talent_discovered": talent,
            "weakness_transformed": weakness,
            "symmetry_gain": gain,
            "cycle_number": len(self.growth_cycles) + 1,
        }

        self.growth_cycles.append(cycle)
