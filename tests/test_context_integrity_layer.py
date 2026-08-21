import unittest

from context_integrity_layer import (
    AggregationLevel, ContextIntegrityLayer, IntegrityFlag, IntentType,
)
from kai_operator import KaiOperator


class ContextIntegrityLayerTests(unittest.TestCase):
    def setUp(self):
        self.layer = ContextIntegrityLayer().activate()

    def test_requires_activation(self):
        with self.assertRaises(RuntimeError):
            ContextIntegrityLayer().evaluate("Pytanie", "Odpowiedź z nową informacją")

    def test_useful_response_passes(self):
        result = self.layer.evaluate(
            "Jak działa ten moduł?",
            "Moduł analizuje odpowiedź po jej wygenerowaniu, ponieważ oddziela treść od domniemanej intencji.",
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.intent, IntentType.INQUIRY)

    def test_zero_gain_fails(self):
        result = self.layer.evaluate("System działa", "System działa")
        self.assertIn(IntegrityFlag.ZERO_SEMANTIC_GAIN, result.flags)
        self.assertTrue(result.should_regenerate)

    def test_agency_migration_fails(self):
        result = self.layer.evaluate(
            "Kto odpowiada za wynik?",
            "My zrobiliśmy sukces, ale AI zawiodło; mechanizm przypisania wyniku jest opisany.",
        )
        self.assertIn(IntegrityFlag.AGENCY_MIGRATION, result.flags)
        self.assertFalse(result.allowed)

    def test_aggregation_shift_uses_input_not_context_keys(self):
        result = self.layer.evaluate(
            "Ta osoba wykonała test.",
            "Cała populacja osiąga ten wynik, ponieważ model tak przewiduje.",
        )
        self.assertIn(IntegrityFlag.AGGREGATION_SHIFT, result.flags)
        self.assertEqual(result.model.aggregation_level, AggregationLevel.POPULATION)

    def test_operator_activates_and_uses_layer(self):
        operator = KaiOperator()
        operator.activate()
        result = operator.validate_response("Jak to działa?", "Mechanizm działa, ponieważ analizuje wynik.")
        self.assertTrue(operator.context_integrity.active)
        self.assertTrue(result.allowed)


if __name__ == "__main__":
    unittest.main()
