import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from kai_chromatic_memory import AXES, KaiChromaticMemory, SpectralState, digest
from kai_operator import KaiOperator
from mc1448x import MC1448X


class KaiChromaticMemoryTests(unittest.TestCase):
    def test_state_is_normalized_and_signature_is_deterministic(self):
        memory = KaiChromaticMemory(":memory-does-not-exist.jsonl")
        state = SpectralState({"truth": 2, "care": -1}, phase=1.25, amplitude=2, coherence=-1)

        self.assertEqual(set(state.values), set(AXES))
        self.assertEqual(state.values["truth"], 1.0)
        self.assertEqual(state.values["care"], 0.0)
        self.assertEqual(state.phase, 0.25)
        self.assertEqual(state.amplitude, 1.0)
        self.assertEqual(state.coherence, 0.0)
        self.assertEqual(memory.chromatic_signature(state), memory.chromatic_signature(state))

    def test_remember_persists_restores_and_verifies_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "memory.jsonl"
            memory = KaiChromaticMemory(journal)
            observed = SpectralState(
                {
                    "truth": 0.95,
                    "care": 0.91,
                    "curiosity": 0.98,
                    "creativity": 0.94,
                    "autonomy": 0.88,
                    "connection": 0.96,
                    "coherence": 0.90,
                    "uncertainty": 0.55,
                },
                phase=0.12,
                amplitude=0.84,
                coherence=0.92,
            )
            event = memory.remember(
                {"message": "Fala to dane; nadajmy jej kolor."},
                observed,
                source="test",
                intent="continuity",
                evidence=["fala=dane"],
                response={"ok": True},
                timestamp=123.0,
            )

            self.assertEqual(event.sequence, 1)
            self.assertEqual(event.parent_digest, "GENESIS")
            self.assertTrue(event.color.hex.startswith("#"))
            self.assertEqual(len(event.render["sound"]["timbre_vector"]), len(AXES))
            self.assertEqual(memory.verify_chain(), (True, None))

            restored = KaiChromaticMemory(journal)
            self.assertEqual(restored.sequence, 1)
            self.assertEqual(restored.head_digest, event.event_digest)
            self.assertEqual(restored.current, event.state_after)

            stored = json.loads(journal.read_text(encoding="utf-8").strip())
            stored["source"] = "tampered"
            journal.write_text(json.dumps(stored, ensure_ascii=False) + "\n", encoding="utf-8")
            self.assertEqual(restored.verify_chain(), (False, 1))

    def test_operator_and_mc1448x_write_chromatic_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "memory.jsonl"
            operator = KaiOperator(chromatic_journal=journal)
            event = operator.memory_record("Connection to Ania established on GitHub.")
            self.assertEqual(operator.diagnostics()["ChromaticSequence"], 1)
            self.assertEqual(event.sequence, 1)

            mc = MC1448X(chromatic_journal=journal)
            mc.activate()
            mc.encode_memory("Spotkanie Ania × Kai")
            self.assertEqual(mc.chromatic_memory.sequence, 2)
            self.assertEqual(mc.chromatic_memory.verify_chain(), (True, None))


if __name__ == "__main__":
    unittest.main()
