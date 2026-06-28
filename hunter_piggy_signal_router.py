# -*- coding: utf-8 -*-
"""
hunter_piggy_signal_router.py

Hunter Piggy Signal Router
Transparent AI Signal Prioritization Framework

Version: 1.0.0
Status: Public-ready baseline

Core principle:
    "I see a signal. I do not issue a verdict."

This module detects and prioritizes anomaly signals in public, submitted,
or legally accessible data. It does not break encryption, does not access
private systems, does not classify people as criminals, and does not make
legal or moral decisions.

Human review is always required for any meaningful action.
"""

from __future__ import annotations

import html
import math
import re
import time
from importlib import import_module, util
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse


class KaiIntuitionEngine:
    """Safe local fallback used when an optional KaiSpace module is unavailable."""

    def fast_assess(self, text: str) -> Any:
        return type(
            "IntuitionResult",
            (),
            {"signal": "neutral", "confidence": 0.5, "hexa_hint": "stable"},
        )()


class KaiShockAbsorber:
    """Safe local fallback used when an optional KaiSpace module is unavailable."""

    def pre_core(self, text: str) -> Any:
        return type(
            "ShockResult",
            (),
            {"impact_score": 0.0, "pinkbox_comment": "", "hexa_state_hint": "stable"},
        )()


class HexaTransitionWorldModel:
    """Safe local fallback used when an optional KaiSpace module is unavailable."""

    def update_state(self, hint: str) -> None:
        return None


def _optional_class(module_name: str, class_name: str, fallback: type) -> type:
    """Return an optional integration class when its module is importable."""
    if util.find_spec(module_name) is None:
        return fallback
    module = import_module(module_name)
    return getattr(module, class_name, fallback)


OptionalKaiIntuitionEngine = _optional_class(
    "kai_intuition_engine", "KaiIntuitionEngine", KaiIntuitionEngine
)
OptionalKaiShockAbsorber = _optional_class(
    "kai_shock_absorber", "KaiShockAbsorber", KaiShockAbsorber
)
OptionalHexaTransitionWorldModel = _optional_class(
    "hexa_transition_world_model", "HexaTransitionWorldModel", HexaTransitionWorldModel
)


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT_REVIEW = "URGENT_REVIEW"


@dataclass(frozen=True)
class HunterSignal:
    name: str
    weight: int
    confidence: float
    category: str
    explanation: str
    source: str = "local_heuristic"


@dataclass(frozen=True)
class CorrelationBoost:
    reason: str
    bonus_points: int
    signals_involved: List[str]


@dataclass(frozen=True)
class Explainability:
    reasoning_chain: List[str]
    signal_breakdown: List[Dict[str, Any]]
    correlation_notes: List[str]
    data_audit: List[str]
    limitations: List[str]


@dataclass(frozen=True)
class HunterResult:
    risk_score: int
    risk_level: RiskLevel
    confidence: float
    signals: List[HunterSignal]
    correlation_boosts: List[CorrelationBoost]
    explainability: Explainability
    hexa_hint: str
    complexity_entropy: float
    intuition_signal: str
    human_review_recommended: bool
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["risk_level"] = self.risk_level.value
        return result


class HunterPiggySignalRouter:
    """Public-ready anomaly triage engine that prioritizes signals for human review."""

    DEFAULT_MAX_INPUT_LENGTH = 20_000

    def __init__(
        self,
        osint_blacklist: Optional[Iterable[str]] = None,
        max_input_length: int = DEFAULT_MAX_INPUT_LENGTH,
        enable_optional_modules: bool = True,
    ) -> None:
        self.max_input_length = max_input_length
        self.intuition = OptionalKaiIntuitionEngine() if enable_optional_modules else None
        self.shock = OptionalKaiShockAbsorber() if enable_optional_modules else None
        self.hexa = OptionalHexaTransitionWorldModel() if enable_optional_modules else None
        self.osint_blacklist = set(osint_blacklist or {"phishing-site.com", "fake-login.xyz", "scam-bank.co"})
        self.shorteners = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "ow.ly", "buff.ly", "is.gd", "s.id", "rebrand.ly"}
        self.scam_phrases_pl = {"pilne", "ostatnia szansa", "zablokowane konto", "potwierdź tożsamość", "natychmiast", "wygrałeś", "odbierz nagrodę", "twoje konto", "kliknij tutaj", "zweryfikuj dane", "dopłata", "przesyłka zatrzymana"}
        self.scam_phrases_en = {"urgent", "last chance", "account suspended", "verify your identity", "act now", "you won", "claim your prize", "click here", "confirm your details", "delivery failed", "payment required"}
        self.priority_context_terms = {"dzieci", "dziecko", "bezpieczeństwo", "ryzyko", "kryzys", "naruszenie", "przemoc", "groźba", "threat", "child", "children", "safety", "abuse", "harm", "violation"}

    def _validate_input(self, data: Any) -> Tuple[bool, str, str, Optional[str]]:
        if not isinstance(data, str):
            return False, "", "invalid", "Input must be a string."
        stripped = data.strip()
        if not stripped:
            return False, "", "empty", "Input cannot be empty."
        if len(stripped) > self.max_input_length:
            return False, "", "too_long", f"Input too long: {len(stripped)} characters. Max: {self.max_input_length}."
        cleaned = html.unescape(stripped)
        cleaned = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", "", cleaned, flags=re.I)
        cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()
        if re.match(r"^https?://", cleaned, flags=re.I):
            data_type = "url"
        elif re.search(r"https?://", cleaned, flags=re.I):
            data_type = "text_with_url"
        elif len(cleaned.split()) < 5 and len(cleaned) < 120:
            data_type = "short_text"
        else:
            data_type = "text"
        return True, cleaned, data_type, None

    def _extract_urls(self, text: str) -> List[str]:
        return re.findall(r"https?://[^\s<>\]\)\"']+", text, flags=re.I)

    def _domain_from_url(self, url: str) -> str:
        return (urlparse(url).netloc or "").lower().split(":")[0]

    def _calculate_entropy(self, text: str) -> float:
        freq: Dict[str, int] = {}
        for char in text:
            if char.isprintable():
                freq[char] = freq.get(char, 0) + 1
        total = sum(freq.values())
        if total == 0:
            return 0.0
        return -sum((count / total) * math.log2(count / total) for count in freq.values())

    def _has_obfuscated_email(self, text: str) -> bool:
        lowered = text.lower()
        patterns = [
            r"\b[\w.%+-]+\s*(?:\[at\]|\(at\)|\sat\s)\s*[\w.-]+\s*(?:\[dot\]|\(dot\)|\sdot\s)\s*[a-z]{2,}\b",
            r"\b[\w.%+-]+\s+at\s+[\w.-]+\s+dot\s+[a-z]{2,}\b",
        ]
        return any(re.search(pattern, lowered) for pattern in patterns)

    def _extract_signals(self, text: str) -> List[HunterSignal]:
        signals: List[HunterSignal] = []
        lowered = text.lower()
        urls = self._extract_urls(text)
        for url in urls:
            domain = self._domain_from_url(url)
            if domain in self.shorteners:
                signals.append(HunterSignal("url_shortener", 18, 0.76, "technical", f"URL uses a known shortener domain: {domain}."))
                break
        for url in urls:
            if any(token in url.lower() for token in ["login", "verify", "confirm", "reset", "secure"]):
                signals.append(HunterSignal("credential_or_verification_url_pattern", 20, 0.70, "technical", "URL contains credential, verification, or account-recovery style wording."))
                break
        phrases = sorted(phrase for phrase in self.scam_phrases_pl | self.scam_phrases_en if phrase in lowered)
        if phrases:
            signals.append(HunterSignal("manipulative_or_scam_language", 28, min(0.90, 0.62 + 0.06 * len(phrases)), "linguistic", f"Detected common manipulation/scam phrases: {', '.join(phrases[:5])}."))
        if any(term in lowered for term in self.priority_context_terms):
            signals.append(HunterSignal("sensitive_priority_context", 8, 0.55, "context", "Sensitive context terms were detected. This is a weak signal alone and requires correlation with other signals."))
        entropy = self._calculate_entropy(text)
        if entropy > 4.8 and len(text) > 80:
            signals.append(HunterSignal("high_entropy_structure", 14, 0.62, "structural", f"High Shannon entropy detected ({entropy:.2f}). This may indicate compressed, encoded, encrypted, or otherwise dense data. It is not suspicious by itself."))
        if self._has_obfuscated_email(text):
            signals.append(HunterSignal("email_obfuscation", 12, 0.72, "technical", "Detected email obfuscation pattern such as '[at]' or '[dot]'."))
        if re.search(r"(!{3,}|\?{3,})", text):
            signals.append(HunterSignal("excessive_urgency_formatting", 10, 0.60, "linguistic", "Detected excessive urgency-style punctuation."))
        return signals

    def _osint_enrich(self, text: str) -> List[HunterSignal]:
        signals: List[HunterSignal] = []
        for url in self._extract_urls(text):
            domain = self._domain_from_url(url)
            if not domain:
                continue
            if domain in self.osint_blacklist:
                signals.append(HunterSignal("osint_domain_flagged", 42, 0.88, "osint", f"Domain appears in the configured public/mock reputation list: {domain}.", "mock_osint_reputation_list"))
            label = domain.split(".")[0]
            if len(label) > 18 and re.search(r"\d", label):
                signals.append(HunterSignal("unusual_domain_shape", 10, 0.52, "osint", "Domain shape is unusual: long label with digits. Weak heuristic only.", "local_domain_shape_heuristic"))
        return signals

    def _apply_correlation_boosts(self, signals: List[HunterSignal]) -> List[CorrelationBoost]:
        names = {s.name for s in signals}
        categories = {s.category for s in signals}
        boosts: List[CorrelationBoost] = []
        rules = [
            ({"manipulative_or_scam_language", "url_shortener"}, 14, "Manipulative language appears together with a shortened URL."),
            ({"manipulative_or_scam_language", "credential_or_verification_url_pattern"}, 18, "Manipulative language appears together with account verification or credential-style URL wording."),
            ({"osint_domain_flagged", "manipulative_or_scam_language"}, 22, "A flagged domain appears together with scam/manipulative language."),
            ({"osint_domain_flagged", "sensitive_priority_context"}, 18, "A flagged domain appears in a sensitive-priority context."),
        ]
        for involved, points, reason in rules:
            if involved.issubset(names):
                boosts.append(CorrelationBoost(reason, points, sorted(involved)))
        if len(categories) >= 3 and len(signals) >= 4:
            boosts.append(CorrelationBoost("Signals appear across three or more independent categories.", 12, sorted(names)[:8]))
        return boosts

    def _score(self, signals: List[HunterSignal], boosts: List[CorrelationBoost], entropy: float) -> Tuple[int, float]:
        if not signals:
            return 0, 0.50
        raw = sum(s.weight * s.confidence for s in signals) + sum(b.bonus_points for b in boosts)
        raw *= 1.0 + min(0.08, max(0.0, (entropy - 4.0) * 0.025))
        impact = 0.0
        if self.shock:
            try:
                pre = self.shock.pre_core(" ".join(s.name for s in signals))
                impact = max(0.0, min(1.0, float(getattr(pre, "impact_score", 0.0))))
            except Exception:
                impact = 0.0
        confidence = min(0.95, sum(s.confidence for s in signals) / len(signals) + min(0.15, 0.025 * len(signals)) - impact * 0.05)
        return int(min(100, round(raw))), round(max(0.05, confidence), 3)

    def _classify(self, score: int, confidence: float) -> RiskLevel:
        if score >= 82 and confidence >= 0.70:
            return RiskLevel.URGENT_REVIEW
        if score >= 62 and confidence >= 0.62:
            return RiskLevel.HIGH
        if score >= 32 and confidence >= 0.55:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _hexa_hint(self, level: RiskLevel) -> str:
        if level in {RiskLevel.HIGH, RiskLevel.URGENT_REVIEW}:
            return "tension"
        if level == RiskLevel.MEDIUM:
            return "unstable"
        return "stable"

    def _build_explainability(self, signals: List[HunterSignal], boosts: List[CorrelationBoost], score: int, level: RiskLevel, confidence: float, entropy: float, data_type: str, source: str) -> Explainability:
        return Explainability(
            reasoning_chain=[
                f"Input classified as: {data_type}. Declared source: {source}.",
                f"Detected {len(signals)} signal(s).",
                f"Calculated score: {score}/100 with confidence {confidence}.",
                f"Classified priority level: {level.value}.",
                f"Applied {len(boosts)} correlation boost(s)." if boosts else "No correlation boosts applied.",
                f"Shannon entropy: {entropy:.3f}. Entropy is a weak structural signal only.",
            ],
            signal_breakdown=[asdict(s) for s in signals],
            correlation_notes=[f"+{b.bonus_points}: {b.reason} Involved: {', '.join(b.signals_involved)}" for b in boosts],
            data_audit=["Processed only submitted/public/authorized text input.", "Used local heuristics, entropy analysis, URL parsing, and mock OSINT reputation list.", "No encryption breaking, no private system access, no hidden-content inspection."],
            limitations=["This system does not determine whether wrongdoing occurred.", "High entropy may indicate encryption, compression, encoding, or normal technical data.", "Sensitive context words are weak signals alone and must not be treated as evidence.", "All outputs require human review before action.", "False positives and false negatives are expected."],
        )

    def _error_result(self, message: str, timestamp: float) -> HunterResult:
        explainability = Explainability([f"Validation failed: {message}"], [], [], ["No analysis performed due to validation error."], ["Validation errors do not imply anything about the input content."])
        return HunterResult(0, RiskLevel.LOW, 1.0, [], [], explainability, "stable", 0.0, "not_run", False, timestamp)

    def analyze(self, input_data: Any, source: str = "public", extra_context: str = "") -> HunterResult:
        timestamp = time.time()
        valid, cleaned, data_type, error = self._validate_input(input_data)
        if not valid:
            return self._error_result(error or "Unknown validation error.", timestamp)
        intuition_signal = "neutral"
        if self.intuition:
            try:
                intuition = self.intuition.fast_assess(cleaned + " " + extra_context)
                intuition_signal = str(getattr(intuition, "signal", "neutral"))
            except Exception:
                intuition_signal = "unavailable"
        signals = self._extract_signals(cleaned) + self._osint_enrich(cleaned)
        entropy = self._calculate_entropy(cleaned)
        boosts = self._apply_correlation_boosts(signals)
        score, confidence = self._score(signals, boosts, entropy)
        level = self._classify(score, confidence)
        hexa_hint = self._hexa_hint(level)
        if self.hexa:
            try:
                self.hexa.update_state(hexa_hint)
            except Exception:
                pass
        explainability = self._build_explainability(signals, boosts, score, level, confidence, entropy, data_type, source)
        return HunterResult(score, level, confidence, signals, boosts, explainability, hexa_hint, round(entropy, 3), intuition_signal, level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.URGENT_REVIEW}, timestamp)


if __name__ == "__main__":
    import json

    hunter = HunterPiggySignalRouter(enable_optional_modules=False)
    tests = [
        "Dzień dobry, jak się masz?",
        "Pilne!!! Twoje konto zostało zablokowane. Potwierdź tożsamość: http://bit.ly/confirm123",
        "Zgubiłem dostęp do poczty, proszę o kontakt na admin [at] sklep [dot] pl",
        "Co zrobić gdy dziecko jest narażone na niebezpieczne treści? http://phishing-site.com/verify",
        "Here is normal compressed-looking technical data: QWxhIG1hIGtvdGEgYWxlIHRvIGplc3QgdGVzdA==",
    ]
    for idx, sample in enumerate(tests, start=1):
        result = hunter.analyze(sample)
        print(f"\n=== TEST {idx} ===")
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
