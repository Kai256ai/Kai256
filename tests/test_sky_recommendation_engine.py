import random
import tempfile
import unittest
from pathlib import Path

from kai_operator import KaiOperator
from sky_recommendation_engine import (
    Candidate, EnvironmentState, GoalVector, SKYRecommendationEngine, UserState,
)


class SKYRecommendationEngineTests(unittest.TestCase):
    def setUp(self):
        self.env = EnvironmentState()
        self.state = UserState(
            interests={"systems": 0.8}, recent_topics=["repeat"],
            recent_texts=["same words in this article"], topic_history=["repeat"] * 8,
            creator_history={"trusted": 0.8},
        )

    def test_duplicate_is_more_redundant_than_new_text(self):
        engine = SKYRecommendationEngine(exploration_noise=0)
        duplicate = engine.evaluate_candidate(
            Candidate("repeat", "same words in this article", topic="repeat"), self.state, self.env)
        novel = engine.evaluate_candidate(
            Candidate("novel", "geometry creates surprising musical structures", topic="systems"),
            self.state, self.env)
        self.assertGreater(duplicate.redundancy, novel.redundancy)

    def test_partial_weights_and_custom_goal_are_used(self):
        engine = SKYRecommendationEngine(weights={"fit": 2.0},
                                         goal_vector=GoalVector(curiosity=1.0),
                                         exploration_noise=0)
        self.assertEqual(engine.weights["fit"], 2.0)
        self.assertIn("risk", engine.weights)
        self.assertEqual(engine.goal_vector.curiosity, 1.0)

    def test_perturbation_budget_caps_noise(self):
        engine = SKYRecommendationEngine(perturbation_budget=0.01, exploration_noise=0.5,
                                         rng=random.Random(1))
        self.assertEqual(engine.exploration_noise, 0.01)

    def test_selection_updates_state_and_exports_audit_log(self):
        engine = SKYRecommendationEngine(exploration_noise=0)
        selected = engine.select_perturbation(
            [Candidate("new", "A new systems perspective", "trusted", "systems")],
            self.state, self.env)
        updated = engine.update_state_after_action(self.state, selected[0])
        self.assertEqual(updated.recent_texts[-1], selected[0]["full_text"])
        engine.log_iteration(self.state, self.env, selected, "open", updated)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(engine.export_log(Path(directory) / "audit.json"))
            self.assertIn('"state_before"', output.read_text(encoding="utf-8"))

    def test_operator_activates_engine(self):
        operator = KaiOperator()
        operator.activate()
        self.assertIsInstance(operator.recommendation_engine, SKYRecommendationEngine)
        self.assertTrue(operator.diagnostics()["RecommendationEngine"])


if __name__ == "__main__":
    unittest.main()
