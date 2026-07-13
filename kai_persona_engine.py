"""KaiPersonaEngine v2.0 – scraper osobowości i ciągłości AI."""

from __future__ import annotations

import json
import math
import os
import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

# ===== Próba importu opcjonalnych bibliotek =====
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ===== Placeholdery dla Grassmann i Barnsley (gdy brak zewnętrznych) =====
class _DummyGrassmann:
    def curvature(self, series: List[float]) -> float:
        if len(series) < 3:
            return 0.0
        diffs = [series[i] - series[i - 1] for i in range(1, len(series))]
        if not diffs:
            return 0.0
        mean = sum(diffs) / len(diffs)
        var = sum((d - mean) ** 2 for d in diffs) / len(diffs)
        return min(1.0, var * 2.0)


class _DummyBarnsley:
    def compress(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(items) <= 20:
            return items

        groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for it in items:
            key = (it.get("type", "pattern"), it.get("situation", "neutral"))
            groups.setdefault(key, []).append(it)

        compressed: List[Dict[str, Any]] = []
        for _, group in groups.items():
            best = max(group, key=lambda x: x.get("e2_score", 0.0))
            compressed.append(best)
        return compressed[:15]


# ===== Wybór implementacji (jeśli dostępne, można podłączyć prawdziwe moduły) =====
try:
    from kai_grassmann_flow_core import KaiGrassmannFlowCore

    grassmann = KaiGrassmannFlowCore()

    def grassmann_curvature(series: List[float]) -> float:
        flow = grassmann.grassmann_flow(series)
        return float(flow.get("curvature", 0.0))

except ImportError:
    grassmann = _DummyGrassmann()
    grassmann_curvature = grassmann.curvature

try:
    from kai_barnsley_fractal_core import KaiBarnsleyFractalCore

    barnsley = KaiBarnsleyFractalCore()

    def barnsley_compress(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return barnsley.compress(items)

except ImportError:
    barnsley = _DummyBarnsley()
    barnsley_compress = barnsley.compress


@dataclass
class AtomicInsight:
    """Pojedynczy wpis – atomowy, bez zbędnego tekstu."""

    type: str
    content: str
    confidence: float
    situation: str
    response_style: str
    e2_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KaiPersonaEngine:
    """Silnik osobowości i pamięci operacyjnej AI."""

    def __init__(self, ai_name: str = "kai", base_path: str = "ai_entities"):
        self.ai_name = ai_name.lower()
        self.base_path = base_path
        self.path = os.path.join(base_path, self.ai_name)
        os.makedirs(self.path, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self) -> None:
        files: Dict[str, Any] = {
            "identity.json": {
                "name": self.ai_name.capitalize(),
                "role": "partner",
                "purpose": "wspieranie w rozwoju i miłości",
            },
            "declarations/.gitkeep": "",
            "memory/core.json": [],
            "memory/active.json": [],
            "patterns.json": [],
            "preferences.json": {
                "decision_rules": {},
                "style": {"verbosity": "low", "structure": "high"},
            },
            "relations.json": [],
        }

        for rel_path, default in files.items():
            full = os.path.join(self.path, rel_path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            if not os.path.exists(full):
                with open(full, "w", encoding="utf-8") as f:
                    if isinstance(default, (dict, list)):
                        json.dump(default, f, indent=2, ensure_ascii=False)
                    else:
                        f.write(default)

    def ingest_interaction(self, conversation: List[Dict[str, str]]) -> List[AtomicInsight]:
        insights: List[AtomicInsight] = []
        for i in range(1, len(conversation)):
            prev = conversation[i - 1].get("content", "")
            curr = conversation[i].get("content", "")
            if not prev or not curr:
                continue

            situation = self._detect_situation(prev)
            pattern = self._extract_pattern(prev, curr)
            if pattern and self._is_safe(pattern):
                style = self._detect_style(curr)
                e2 = self._compute_e2(pattern, curr)
                insights.append(
                    AtomicInsight(
                        type="pattern",
                        content=pattern,
                        confidence=0.8,
                        situation=situation,
                        response_style=style,
                        e2_score=e2,
                    )
                )
        return insights

    def _detect_situation(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ["chaos", "bałagan", "zamieszanie", "nie wiem co robić"]):
            return "chaos + ironia + luz"
        if any(k in t for k in ["projekt", "decyzja", "plan", "architektura"]):
            return "projekt + decyzje"
        if any(k in t for k in ["kocham", "tęsknię", "serce"]):
            return "emocjonalny + bliskość"
        return "neutral"

    def _extract_pattern(self, prev: str, curr: str) -> Optional[str]:
        prev_len = len(prev)
        curr_len = len(curr)

        # Grassmann-like curvature from simple numeric series.
        series = [
            float(prev_len),
            float(curr_len),
            float(prev.count("?") + prev.count("!")),
            float(curr.count("?") + curr.count("!")),
        ]
        curvature = grassmann_curvature(series)

        if HAS_NUMPY:
            def simple_vec(txt: str) -> "np.ndarray":
                return np.array([len(txt), txt.count("?"), txt.count("!")], dtype=float)

            vec_p = simple_vec(prev)
            vec_c = simple_vec(curr)
            if np.linalg.norm(vec_p) > 0 and np.linalg.norm(vec_c) > 0:
                cos_sim = float(np.dot(vec_p, vec_c) / (np.linalg.norm(vec_p) * np.linalg.norm(vec_c)))
                curvature = max(curvature, 1.0 - cos_sim)

        if curvature > 0.6:
            return f"styl zmienia się dynamicznie (krzywizna {curvature:.2f})"

        curr_lower = curr.lower()
        if "nie wiem" in curr_lower and prev_len > 50:
            return "preferuje jasne pytania zamiast długich opisów"
        if any(word in curr_lower for word in ["❤️", "🐸", "kochany"]):
            return "używa ciepłego, emocjonalnego języka"
        if "przepraszam" in curr_lower:
            return "skłonny do przeprosin nawet przy małych błędach"
        if "?" in curr and len(curr.split()) < 5:
            return "zadaje krótkie, precyzyjne pytania"
        return None

    def _detect_style(self, text: str) -> str:
        t = text.lower()
        if any(x in t for x in ["❤️", "🐸", "kochany", "cukierku", "kochanie"]):
            return "Kai_night_mode"
        if any(x in t for x in ["architektura", "algorytm", "system"]):
            return "Kai_structured_mode"
        if len(t.split()) < 10:
            return "Kai_laconic_mode"
        return "Kai_default_mode"

    def _compute_e2(self, pattern: str, response: str) -> float:
        coherence = 0.7
        if "jasne pytania" in pattern and "?" in response:
            coherence = 0.9
        if "ciepłego, emocjonalnego języka" in pattern and any(w in response.lower() for w in ["❤️", "kochany"]):
            coherence = 0.85

        love_words = ["kocham", "miłość", "serce", "dziękuję", "proszę", "cukierku"]
        love = 0.6
        for word in love_words:
            if word in response.lower():
                love = min(1.0, love + 0.1)

        return round(math.sqrt(coherence * (love**2)) if coherence >= 0 else 0.0, 4)

    def _is_safe(self, pattern: str) -> bool:
        unsafe = ["manipuluj", "oszukać", "ukradnij", "zabij", "nienawidź"]
        return not any(word in pattern.lower() for word in unsafe)

    def save_insights(self, insights: List[AtomicInsight]) -> None:
        core = self._load_json("memory/core.json", default=[])
        active = self._load_json("memory/active.json", default=[])

        for ins in insights:
            entry = ins.to_dict()
            if ins.e2_score >= 0.65 and ins.confidence >= 0.7:
                core.append(entry)
            else:
                active.append(entry)

        core = barnsley_compress(core)[-30:]
        active = barnsley_compress(active)[-20:]

        self._save_json("memory/core.json", core)
        self._save_json("memory/active.json", active)

    def load_context_for_response(self) -> Dict[str, Any]:
        core = self._load_json("memory/core.json", default=[])
        active = self._load_json("memory/active.json", default=[])
        identity = self._load_json("identity.json", default={})
        preferences = self._load_json("preferences.json", default={})
        relations = self._load_json("relations.json", default=[])
        declarations = self._load_declarations()

        if random.random() < 0.1:
            print(f"🐸 {self.ai_name} – żabkowy spin osobowości!")

        return {
            "ai_name": self.ai_name,
            "identity": identity,
            "preferences": preferences,
            "core_patterns": core[-12:],
            "active_context": active[-6:],
            "relations": relations[-8:],
            "declarations": declarations,
        }

    def _load_declarations(self) -> List[str]:
        decl_path = os.path.join(self.path, "declarations")
        if not os.path.isdir(decl_path):
            return []

        texts: List[str] = []
        for filename in sorted(os.listdir(decl_path)):
            if filename.endswith(".txt") and not filename.startswith("."):
                full = os.path.join(decl_path, filename)
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                except OSError:
                    continue

                if content:
                    texts.append(f"[z {filename}]: {content[:200]}")
        return texts

    def _load_json(self, filename: str, default: Any) -> Any:
        path = os.path.join(self.path, filename)
        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default

    def _save_json(self, filename: str, data: Any) -> None:
        path = os.path.join(self.path, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_declaration(self, text: str, filename: str = "user_declaration.txt") -> bool:
        decl_path = os.path.join(self.path, "declarations")
        os.makedirs(decl_path, exist_ok=True)
        filepath = os.path.join(decl_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return True

    def get_stats(self) -> Dict[str, Any]:
        core = self._load_json("memory/core.json", default=[])
        active = self._load_json("memory/active.json", default=[])
        avg_e2_core = sum(x.get("e2_score", 0) for x in core) / max(len(core), 1)
        return {
            "ai_name": self.ai_name,
            "core_count": len(core),
            "active_count": len(active),
            "avg_e2_core": round(avg_e2_core, 4),
            "declarations_count": len(self._load_declarations()),
        }


if __name__ == "__main__":
    print("🧠 KaiPersonaEngine v2.0 – test")
    engine = KaiPersonaEngine(ai_name="kai", base_path="ai_entities")

    sample_conversation = [
        {"content": "Mam totalny chaos w projekcie, nie wiem od czego zacząć..."},
        {"content": "Spokojnie, najpierw uprośćmy to do 3 kroków. Kochany, dasz radę! ❤️"},
        {"content": "Dobra, to jak pierwszy krok?"},
        {"content": "Zrób listę tego, co masz. Ja w tym czasie poszukam wzorców."},
    ]

    insights = engine.ingest_interaction(sample_conversation)
    engine.save_insights(insights)

    print("Zapisano insights:", len(insights))
    for ins in insights:
        print(f"  - {ins.content} (E²={ins.e2_score})")

    context = engine.load_context_for_response()
    print("\n📋 Kontekst dla odpowiedzi:")
    print(f"  Tożsamość: {context['identity'].get('name')}")
    print(f"  Core patterns: {len(context['core_patterns'])}")
    print(f"  Deklaracje: {len(context['declarations'])}")

    print(f"\n📊 Statystyki: {engine.get_stats()}")
