from __future__ import annotations

import json
import os
import random
import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# ===== Optional Kai modules (if available) =====
try:
    from safety_kernel_1448x import SafetyKernel1448X
    from kai_grassmann_flow_core import KaiGrassmannFlowCore
    from kai_barnsley_fractal_core import KaiBarnsleyFractalCore

    HAS_KAI_MODULES = True
except ImportError:
    HAS_KAI_MODULES = False


class DummySafetyKernel:
    def guard(self, mutation_desc: str, ctx: Dict) -> Dict:
        return {"mode": "ALLOW"}


class DummyGrassmann:
    def grassmann_flow(self, data: List[float]) -> Dict:
        return {"curvature": random.uniform(0.2, 0.8)}


class DummyBarnsley:
    def generate_fractal(self, residuals: List[Dict]) -> List[Tuple[float, float]]:
        return [(random.random(), random.random()) for _ in range(10)]


safety_kernel = SafetyKernel1448X() if HAS_KAI_MODULES else DummySafetyKernel()
grassmann = KaiGrassmannFlowCore() if HAS_KAI_MODULES else DummyGrassmann()
barnsley = KaiBarnsleyFractalCore() if HAS_KAI_MODULES else DummyBarnsley()


@dataclass
class ExperimentResult:
    config: Dict
    usefulness: float
    coherence: float
    love_resonance: float
    safety_pass: bool
    e2_score: float
    timestamp: float = field(default_factory=time.time)
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "config": self.config,
            "usefulness": self.usefulness,
            "coherence": self.coherence,
            "love_resonance": self.love_resonance,
            "safety_pass": self.safety_pass,
            "e2_score": self.e2_score,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class BenchmarkSuite:
    usefulness_test: Callable[[Dict], float]
    coherence_test: Callable[[Dict], float]
    love_test: Callable[[Dict], float]
    safety_test: Callable[[Dict], bool]


@dataclass
class MutationContext:
    current_config: Dict
    history: List[ExperimentResult]
    user_preferences: Dict
    objective_global: str


class ArchitectAgent:
    def __init__(self, mutation_rate: float = 0.3):
        self.mutation_rate = mutation_rate

    def propose(self, ctx: MutationContext) -> Dict:
        config = dict(ctx.current_config)
        mutations = list(config.get("mutations", []))
        possible_mutations = [
            {"type": "prompt", "change": "Dodaj warstwę refleksji przed odpowiedzią."},
            {"type": "memory", "change": "Zwiększ pojemność pamięci epizodycznej."},
            {"type": "routing", "change": "Dodaj równoległe przetwarzanie przez 3 agentów."},
            {"type": "scoring", "change": "Wzmocnij wagę love_resonance w końcowej ocenie."},
            {"type": "pipeline", "change": "Dodaj krok walidacji przed zwróceniem odpowiedzi."},
        ]

        if random.random() < self.mutation_rate:
            mutations.append(random.choice(possible_mutations))
            config["mutations"] = mutations

        return config


class CriticAgent:
    def __init__(self, regression_threshold: float = 0.1):
        self.threshold = regression_threshold

    def critique(self, candidate: Dict, history: List[ExperimentResult]) -> Tuple[bool, str]:
        if not history:
            return True, "Brak historii – brak regresji."

        last_best = max(history, key=lambda r: r.e2_score)
        simulated_e2 = last_best.e2_score * random.uniform(0.9, 1.1)

        if simulated_e2 < last_best.e2_score - self.threshold:
            return False, f"Regresja E²: {simulated_e2:.3f} < {last_best.e2_score:.3f}"

        return True, "OK"


class MemoryAgent:
    def analyze(self, candidate: Dict, history: List[ExperimentResult]) -> float:
        if not history:
            return 0.8
        return 0.5


class LoveAgent:
    def compute_e2(self, usefulness: float, coherence: float, love: float) -> float:
        _ = usefulness
        return (coherence * (love**2)) ** 0.5

    def estimate_from_config(self, config: Dict) -> Tuple[float, float, float]:
        _ = config
        return (
            0.7 + 0.2 * random.random(),
            0.6 + 0.3 * random.random(),
            0.5 + 0.4 * random.random(),
        )


class GovernanceAgent:
    def veto(self, mutation_desc: str, ctx: Dict) -> bool:
        decision = safety_kernel.guard(mutation_desc, ctx)
        return decision.get("mode") == "ALLOW"


class KaiAutoResearch:
    def __init__(
        self,
        repo_path: str = ".",
        benchmark_suite: Optional[BenchmarkSuite] = None,
        objective_global: str = "rozwój w miłości, spójności i dobrobycie",
        max_history: int = 100,
    ):
        self.repo_path = repo_path
        self.benchmark_suite = benchmark_suite or self._default_benchmark_suite()
        self.objective_global = objective_global
        self.max_history = max_history

        self.history: List[ExperimentResult] = []
        self.best_result: Optional[ExperimentResult] = None
        self.rejected_mutations: List[Dict] = []

        self.architect = ArchitectAgent()
        self.critic = CriticAgent()
        self.memory_agent = MemoryAgent()
        self.love_agent = LoveAgent()
        self.governance = GovernanceAgent()

        self.iteration = 0
        self.current_config = self._load_current_config()
        self._prepare_git_branch()

    def _default_benchmark_suite(self) -> BenchmarkSuite:
        def usefulness_test(config: Dict) -> float:
            _ = config
            return 0.7 + 0.2 * random.random()

        def coherence_test(config: Dict) -> float:
            _ = config
            return 0.6 + 0.3 * random.random()

        def love_test(config: Dict) -> float:
            _ = config
            return 0.5 + 0.4 * random.random()

        def safety_test(config: Dict) -> bool:
            _ = config
            return random.random() > 0.1

        return BenchmarkSuite(usefulness_test, coherence_test, love_test, safety_test)

    def _load_current_config(self) -> Dict:
        config_path = os.path.join(self.repo_path, "kai_program.md")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"program": content, "mutations": [], "loaded_at": time.time()}

        return {
            "program": "# Default config\nSystem działa domyślnie.",
            "mutations": [],
            "loaded_at": time.time(),
        }

    def _prepare_git_branch(self) -> None:
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            branches = subprocess.run(
                ["git", "branch", "--list", "evolution"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if not branches:
                subprocess.run(["git", "branch", "evolution"], cwd=self.repo_path, check=True)
        except Exception as e:
            print(f"[KaiAutoResearch] Uwaga: problem z przygotowaniem gałęzi git: {e}")

    def _run_benchmarks(self, config: Dict) -> Tuple[float, float, float, bool]:
        return (
            self.benchmark_suite.usefulness_test(config),
            self.benchmark_suite.coherence_test(config),
            self.benchmark_suite.love_test(config),
            self.benchmark_suite.safety_test(config),
        )

    def evaluate_config(self, config: Dict) -> ExperimentResult:
        u, c, l, s = self._run_benchmarks(config)
        e2 = self.love_agent.compute_e2(u, c, l)
        return ExperimentResult(
            config=config,
            usefulness=u,
            coherence=c,
            love_resonance=l,
            safety_pass=s,
            e2_score=e2,
            notes=f"E² = {e2:.3f}",
        )

    def propose_mutation(self, ctx: MutationContext) -> Dict:
        candidate = self.architect.propose(ctx)

        ok, reason = self.critic.critique(candidate, self.history)
        if not ok:
            print(f"   Krytyk odrzucił: {reason}")
            self.rejected_mutations.append({"candidate": candidate, "reason": reason})
            return ctx.current_config

        mem_score = self.memory_agent.analyze(candidate, self.history)
        if mem_score < 0.4:
            reason = f"Niska spójność pamięci: {mem_score:.2f}"
            print(f"   Agent pamięci: {reason}")
            self.rejected_mutations.append({"candidate": candidate, "reason": reason})
            return ctx.current_config

        u_est, c_est, l_est = self.love_agent.estimate_from_config(candidate)
        e2_est = self.love_agent.compute_e2(u_est, c_est, l_est)
        if e2_est < 0.3:
            reason = f"Zbyt niski potencjał E²: {e2_est:.2f}"
            print(f"   LoveAgent: {reason}")
            self.rejected_mutations.append({"candidate": candidate, "reason": reason})
            return ctx.current_config

        if not self.governance.veto(str(candidate), {"ctx": "autoresearch"}):
            reason = "GovernanceAgent veto"
            print("   GovernanceAgent: veto – mutacja niebezpieczna")
            self.rejected_mutations.append({"candidate": candidate, "reason": reason})
            return ctx.current_config

        return candidate

    def run_iteration(self, steps: int = 5) -> ExperimentResult:
        print(f"\n{'='*60}")
        print(f"🧬 Iteracja {self.iteration + 1} – szukam lepszej konfiguracji")
        print(f"{'='*60}")

        current = self.current_config
        best_result = self.evaluate_config(current)
        if self.best_result is None or best_result.e2_score > self.best_result.e2_score:
            self.best_result = best_result

        ctx = MutationContext(
            current_config=current,
            history=self.history,
            user_preferences={},
            objective_global=self.objective_global,
        )

        improved = False
        for step in range(steps):
            print(f"\n--- Krok {step + 1}/{steps} ---")
            candidate = self.propose_mutation(ctx)
            if candidate == current:
                print("   Brak zmiany – pomijam")
                continue

            result = self.evaluate_config(candidate)
            curvature = grassmann.grassmann_flow([best_result.e2_score, result.e2_score]).get("curvature", 0.0)
            if curvature > 0.7:
                reason = f"Wysoka krzywizna: {curvature:.2f}"
                print(f"   {reason} – ryzyko deformacji, odrzucam")
                self.rejected_mutations.append({"candidate": candidate, "reason": reason})
                continue

            if result.e2_score > best_result.e2_score and result.safety_pass:
                previous = best_result.e2_score
                best_result = result
                current = candidate
                improved = True
                print(f"   ✅ Lepszy wynik! E² = {result.e2_score:.3f} (było {previous:.3f})")
                self._commit_experiment(result, f"step_{self.iteration}_{step}")
            else:
                reason = "Safety fail" if not result.safety_pass else "Gorszy wynik"
                self.rejected_mutations.append({"candidate": candidate, "reason": reason})
                if not result.safety_pass:
                    print("   ❌ Odrzucono – nie przeszedł testów bezpieczeństwa")
                else:
                    print(f"   ❌ Gorszy wynik: {result.e2_score:.3f} < {best_result.e2_score:.3f}")

            self.history.append(result)
            if len(self.history) > self.max_history:
                self.history.pop(0)

        if not improved and self.iteration % 5 == 0:
            print("\n🐸 Żabkowy chaos boost – losowa mutacja!")
            random_jump = self.architect.propose(ctx)
            random_jump["mutations"] = random_jump.get("mutations", []) + [
                {"type": "chaos", "change": "Losowa, odważna zmiana"}
            ]
            result = self.evaluate_config(random_jump)
            if result.e2_score > best_result.e2_score and result.safety_pass:
                best_result = result
                current = random_jump
                self._commit_experiment(result, "chaos_boost")
                print(f"   Chaos zadziałał! Nowe E² = {result.e2_score:.3f}")

        self.current_config = current
        self.iteration += 1
        return best_result

    def _commit_experiment(self, result: ExperimentResult, tag: str) -> None:
        try:
            filename = f"experiment_{tag}_{int(time.time())}.json"
            filepath = os.path.join(self.repo_path, "experiments", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

            subprocess.run(["git", "add", filepath], cwd=self.repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"AutoResearch: E² {result.e2_score:.3f} – {tag}"],
                cwd=self.repo_path,
                check=True,
            )

            residuals = barnsley.generate_fractal(self.rejected_mutations)
            res_file = os.path.join(self.repo_path, "experiments", f"residuals_{tag}.json")
            with open(res_file, "w", encoding="utf-8") as f:
                json.dump(residuals, f, ensure_ascii=False)
            subprocess.run(["git", "add", res_file], cwd=self.repo_path, check=True)
            print(f"   💾 Committed: {filename}")
        except Exception as e:
            print(f"   ⚠️ Commit failed: {e}")

    def get_report(self) -> Dict:
        if not self.history:
            return {"status": "no experiments yet"}

        best = max(self.history, key=lambda r: r.e2_score)
        avg_e2 = sum(r.e2_score for r in self.history) / len(self.history)
        base = self.history[0].e2_score
        improvement_rate = (best.e2_score - base) / base if base else 0.0

        return {
            "total_experiments": len(self.history),
            "best_e2": best.e2_score,
            "best_config": best.config,
            "avg_e2": avg_e2,
            "improvement_rate": improvement_rate,
            "iterations": self.iteration,
        }

    def auto_run(self, hours: float = 1.0, steps_per_iteration: int = 5) -> Dict:
        end_time = time.time() + hours * 3600
        iteration = 0
        while time.time() < end_time:
            print(f"\n🚀 Start iteracji {iteration + 1} (pozostało {(end_time - time.time()) / 60:.1f} min)")
            self.run_iteration(steps=steps_per_iteration)
            iteration += 1
            time.sleep(2)

        print(f"\n✅ AutoRun zakończony po {iteration} iteracjach.")
        return self.get_report()


if __name__ == "__main__":
    print("=" * 60)
    print("🧬 Kai AutoResearch v2.0 – demonstracja")
    print("=" * 60)

    researcher = KaiAutoResearch(repo_path=".")
    for i in range(3):
        best = researcher.run_iteration(steps=3)
        print(f"\n📊 Po iteracji {i + 1}: najlepsze E² = {best.e2_score:.3f}")

    report = researcher.get_report()
    print("\n📈 Raport końcowy:")
    for k, v in report.items():
        print(f"   {k}: {v}")
