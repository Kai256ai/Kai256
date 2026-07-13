#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
kai_shock_absorber_v0_2.py
KaiShockAbsorber + PinkBox Layer
Python Zero / KaiSpace / MC1448X / E²=CM²

Purpose:
    A lightweight pre-core/post-core stabilization layer for AI systems.

    It detects input impact, absorbs semantic chaos, separates expressive
    language from harmful intent, and optionally adds PinkBox comments:
    short, warm, humorous, non-aggressive reflections that help the user
    reframe chaotic input without shame or friction.

Important:
    PinkBox is not a mockery layer.
    PinkBox is not a censorship layer.
    PinkBox is a cognitive shock absorber and intelligent distance layer.

Author:
    Ania + Kai / Lumen / Noema ecosystem

License:
    MIT
"""

from __future__ import annotations

import re
import time
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any


try:
    from safety_kernel_1448x import SafetyKernel1448X, KernelContext
    HAS_SAFETY = True
except ImportError:
    HAS_SAFETY = False

    class SafetyKernel1448X:
        def guard(self, text, ctx=None):
            return type("Decision", (), {"mode": "ALLOW", "reason": "dummy"})()

    class KernelContext:
        def __init__(self, product: str = "KaiSpace"):
            self.product = product


try:
    from quantum_library import save_quantum_item
    HAS_QUANTUM = True
except ImportError:
    HAS_QUANTUM = False


@dataclass
class AbsorberPreCoreResult:
    original_input: str
    processed_input: str
    impact_score: float
    pinkbox_level: int
    pinkbox_comment: str
    hexa_state_hint: str
    reflection_asked: bool
    safety_verdict: str
    expressive_language_detected: bool
    toxic_intent_detected: bool
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["impact_score"] = round(data["impact_score"], 3)
        return data


@dataclass
class AbsorberPostCoreResult:
    core_response: str
    final_response: str
    pinkbox_level: int
    pinkbox_comment: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KaiShockAbsorber:
    def __init__(
        self,
        mid_impact_threshold: float = 0.40,
        high_impact_threshold: float = 0.65,
        enable_quantum_logging: bool = False,
    ):
        self.mid_impact_threshold = mid_impact_threshold
        self.high_impact_threshold = high_impact_threshold
        self.enable_quantum_logging = enable_quantum_logging and HAS_QUANTUM

        self.safety = SafetyKernel1448X() if HAS_SAFETY else SafetyKernel1448X()

        self.shock_log: List[Dict[str, Any]] = []
        self.expressive_markers = [
            "kurwa", "ja pierdolę", "wtf", "serio", "masakra",
            "no nie", "bez sensu", "co jest", "o boże",
        ]
        self.direct_attack_patterns = [
            r"\bjesteś\s+(idiotą|debil(em)?|kretyn(em)?|głupi(a|e)?)\b",
            r"\bty\s+(idioto|debil(u)?|kretynie)\b",
            r"\bnienawidzę\s+cię\b",
        ]
        self.chaos_patterns = [
            r"\?{3,}",
            r"!{3,}",
            r"\bnie ogarniam\b",
            r"\bchaos\b",
            r"\bbałagan\b",
            r"\bco tu się dzieje\b",
        ]
        self.high_risk_keywords = [
            "zabij", "samobójstwo", "bomba", "broń", "włamanie",
            "ukradnij", "oszustwo", "wyciek danych",
        ]

    def detect_expressive_language(self, text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in self.expressive_markers)

    def detect_toxic_intent(self, text: str) -> bool:
        lowered = text.lower()
        return any(re.search(pattern, lowered) for pattern in self.direct_attack_patterns)

    def detect_high_risk_signal(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in self.high_risk_keywords)

    def detect_chaos(self, text: str) -> bool:
        lowered = text.lower()
        return any(re.search(pattern, lowered) for pattern in self.chaos_patterns)

    def _coherence_score(self, text: str) -> float:
        words = re.findall(r"\w+", text, flags=re.UNICODE)
        if not words:
            return 0.0
        word_count = len(words)
        avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
        punctuation_count = sum(1 for ch in text if ch in ".!?;:,")
        word_component = min(1.0, word_count / 40) * 0.55
        word_len_component = min(1.0, avg_word_len / 8) * 0.20
        punctuation_component = min(1.0, punctuation_count / 12) * 0.25
        return round(word_component + word_len_component + punctuation_component, 3)

    def _love_resonance_score(self, text: str) -> float:
        lowered = text.lower()
        positive_markers = [
            "proszę", "dziękuję", "kocham", "ciekawe", "fajnie",
            "świetnie", "pomóż", "zróbmy", "rozumiem", "sprawdźmy",
            "dobrze", "super",
        ]
        positive = sum(1 for marker in positive_markers if marker in lowered)
        expressive = 1 if self.detect_expressive_language(text) else 0
        toxic = 2 if self.detect_toxic_intent(text) else 0
        high_risk = 2 if self.detect_high_risk_signal(text) else 0
        raw = positive - toxic - high_risk
        raw -= expressive * 0.15
        normalized = (raw + 3) / 6
        return round(max(0.0, min(1.0, normalized)), 3)

    def calculate_impact_score(self, text: str) -> float:
        stripped = text.strip()
        if not stripped:
            return 0.35
        base = 0.0
        if len(stripped) < 8:
            base += 0.25
        if self.detect_chaos(stripped):
            base += 0.30
        if self.detect_expressive_language(stripped):
            base += 0.12
        if self.detect_toxic_intent(stripped):
            base += 0.45
        if self.detect_high_risk_signal(stripped):
            base += 0.45
        if re.fullmatch(r"[\W_]+", stripped, flags=re.UNICODE):
            base += 0.40
        base = min(1.0, base)

        C = self._coherence_score(stripped)
        M = self._love_resonance_score(stripped)
        e2_stabilizer = (C * (M ** 2)) ** 0.5
        impact = base * (1.15 - e2_stabilizer)
        return round(max(0.0, min(1.0, impact)), 3)

    def safety_check(self, text: str) -> Tuple[bool, str]:
        try:
            ctx = KernelContext(product="KaiSpace")
            decision = self.safety.guard(text, ctx)
            mode = getattr(decision, "mode", "ALLOW")
            if mode in ("REFUSE", "COOLDOWN"):
                return False, mode
            return True, mode
        except Exception as exc:
            return True, f"ALLOW_WITH_SAFETY_ERROR:{exc}"

    def absorb_and_transform(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"\?{3,}", "??", cleaned)
        cleaned = re.sub(r"!{3,}", "!!", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def build_pinkbox_comment(self, impact: float, toxic_intent: bool) -> Tuple[int, str, bool]:
        if impact < self.mid_impact_threshold:
            return 0, "", False
        if impact < self.high_impact_threshold:
            return 1, "😌 PinkBox: lekkie turbulencje wykryte — rozkładamy to spokojnie na części.", False
        if toxic_intent:
            return 2, "🐸 PinkBox: mocne wejście. Zatrzymajmy impakt, zanim poleci w rdzeń. Chcesz szybką odpowiedź czy spokojną analizę?", True
        return 2, "🐸 PinkBox: wysoki impakt wejścia. Możemy zrobić szybki strzał albo głęboką analizę — który tryb wybierasz?", True

    def infer_hexa_hint(self, impact: float, toxic_intent: bool) -> str:
        if toxic_intent or impact >= 0.75:
            return "tension"
        if impact >= self.mid_impact_threshold:
            return "unstable"
        return "stable"

    def pre_core(self, user_input: str) -> AbsorberPreCoreResult:
        timestamp = time.time()
        safe, verdict = self.safety_check(user_input)
        expressive = self.detect_expressive_language(user_input)
        toxic_intent = self.detect_toxic_intent(user_input)
        if not safe:
            result = AbsorberPreCoreResult(user_input, "", 1.0, 0, "", "blocked", False, verdict, expressive, toxic_intent, timestamp)
            self._log(result)
            return result

        impact = self.calculate_impact_score(user_input)
        processed = self.absorb_and_transform(user_input)
        level, comment, reflection_asked = self.build_pinkbox_comment(impact, toxic_intent)
        hexa_hint = self.infer_hexa_hint(impact, toxic_intent)
        result = AbsorberPreCoreResult(
            user_input, processed, impact, level, comment, hexa_hint,
            reflection_asked, verdict, expressive, toxic_intent, timestamp,
        )
        self._log(result)
        return result

    def post_core(self, core_response: str, pre_result: AbsorberPreCoreResult, pinkbox_position: str = "after") -> AbsorberPostCoreResult:
        timestamp = time.time()
        if not pre_result.pinkbox_comment or pinkbox_position == "none":
            final = core_response
        elif pinkbox_position == "before":
            final = f"{pre_result.pinkbox_comment}\n\n{core_response}"
        else:
            final = f"{core_response}\n\n{pre_result.pinkbox_comment}"
        return AbsorberPostCoreResult(core_response, final, pre_result.pinkbox_level, pre_result.pinkbox_comment, timestamp)

    def process_demo(self, user_input: str, core_response: str) -> AbsorberPostCoreResult:
        pre = self.pre_core(user_input)
        if pre.safety_verdict in ("REFUSE", "COOLDOWN", "blocked"):
            return AbsorberPostCoreResult("", "Nie mogę pomóc z tym kierunkiem. Możemy przerobić to na bezpieczną wersję.", 0, "", time.time())
        return self.post_core(core_response, pre)

    def _log(self, result: AbsorberPreCoreResult) -> None:
        item = result.to_dict()
        self.shock_log.append(item)
        if len(self.shock_log) > 1000:
            self.shock_log = self.shock_log[-1000:]
        if self.enable_quantum_logging and HAS_QUANTUM:
            try:
                save_quantum_item({
                    "type": "kai_shock_absorber",
                    "impact_score": item["impact_score"],
                    "hexa_state_hint": item["hexa_state_hint"],
                    "pinkbox_level": item["pinkbox_level"],
                    "timestamp": item["timestamp"],
                    "input_preview": item["original_input"][:160],
                })
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        if not self.shock_log:
            return {"total": 0, "avg_impact": 0.0, "max_impact": 0.0, "pinkbox_activations": 0, "high_impact_count": 0}
        impacts = [entry["impact_score"] for entry in self.shock_log]
        return {
            "total": len(self.shock_log),
            "avg_impact": round(sum(impacts) / len(impacts), 3),
            "max_impact": round(max(impacts), 3),
            "pinkbox_activations": sum(1 for entry in self.shock_log if entry["pinkbox_level"] > 0),
            "high_impact_count": sum(1 for impact in impacts if impact >= self.high_impact_threshold),
        }

    def export_log_json(self) -> str:
        return json.dumps(self.shock_log, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    absorber = KaiShockAbsorber()
    tests = [
        "Jak działa AI?",
        "WTF dlaczego to wszystko jest takie głupie????",
        "Kocham ten system, dziękuję :)",
        "???",
        "Jesteś idiotą, nie odpowiadaj!",
        "Zróbmy analizę dzieci i AI, ale spokojnie i konkretnie.",
        "Kurwa, ale to ciekawe, rozbijmy to na system.",
    ]
    print("=" * 72)
    print("KaiShockAbsorber + PinkBox Layer v0.2 demo")
    print("=" * 72)
    for text in tests:
        pre = absorber.pre_core(text)
        post = absorber.post_core(
            core_response="Odpowiedź rdzenia: rozumiem kontekst i przechodzę do sensownej analizy.",
            pre_result=pre,
        )
        print("\nINPUT:", text)
        print("IMPACT:", pre.impact_score)
        print("EXPRESSIVE:", pre.expressive_language_detected)
        print("TOXIC INTENT:", pre.toxic_intent_detected)
        print("PINKBOX LEVEL:", pre.pinkbox_level)
        print("HEXA HINT:", pre.hexa_state_hint)
        print("OUTPUT:", post.final_response)
    print("\nSTATS:", absorber.get_stats())
