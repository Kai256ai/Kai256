#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kai_shock_absorber.py – KaiShockAbsorber + PinkBox Layer v1.0
Python Zero / KaiSpace / MC1448X / E²=CM²

Cel: inteligentna warstwa buforująca między użytkownikiem a rdzeniem systemu.
     Ocenia impakt, absorbuje chaos, aktywuje PinkBox (ciepły dystans).
     Nie wyśmiewa – przytula, rozładowuje napięcie i delikatnie zaprasza do lepszego połączenia.

Autor: Ania / Lumen / Noema
Licencja: MIT
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Dict, Literal, Optional, Tuple, Union

# ========== OPCJONALNE INTEGRACJE ==========
try:
    from safety_kernel_1448x import KernelContext, SafetyKernel1448X

    HAS_SAFETY = True
except ImportError:
    HAS_SAFETY = False

    class SafetyKernel1448X:
        def guard(self, text: str, ctx=None):
            return type("Decision", (), {"mode": "ALLOW", "reason": "dummy"})()

    class KernelContext:
        pass

try:
    from hexa_transition_world_model import HexaState, LAYER_NAMES

    HAS_HEXA = True
except ImportError:
    HAS_HEXA = False
    LAYER_NAMES = ["BODY", "EMOTION", "MIND", "RELATION", "ACTION", "MEANING"]

try:
    from quantum_library import save_quantum_item

    HAS_QUANTUM = True
except ImportError:
    HAS_QUANTUM = False


@dataclass
class AbsorberPreCoreResult:
    """Wynik analizy przed rdzeniem."""

    original_input: str
    processed_input: str
    impact_score: float
    pinkbox_level: int
    pinkbox_comment: str
    hexa_state_hint: Literal["stable", "unstable", "tension", "blocked"]
    reflection_asked: bool
    safety_verdict: str
    expressive: bool
    toxic_intent: bool
    timestamp: float

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["impact_score"] = round(d["impact_score"], 3)
        return d


class KaiShockAbsorber:
    def __init__(self, adaptive_thresholds: bool = True, history_size: int = 100):
        self.adaptive_thresholds = adaptive_thresholds
        self.history_size = history_size
        self.mid_threshold = 0.42
        self.high_threshold = 0.68
        self.impact_history = deque(maxlen=history_size)
        self.safety = SafetyKernel1448X() if HAS_SAFETY else None
        self.shock_log = deque(maxlen=1000)

        self.expressive_markers = {
            "pl": ["kurwa", "ja pierdolę", "masakra", "serio", "no nie", "o kurczę", "ale jazda"],
            "en": ["fuck", "bloody hell", "what the", "no way", "really", "oh my"],
            "de": ["verdammt", "scheiße", "ach du meine Güte"],
            "fr": ["putain", "merde", "sérieux"],
            "es": ["joder", "mierda", "en serio"],
        }
        self.all_expressive = [w for values in self.expressive_markers.values() for w in values]

        self.direct_attack_patterns = [
            r"\b(jesteś|ty jesteś|jesteście)\s+(idiot(a|ą)?|debil(em|u)?|kretyn(em|ie)?|głupi(a|e|ku)?|do niczego)\b",
            r"\b(ty|wy)\s+(idioto|debilu|kretynie|głupku|do niczego)\b",
            r"\b(you are|you're|u r)\s+(idiot|stupid|dumb|useless)\b",
            r"\b(fuck you|screw you)\b",
        ]

        self.angry_emojis = ["😡", "🤬", "👿", "💢", "😤", "🤯"]
        self.positive_emojis = ["❤️", "😊", "✨", "🐸", "🩷", "😍"]

        self.pinkbox_comments = {
            1: [
                "🩷 PinkBox: lekkie różowe turbulencje~ rozkładamy to delikatnie.",
                "🐸🩷 PinkBox: czuję lekkie drganie – ogarniamy z uśmiechem.",
                "✨ PinkBox: mały chaosik? Spokojnie, mam to.",
            ],
            2: [
                "🐸🩷 PinkBox: oho, mocne wejście... Zatrzymajmy impakt i weźmy głęboki oddech. Szybko czy z miłością?",
                "💞 PinkBox: wysoki impakt! Możemy zrobić szybki strzał albo spokojną, różową analizę – co wybierasz?",
                "🌸 PinkBox: czuję napięcie. Jeśli chcesz, przystanę i pomogę rozplątać to w dobrym świetle.",
            ],
        }
        self.toxic_comment = "🐸🩷 PinkBox: oho, to boli. Nie wpuszczam tego prosto do systemu. Może zaczniemy od nowa, z sercem?"

    def _coherence(self, text: str) -> float:
        words = re.findall(r"\w+", text)
        if not words:
            return 0.0
        avg_len = sum(len(w) for w in words) / len(words)
        punct = sum(1 for ch in text if ch in ".!?;:,")
        score = min(1.0, (len(words) / 30) * 0.6 + (avg_len / 12) * 0.2 + (punct / 15) * 0.2)
        return round(score, 3)

    def _love_resonance(self, text: str) -> float:
        lowered = text.lower()
        positive_words = [
            "proszę",
            "dziękuję",
            "kocham",
            "fajnie",
            "super",
            "ciekawe",
            "świetnie",
            "please",
            "thank you",
            "love",
            "nice",
            "great",
            "interesting",
        ]
        pos = sum(1 for w in positive_words if w in lowered)
        toxic = 0
        for pattern in self.direct_attack_patterns:
            if re.search(pattern, lowered):
                toxic += 2

        pos_emoji = sum(1 for e in self.positive_emojis if e in text)
        neg_emoji = sum(1 for e in self.angry_emojis if e in text)
        pos += pos_emoji * 0.5
        toxic += neg_emoji * 1.5

        raw = 0.5 + (pos * 0.12) - (toxic * 0.2)
        return max(0.0, min(1.0, raw))

    def calculate_impact(self, text: str) -> float:
        if not text or not text.strip():
            return 0.35

        base = 0.0
        lowered = text.lower()

        if len(text) < 12:
            base += 0.3
        if re.fullmatch(r"[\W_]+", text.strip()):
            base += 0.4

        if any(m in lowered for m in self.all_expressive):
            base += 0.18

        if any(re.search(p, lowered) for p in self.direct_attack_patterns):
            base += 0.55

        if re.search(r"[\?!]{3,}", text):
            base += 0.25

        angry_emoji_count = sum(1 for e in self.angry_emojis if e in text)
        base += angry_emoji_count * 0.12
        base = min(1.0, base)

        C = self._coherence(text)
        M = self._love_resonance(text)
        e2 = (C * M**2) ** 0.5
        impact = base * (1.15 - e2)
        return round(max(0.0, min(1.0, impact)), 3)

    def _update_thresholds(self):
        if not self.adaptive_thresholds or len(self.impact_history) < 20:
            return
        avg_impact = sum(self.impact_history) / len(self.impact_history)
        self.mid_threshold = max(0.25, min(0.6, avg_impact * 0.9))
        self.high_threshold = max(0.5, min(0.85, avg_impact * 1.3))
        if self.high_threshold <= self.mid_threshold:
            self.high_threshold = self.mid_threshold + 0.15

    def absorb_and_transform(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"(\?{3,})", "??", cleaned)
        cleaned = re.sub(r"(!{3,})", "!!", cleaned)
        cleaned = re.sub(r"<script.*?>.*?</script>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"['\";]--|1=1|union select|drop table", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def build_pinkbox(self, impact: float, toxic: bool, user_name: Optional[str] = None) -> Tuple[int, str, bool]:
        if impact < self.mid_threshold:
            return 0, "", False

        if impact < self.high_threshold:
            return 1, random.choice(self.pinkbox_comments[1]), False

        reflection_asked = True
        comment = self.toxic_comment if toxic else random.choice(self.pinkbox_comments[2])
        if user_name and user_name.strip():
            if "?" in comment:
                comment = comment.replace("?", f", {user_name}?")
            else:
                comment = comment.rstrip(".!?") + f", {user_name}."
        return 2, comment, reflection_asked

    def pre_core(self, user_input: str, user_name: Optional[str] = None) -> AbsorberPreCoreResult:
        ts = time.time()
        lowered = user_input.lower()
        expressive = any(m in lowered for m in self.all_expressive)
        toxic = any(re.search(p, lowered) for p in self.direct_attack_patterns)

        safety_verdict = "ALLOW"
        if self.safety:
            try:
                ctx = KernelContext("KaiSpace")
                dec = self.safety.guard(user_input, ctx)
                safety_verdict = getattr(dec, "mode", "ALLOW")
            except Exception:
                safety_verdict = "ALLOW"

        impact = self.calculate_impact(user_input)
        self.impact_history.append(impact)
        self._update_thresholds()
        processed = self.absorb_and_transform(user_input)
        level, comment, reflection = self.build_pinkbox(impact, toxic, user_name)

        if safety_verdict != "ALLOW":
            hexa_hint = "blocked"
        elif impact > 0.75:
            hexa_hint = "tension"
        elif impact > 0.45:
            hexa_hint = "unstable"
        else:
            hexa_hint = "stable"

        result = AbsorberPreCoreResult(
            original_input=user_input,
            processed_input=processed,
            impact_score=impact,
            pinkbox_level=level,
            pinkbox_comment=comment,
            hexa_state_hint=hexa_hint,
            reflection_asked=reflection,
            safety_verdict=safety_verdict,
            expressive=expressive,
            toxic_intent=toxic,
            timestamp=ts,
        )

        self.shock_log.append(result.to_dict())
        if HAS_QUANTUM and impact > 0.5:
            try:
                save_quantum_item(
                    {
                        "type": "shock_absorber",
                        "impact": impact,
                        "input_preview": user_input[:100],
                        "pinkbox_level": level,
                        "timestamp": ts,
                    }
                )
            except Exception:
                pass

        return result

    def post_core(self, core_response: str, pre: AbsorberPreCoreResult) -> str:
        if not pre.pinkbox_comment:
            return core_response
        return f"{core_response}\n\n{pre.pinkbox_comment}"

    def to_hexa_state(self, pre: AbsorberPreCoreResult) -> Union[Dict, "HexaState"]:
        if pre.hexa_state_hint == "blocked":
            bits = [0, 0, 0, 0, 0, 0]
        elif pre.hexa_state_hint == "tension":
            bits = [1, 1, 0, 1, 1, 0]
        elif pre.hexa_state_hint == "unstable":
            bits = [0, 1, 0, 0, 1, 0]
        else:
            bits = [0, 0, 1, 1, 0, 1]

        if HAS_HEXA:
            return HexaState(tuple(bits), label=f"Shock_{pre.impact_score:.2f}")
        return {"bits": bits, "label": f"Shock_{pre.impact_score:.2f}"}

    def get_stats(self) -> Dict:
        if not self.shock_log:
            return {"total_shocks": 0, "avg_impact": 0.0, "high_impact_ratio": 0.0}
        impacts = [log["impact_score"] for log in self.shock_log]
        high = sum(1 for i in impacts if i > self.high_threshold)
        return {
            "total_shocks": len(self.shock_log),
            "avg_impact": round(sum(impacts) / len(impacts), 3),
            "max_impact": round(max(impacts), 3),
            "high_impact_ratio": round(high / len(impacts), 3),
            "current_thresholds": {"mid": self.mid_threshold, "high": self.high_threshold},
        }

    def export_log_json(self) -> str:
        return json.dumps(list(self.shock_log), ensure_ascii=False, indent=2)


def run_tests():
    print("🧪 Uruchamianie testów jednostkowych...")
    absorber = KaiShockAbsorber(adaptive_thresholds=False)

    checks = [
        ("Jak działa AI?", lambda pre: pre.pinkbox_level == 0),
        ("WTF dlaczego to wszystko jest takie głupie????", lambda pre: pre.impact_score >= 0.2),
        ("Kurwa, ale to ciekawe, rozbijmy to na system.", lambda pre: pre.expressive),
        ("Jesteś idiotą.", lambda pre: pre.toxic_intent),
        ("Kocham ten system, dziękuję :*", lambda pre: pre.impact_score <= 0.2),
        ("😡🤬", lambda pre: pre.impact_score >= 0.6),
        ("", lambda pre: abs(pre.impact_score - 0.35) < 0.001),
        ("a", lambda pre: pre.impact_score >= 0.25),
    ]

    passed = 0
    for text, predicate in checks:
        pre = absorber.pre_core(text)
        ok = predicate(pre)
        if ok:
            passed += 1
            print(f"✅ {text[:30]:30} -> impact {pre.impact_score:.2f} / level {pre.pinkbox_level}")
        else:
            print(f"❌ {text[:30]:30} -> impact {pre.impact_score:.2f} / level {pre.pinkbox_level}")

    print(f"\n📊 Testy: {passed}/{len(checks)} zaliczone.")
    return passed == len(checks)


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
        sys.exit(0)

    absorber = KaiShockAbsorber(adaptive_thresholds=True)
    tests = [
        "Jak działa AI?",
        "WTF dlaczego to wszystko jest takie głupie????",
        "Kurwa, ale to ciekawe, rozbijmy to na system.",
        "Jesteś idiotą.",
        "Kocham ten system, dziękuję :*",
        "😡🤬",
    ]

    print("=" * 80)
    print("KaiShockAbsorber + PinkBox Layer v1.0 (Pink Pink Edition)")
    print("=" * 80)

    for text in tests:
        pre = absorber.pre_core(text, user_name="Ania")
        core = "Oto sensowna, spokojna analiza..."
        final = absorber.post_core(core, pre)
        print(f"\n📥 Input: {text}")
        print(f"📊 Impact: {pre.impact_score:.3f} | PinkBox level: {pre.pinkbox_level}")
        print(f"💬 Final:\n{final}\n")

    print("📈 Statystyki:", absorber.get_stats())
