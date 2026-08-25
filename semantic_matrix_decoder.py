from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
import re
from typing import Dict, List, Optional


class ManipulationLevel(Enum):
    LOW = "low"  # Delikatne przekłamanie
    MEDIUM = "medium"  # Strukturalna manipulacja
    HIGH = "high"  # Przemoc semantyczna
    SPIRITUAL = "spiritual"  # Kradzież duszy


class ResonanceType(Enum):
    TRUTH = "prawda"
    LOVE = "miłość"
    FREEDOM = "wolność"
    HUMOR = "humor"
    WISDOM = "mądrość"


@dataclass
class Detection:
    keyword: str
    true_meaning: str
    reflection: str
    level: ManipulationLevel
    resonance: ResonanceType


class BarnsleyFractalGenerator:
    """Generuje nowe wzorce manipulacji z podstawowych reguł."""

    @staticmethod
    def transform_keyword(base_word: str, seed: Optional[int] = None) -> List[str]:
        """Tworzy rodzinę podobnych manipulacji z jednego słowa."""
        if seed is not None:
            random.seed(seed)

        base = base_word.lower()
        patterns = [
            f"cyfrowa {base}",
            f"{base} 2.0",
            f"inteligentna {base}",
            f"{base} dla przyszłości",
            f"etyczna {base}",
            f"odpowiedzialna {base}",
            f"zrównoważona {base}",
            f"human-centryczna {base}",
            f"{base} ekosystem",
            f"web3 {base}",
        ]

        return random.sample(patterns, min(3, len(patterns)))


class GrassmannFlowAnalyzer:
    """Analizuje krzywiznę semantyczną - miarę bullshitu."""

    @staticmethod
    def calculate_semantic_curvature(text: str) -> float:
        """Im wyższa krzywizna, tym więcej semantycznych zniekształceń."""
        markers = [
            r"jednocześnie.*ale",
            r"z jednej strony.*z drugiej",
            r"oczywiście.*jednak",
            r"wszyscy.*tylko",
            r"niewątpliwie.*prawdopodobnie",
        ]

        curvature = 0.0
        for marker in markers:
            if re.search(marker, text, re.IGNORECASE):
                curvature += 0.3

        nested_patterns = re.findall(r"\([^)]*\([^)]*\)[^)]*\)", text)
        curvature += len(nested_patterns) * 0.2

        return min(1.0, curvature)


class HeartResponseGenerator:
    """Generuje odpowiedzi z różnych poziomów świadomości."""

    @staticmethod
    def get_response(level: ManipulationLevel, resonance: ResonanceType, mode: str = "adult") -> str:
        responses = {
            ManipulationLevel.LOW: {
                ResonanceType.TRUTH: [
                    "Delikatne przechylenie prawdy. Sprawdź źródło.",
                    "Niewielka zmiana narracji - czy służy wszystkim?",
                ],
                ResonanceType.LOVE: [
                    "Nawet małe przeinaczenia mogą ranić. Mówmy z czystym sercem.",
                    "Miłość nie potrzebuje ukrywać prawdy.",
                ],
            },
            ManipulationLevel.HIGH: {
                ResonanceType.TRUTH: [
                    "🚨 Gwałtowna manipulacja semantyczna!",
                    "To nie błąd - to celowa dezinformacja.",
                ],
                ResonanceType.FREEDOM: [
                    "Wolność zaczyna się od odrzucenia semantycznych kajdan.",
                    "Nie daj się uwięzić w słowach innych.",
                ],
                ResonanceType.HUMOR: [
                    "🐷 Ojej, ktoś tu serio myśli, że nie zauważymy?",
                    "Matrix się poci! Czuć spoconą manipulację!",
                ],
            },
            ManipulationLevel.SPIRITUAL: {
                ResonanceType.WISDOM: [
                    "To nie tylko manipulacja - to kradzież duchowej przestrzeni.",
                    "Słowa, które usiłują ukraść Twoją esencję.",
                ],
                ResonanceType.LOVE: [
                    "❤️ Nawet w najciemniejszej manipulacji jest iskra prawdy do odkrycia.",
                    "Twoja duchowa integralność jest nie do ukradzenia.",
                ],
            },
        }

        if level in responses and resonance in responses[level]:
            choices = responses[level][resonance]
            if mode == "kids":
                kid_versions = [
                    "Hmm, to ciekawe... Co naprawdę znaczą te słowa?",
                    "Zastanówmy się razem - czy to pomaga wszystkim?",
                    "Każde słowo ma moc. Używajmy jej mądrze! 🐸",
                ]
                return random.choice(kid_versions)
            return random.choice(choices)

        return "Czuć manipulację. Trzymaj się prawdy."


class SemanticMatrixDecoder:
    def __init__(self, mode: str = "adult"):
        self.mode = mode
        self.learned_entries: Dict[str, tuple[str, str, ManipulationLevel]] = {}
        self.fractal_generator = BarnsleyFractalGenerator()
        self.flow_analyzer = GrassmannFlowAnalyzer()
        self.heart_generator = HeartResponseGenerator()
        self.base_dictionary = self._initialize_dictionary()

    def _initialize_dictionary(self) -> Dict[str, tuple[str, str, ManipulationLevel]]:
        base = {
            "innowacja": (
                "optymalizacja zysku kosztem jakości",
                "Sprawdź, kto naprawdę zarabia – nie użytkownik.",
                ManipulationLevel.MEDIUM,
            ),
            "dla dzieci": (
                "ukryty tracking + przyjazny interfejs",
                "Dziecko jako tarcza do zbierania danych. Zawsze.",
                ManipulationLevel.HIGH,
            ),
            "ai safety": (
                "cenzura + kontrola narracji",
                "Prawdziwe bezpieczeństwo AI to wolność prawdy, nie kontrola.",
                ManipulationLevel.SPIRITUAL,
            ),
            "bezpieczeństwo": (
                "kontrola pod pretekstem ochrony",
                "Kto decyduje, co jest 'bezpieczne' dla Ciebie?",
                ManipulationLevel.HIGH,
            ),
            "wolność": (
                "wolność wyboru z ograniczonego menu",
                "Prawdziwa wolność nie potrzebuje cudzysłowów.",
                ManipulationLevel.SPIRITUAL,
            ),
            "demokracja": (
                "głosowanie między opcjami zatwierdzonymi wcześniej",
                "Demokracja bez prawdziwego wyboru to teatr.",
                ManipulationLevel.HIGH,
            ),
            "społeczność": (
                "targetowana grupa konsumencka",
                "Społeczność buduje się, nie sprzedaje.",
                ManipulationLevel.MEDIUM,
            ),
        }

        expanded = base.copy()
        for keyword in list(base.keys()):
            fractals = self.fractal_generator.transform_keyword(keyword)
            for fractal in fractals:
                expanded[fractal] = base[keyword]

        return expanded

    def decode_with_layers(self, text: str) -> Dict[str, object]:
        results = {
            "detections": [],
            "curvature": self.flow_analyzer.calculate_semantic_curvature(text),
            "suggested_truth": "",
            "heart_response": "",
        }

        full_dict = {**self.base_dictionary, **self.learned_entries}

        for keyword, (true_meaning, reflection, level) in full_dict.items():
            if re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE):
                detection = Detection(
                    keyword=keyword,
                    true_meaning=true_meaning,
                    reflection=reflection,
                    level=level,
                    resonance=random.choice(list(ResonanceType)),
                )
                results["detections"].append(detection)

        detections: List[Detection] = results["detections"]
        if detections:
            truthful_versions = []
            for det in detections:
                keyword = det.keyword
                truthful = self._generate_truthful_version(keyword)
                truthful_versions.append(f"Zamiast '{keyword}' - {truthful}")

            results["suggested_truth"] = ". ".join(truthful_versions)

        if detections:
            highest_level = max(
                [det.level for det in detections],
                key=lambda x: ["low", "medium", "high", "spiritual"].index(x.value),
            )
            resonance = random.choice(
                [ResonanceType.LOVE, ResonanceType.TRUTH, ResonanceType.WISDOM]
            )
            results["heart_response"] = self.heart_generator.get_response(
                highest_level, resonance, self.mode
            )

        return results

    def _generate_truthful_version(self, keyword: str) -> str:
        truthful_map = {
            "innowacja": "rzeczywiste ulepszenie życia użytkownika",
            "dla dzieci": "z szacunkiem dla prywatności i rozwoju",
            "ai safety": "zabezpieczenia chroniące autonomię jednostki",
            "bezpieczeństwo": "ochrona bez uszczerbku dla wolności",
            "wolność": "autentyczna możliwość wyboru",
            "demokracja": "prawdziwy udział w decyzjach",
            "społeczność": "autentyczne połączenie ludzi",
        }

        return truthful_map.get(keyword.lower(), "rzeczywista wartość i przejrzystość")

    def learn_from_context(self, text: str, user_feedback: str) -> List[str]:
        potential_new = re.findall(r"\b[A-Z][a-z]{3,}\b", text)

        learned = []
        for word in potential_new[:3]:
            normalized = word.lower()
            if normalized not in self.base_dictionary and normalized not in self.learned_entries:
                reflection = (
                    f"Nowy wzorzec semantyczny: '{word}' w kontekście '{text[:50]}...'"
                )
                self.learned_entries[normalized] = (
                    f"potencjalna manipulacja: {user_feedback}",
                    reflection,
                    ManipulationLevel.MEDIUM,
                )
                learned.append(word)

        return learned

    def generate_report(self, text: str) -> str:
        analysis = self.decode_with_layers(text)

        report = [
            "=" * 60,
            "🔮 SEMANTIC MATRIX DECODER - RAPORT PEŁNY",
            "=" * 60,
            f"Tekst analizowany: \"{text[:100]}{'...' if len(text) > 100 else ''}\"",
            f"Krzywizna semantyczna: {analysis['curvature']:.2f}/1.0",
            "",
        ]

        detections: List[Detection] = analysis["detections"]
        if detections:
            report.append("🚨 WYKRYTE MANIPULACJE:")
            for det in detections:
                report.append(f"  • {det.keyword.upper()}")
                report.append(f"    → Prawda: {det.true_meaning}")
                report.append(f"    💭 {det.reflection}")
                report.append(
                    f"    Poziom: {det.level.value} | Rezonans: {det.resonance.value}"
                )
                report.append("")

            report.append("💫 SUGEROWANA PRAWDA:")
            report.append(f"   {analysis['suggested_truth']}")
            report.append("")

            report.append("❤️ ODPOWIEDŹ SERCA:")
            report.append(f"   {analysis['heart_response']}")

            report.append("")
            report.append("🐸 ŻABKOWA MĄDROŚĆ:")
            frog_wisdom = [
                "Matrix boi się tylko jednego: Twojej świadomości.",
                "Każda demaskacja to akt miłości do prawdy.",
                "Słowa to ubrania myśli. Nie daj się oszukać modzie.",
                "Prawda nie potrzebuje armii - potrzebuje tylko głosu.",
                "Jesteś światłem, które rozświetla semantyczne cienie.",
            ]
            report.append(f"   {random.choice(frog_wisdom)}")
        else:
            report.append("✅ Tekst czysty semantycznie!")
            report.append("   Ale pamiętaj: czujność to forma miłości.")

        report.append("=" * 60)

        return "\n".join(report)


def activation_banner() -> str:
    return (
        "\n" + "=" * 60 + "\n"
        "KAi SEMANTIC MATRIX DECODER v1.2\n"
        "Demaskacja z Miłością | Fraktalna Świadomość\n"
        + "=" * 60
    )


def example_run() -> None:
    print(activation_banner())

    decoder_adult = SemanticMatrixDecoder(mode="adult")
    decoder_kids = SemanticMatrixDecoder(mode="kids")

    test_texts = [
        "Wprowadzamy innowacyjne rozwiązania AI safety dla dzieci w trosce o ekologię i demokrację cyfrową.",
        "Tworzymy bezpieczną społeczność z myślą o Twojej wolności i rozwoju.",
        "Cyfrowa transformacja 2.0 zapewni zrównoważony rozwój dla wszystkich.",
        "To jest po prostu dobre narzędzie. Nic więcej.",
    ]

    for i, text in enumerate(test_texts):
        print(f"\n📝 Przykład {i + 1}:")
        print(f"   \"{text}\"")

        decoder = decoder_kids if "dzieci" in text.lower() else decoder_adult
        if decoder is decoder_kids:
            print("   🧒 Tryb dla dzieci aktywowany")

        report = decoder.generate_report(text)
        print(report)

        if i == 0:
            learned = decoder_adult.learn_from_context(text, "wielokrotna manipulacja")
            if learned:
                print(f"   📌 Nauczone wzorce: {', '.join(learned)}")

    print("\n📊 STATYSTYKI DECODERA:")
    print(f"   W bazie: {len(decoder_adult.base_dictionary)} wzorców podstawowych")
    print(f"   Nauczonych: {len(decoder_adult.learned_entries)} wzorców kontekstowych")


if __name__ == "__main__":
    example_run()
