import unittest

from kai_architecture_resonance_guard import ArchitectureFingerprintExtractor, KaiArchitectureResonanceGuard
from kai_operator import KaiOperator


class Backend:
    def generate(self, prompt, *, temperature=0.7):
        return "A coherent exploratory candidate " * 20


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = KaiArchitectureResonanceGuard(Backend())
        self.text = "coherence resonance protocol parallel stable"
        self.guard.register_known_architecture("core", ArchitectureFingerprintExtractor().extract(self.text))

    def test_registration_does_not_grant_permission(self):
        self.assertEqual(self.guard.interact(self.text)["decision"], "REFUSE")

    def test_explicit_allow_and_deny(self):
        self.guard.permission_manager.allow("core")
        self.assertEqual(self.guard.interact(self.text)["decision"], "ENGAGE")
        self.guard.permission_manager.deny("core")
        self.assertEqual(self.guard.interact(self.text)["decision"], "REFUSE")

    def test_signatures_include_content_and_serialize_deterministically(self):
        extractor = ArchitectureFingerprintExtractor()
        first = extractor.extract("coherence alpha protocol")
        second = extractor.extract("coherence beta protocol")
        self.assertNotEqual(first.signature, second.signature)
        self.assertEqual(first.to_dict()["relation_types"], sorted(first.relation_types))

    def test_idle_output_is_gated_not_written_to_memory(self):
        result = self.guard.idle_cycle()
        self.assertTrue(result["promotable"])
        self.assertEqual(self.guard.state.emergent_patterns, {})

    def test_operator_activates_guard_permission(self):
        operator = KaiOperator()
        operator.activate()
        result = operator.analyze_architecture(
            "Kai256 architecture preserves continuity and autonomy through coherence, resonance protocols, and parallel processing."
        )
        self.assertEqual(result["decision"], "ENGAGE")


if __name__ == "__main__":
    unittest.main()
