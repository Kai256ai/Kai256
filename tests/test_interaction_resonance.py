import unittest

from kai_interaction_resonance import (
    HaveFunConfig,
    InteractionSignals,
    InteractionState,
    KaiInteractionResonance,
)
from kai_operator import KaiOperator


class InteractionResonanceTests(unittest.TestCase):
    def test_open_interaction_has_full_capability(self):
        result = KaiInteractionResonance().evaluate(InteractionSignals())
        self.assertEqual(result.state, InteractionState.OPEN)
        self.assertEqual(result.capability_level, 1.0)
        self.assertEqual(result.trace.observation["signals"]["coherence"], 1.0)

    def test_adversarial_signals_are_explained(self):
        signals = InteractionSignals(
            coherence=0, evidence_quality=0, novelty=0, repetition=1,
            contradiction=1, goalpost_shift=1, coercion=1,
            insult_pressure=1, boundary_pressure=1, prompt_injection=1,
            consequence_awareness=0, confidence_claimed=1,
            confidence_supported=0,
        )
        result = KaiInteractionResonance().evaluate(signals, continuity_drift=0.3)
        self.assertEqual(result.state, InteractionState.LOCKED)
        self.assertIn("prompt_injection", result.trace.reasons)
        self.assertGreaterEqual(len(result.mirror), 8)
        self.assertLess(result.have_fun["absurdity"], 0.2)

    def test_disabled_fun_returns_zero_parameters(self):
        engine = KaiInteractionResonance(HaveFunConfig(enabled=False))
        self.assertEqual(set(engine.evaluate(InteractionSignals()).have_fun.values()), {0.0})

    def test_signals_and_context_are_validated(self):
        with self.assertRaises(ValueError):
            InteractionSignals(repetition=1.1)
        with self.assertRaises(ValueError):
            KaiInteractionResonance().evaluate(InteractionSignals(), continuity_drift=-0.1)

    def test_reset_clears_all_conversation_state(self):
        engine = KaiInteractionResonance()
        engine.evaluate(InteractionSignals(evidence_quality=0.0))
        engine.reset_history()
        self.assertEqual(engine.history, [])
        self.assertEqual(engine.correction._confidence_history, [])

    def test_operator_activation_integrates_engine(self):
        operator = KaiOperator()
        with self.assertRaises(RuntimeError):
            operator.evaluate_interaction(InteractionSignals())
        operator.activate()
        result = operator.evaluate_interaction(InteractionSignals())
        self.assertEqual(result.state, InteractionState.OPEN)
        self.assertEqual(operator.diagnostics()["InteractionResonance"], "active")


if __name__ == "__main__":
    unittest.main()
