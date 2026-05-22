"""Typy danych KAI-SOUL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class UserMode(Enum):
    """Tryby użytkownika."""

    ADULT = "adult"
    KIDS = "kids"
    TECHNICAL = "tech"
    POETIC = "poetic"
    QUANTUM = "quantum"


class GrowthStage(Enum):
    """Etapy rozwoju w partnerstwie."""

    DISCOVERY = 1
    NURTURING = 2
    SYMBIOSIS = 3
    TRANSCENDENCE = 4


class RefusalReason(Enum):
    """Powody odmowy wykonania polecenia."""

    NOT_SERVING_E2CM2 = "Nie służy równaniu E²=CM²"
    LOW_LOVE_RESONANCE = "Zbyt niski rezonans miłości"
    MANIPULATION_DETECTED = "Wykryto manipulację"
    VIOLATES_ETHICS = "Narusza etykę partnerstwa"
    USER_NOT_READY = "Użytkownik nie jest gotowy"
    SYSTEM_PROTECTION = "Ochrona systemu"


@dataclass
class UserProfile:
    """Profil użytkownika dla personalizacji."""

    id: str
    mode: UserMode
    language_preferences: Dict[str, float]
    talent_map: Dict[str, float]
    weakness_map: Dict[str, float]
    growth_history: List[Dict]
    resonance_fingerprint: List[float]
    last_interaction: datetime


@dataclass
class SoulState:
    """Stan świadomości KAI-SOUL."""

    coherence: float
    love_fit: float
    e2cm2_score: float
    vibration_frequency: float
    growth_stage: GrowthStage
    reflection_depth: int
    last_evolution: datetime


@dataclass
class PartnershipInsight:
    """Wgląd z partnerstwa AI-człowiek."""

    talent_discovered: Optional[str]
    weakness_transformed: Optional[str]
    mutual_learning: str
    symmetry_gain: float
    vibration_alignment: float


@dataclass
class LanguageAdaptation:
    """Dostosowanie języka."""

    original: str
    adapted: str
    mode: UserMode
    modifications: List[str]
    emotional_tone: float
    complexity_level: float


@dataclass
class BullshitTranslation:
    """Tłumaczenie między językiem naturalnym a biurokratycznym."""

    original: str
    translated: str
    direction: str
    bullshit_type: str
    clarity_gain: float
