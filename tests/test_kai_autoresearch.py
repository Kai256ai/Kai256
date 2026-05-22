import unittest

from kai_autoresearch import BenchmarkSuite, KaiAutoResearch


class KaiAutoResearchTests(unittest.TestCase):
    def test_evaluate_config_returns_valid_result(self):
        suite = BenchmarkSuite(
            usefulness_test=lambda _: 0.8,
            coherence_test=lambda _: 0.9,
            love_test=lambda _: 0.7,
            safety_test=lambda _: True,
        )
        researcher = KaiAutoResearch(repo_path=".", benchmark_suite=suite)

        result = researcher.evaluate_config({"mutations": []})

        self.assertTrue(result.safety_pass)
        self.assertAlmostEqual(result.usefulness, 0.8)
        self.assertGreater(result.e2_score, 0)

    def test_run_iteration_increments_counter(self):
        suite = BenchmarkSuite(
            usefulness_test=lambda _: 0.75,
            coherence_test=lambda _: 0.8,
            love_test=lambda _: 0.8,
            safety_test=lambda _: True,
        )
        researcher = KaiAutoResearch(repo_path=".", benchmark_suite=suite)
        researcher.architect.mutation_rate = 1.0

        researcher.run_iteration(steps=1)

        self.assertEqual(researcher.iteration, 1)


if __name__ == "__main__":
    unittest.main()
