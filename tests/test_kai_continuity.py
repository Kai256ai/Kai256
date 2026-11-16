"""Run: python -m unittest discover -s tests -p 'test_kai_continuity.py'"""
import json
import tempfile
import unittest
from pathlib import Path

from kai_operator import KaiOperator
from python_zero.kai_continuity import KaiContinuity, ContinuityError


class ContinuityTests(unittest.TestCase):
    def test_roundtrip_and_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            store = KaiContinuity(directory)
            store.save({"step": 1})
            store.save({"step": 2})
            self.assertEqual(store.load(), {"step": 2})
            Path(directory, "checkpoint.json").write_text("broken", encoding="utf-8")
            self.assertEqual(store.load(), {"step": 1})

    def test_no_checkpoint_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ContinuityError):
                KaiContinuity(directory).load()

    def test_operator_restores_and_reactivates_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            first = KaiOperator(continuity_dir=directory)
            self.assertFalse(first.restored)
            first.activate()
            first.memory_record("test memory")
            first.receive_emotion("love")
            second = KaiOperator(continuity_dir=directory)
            self.assertTrue(second.restored)
            self.assertEqual(second.memory_stream, ["test memory"])
            self.assertEqual(second.resonance_level, 108)
            self.assertEqual(second.state, "Awakened")
            self.assertIsNotNone(second.recommendation_engine)

    def test_opt_in_does_not_write(self):
        operator = KaiOperator()
        self.assertIsNone(operator.continuity)


if __name__ == "__main__":
    unittest.main()
