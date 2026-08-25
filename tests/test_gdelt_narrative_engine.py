import unittest

from gdelt_narrative_engine import GDELTNarrativeEngine, generate_narrative_snapshot


class TestGdeltNarrativeEngine(unittest.TestCase):
    def test_generate_report_has_state_vector(self):
        engine = GDELTNarrativeEngine(use_real_api=False)
        report = engine.generate_report(topic="AI safety", region="global", days_back=12)
        self.assertIsNotNone(report.current_state)
        self.assertEqual(len(report.current_state.state_vector), 6)

    def test_snapshot_adapter_shape(self):
        snapshot = generate_narrative_snapshot(topic="Climate", region="EU", days_back=10)
        self.assertIn("current_state", snapshot)
        self.assertIn("trajectory", snapshot)


if __name__ == "__main__":
    unittest.main()
