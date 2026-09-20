import unittest

from kai_operator import KaiOperator
from kai_lambda_housekeeper import (
    Action, Decision, DecisionRationale, Edge, EpistemicType, GraphState,
    KaiLambdaHousekeeper360, LambdaClass, LambdaResult, Node, Severity,
    SeverityScorer, TemporalAuditor, TemporalRelationship, tarjan_bridges,
)


class KaiLambdaHousekeeperTests(unittest.TestCase):
    def setUp(self):
        self.engine = KaiLambdaHousekeeper360()

    def test_semantic_discrepancy_is_repaired_transform_first(self):
        state = GraphState(nodes={
            "truth": Node("truth", semantic="Greece", epistemic=EpistemicType.OBSERVED,
                          source_id="intent", observed_at=100, metadata={"entity": "country"}),
            "form": Node("form", semantic="Egypt", epistemic=EpistemicType.REPORTED,
                         parents=["truth"], reported_at=101, metadata={"entity": "country"}),
        })
        result = self.engine.run(state, ["form"])
        self.assertIn("STATE_DISCREPANCY", {finding.kind for finding in result.findings})
        self.assertEqual(result.decisions[0].action, Action.TRANSFORM)
        self.assertEqual(result.final_state.nodes["form"].semantic, "Greece")

    def test_temporal_divergence_and_epoch_timestamp(self):
        first = Node("a", observed_at=0)
        second = Node("b", observed_at=TemporalAuditor.WINDOW_SECONDS + 1)
        self.assertEqual(TemporalAuditor().classify(first, second), TemporalRelationship.DIVERGENT)

    def test_provenance_links_feed_real_tarjan(self):
        state = GraphState(nodes={
            "a": Node("a"), "b": Node("b", parents=["a"]),
            "c": Node("c", parents=["b"]),
        })
        articulation, bridges = tarjan_bridges(state)
        self.assertEqual(articulation, {"b"})
        self.assertEqual(bridges, {("a", "b"), ("b", "c")})

    def test_cycle_detection_is_critical(self):
        state = GraphState(nodes={"a": Node("a", parents=["b"]),
                                  "b": Node("b", parents=["a"])})
        findings = self.engine.analyse(state)
        self.assertTrue(any(item.kind == "PROVENANCE_CYCLE" and
                            item.severity == Severity.CRITICAL for item in findings))

    def test_translation_caps_severity(self):
        self.assertEqual(SeverityScorer().score(
            EpistemicType.OBSERVED, EpistemicType.REPORTED, ["translation"]), Severity.LOW)

    def test_batch_conflict_cascades_weakest_decision(self):
        state = GraphState(nodes={"parent": Node("parent"),
                                  "child": Node("child", parents=["parent"])})
        weak = LambdaResult(LambdaClass.PLUS, 0.03, {}, 0.1)
        strong = LambdaResult(LambdaClass.PLUS, 0.05, {}, 0.9)
        rationale = DecisionRationale("test", 0, 0)
        accepted, removed, note = self.engine.batch.cascade_resolve(state, [
            Decision("parent", Action.DELETE, weak, rationale),
            Decision("child", Action.KEEP, strong, rationale),
        ])
        self.assertEqual([item.target for item in removed], ["parent"])
        self.assertEqual([item.target for item in accepted], ["child"])
        self.assertIn("DELETE_PARENT_ACTIVE_CHILD", note)

    def test_explicit_edge_and_parent_are_both_supported(self):
        state = GraphState(nodes={"a": Node("a"), "b": Node("b"), "c": Node("c")},
                           edges=[Edge("a", "b")])
        state.nodes["c"].parents = ["b"]
        self.assertEqual(tarjan_bridges(state)[0], {"b"})

    def test_operator_activates_housekeeper(self):
        operator = KaiOperator()
        operator.activate()
        self.assertIsInstance(operator.housekeeper_engine, KaiLambdaHousekeeper360)
        self.assertTrue(operator.diagnostics()["LambdaHousekeeper360"])


if __name__ == "__main__":
    unittest.main()
