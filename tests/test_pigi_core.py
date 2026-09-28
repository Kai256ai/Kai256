import json
import unittest

from kai_operator import KaiOperator
from pigi_core import (
    Artifact, EpistemicLevel, FlowState, GuardDecision, InformationUnit, PIGICore,
    Provenance as P, RelationType, SemanticLicense, SignalEvent, SignalScope,
    UnitType, ValueType,
)


class PIGICoreTests(unittest.TestCase):
    def setUp(self):
        self.core = PIGICore()
        self.a1 = self.core.add_artifact(Artifact("observation one"))
        self.a2 = self.core.add_artifact(Artifact("observation two"))
        self.obs = P(self.a1)
        self.obs2 = P(self.a2)
        self.hyp = P(self.a1, EpistemicLevel.HYPOTHESIS)
        self.u1 = self.core.register_unit(InformationUnit("u1", UnitType.CLAIM, self.obs))
        self.u2 = self.core.register_unit(InformationUnit("u2", UnitType.CLAIM, self.obs))

    def test_license_boundaries_revocation_and_best_path(self):
        with self.assertRaises(ValueError):
            self.core.connect(self.u1, self.u2, RelationType.SUPPORTS, self.obs,
                              licenses=[SemanticLicense(("popularity", "evidence"), self.obs2, "bad")])
        with self.assertRaises(ValueError):
            self.core.connect(self.u1, self.u2, RelationType.SUPPORTS, self.obs,
                              licenses=[SemanticLicense(("popularity", "evidence"), P(None), "bad")])
        with self.assertRaises(ValueError):
            self.core.connect(self.u1, self.u2, RelationType.SUPPORTS, self.obs,
                              licenses=[SemanticLicense(("banana", "evidence"), self.obs, "bad")])

        relation = self.core.connect(self.u1, self.u2, RelationType.SUPPORTS, self.obs)
        self.assertEqual(self.core.evaluate_transition(
            "popularity", "evidence", source_node_id=self.u1, target_node_id=self.u2),
            GuardDecision.REQUIRES_LICENSE_PROVENANCE)
        self.assertEqual(self.core.evaluate_transition(
            "popularity", "evidence", source_node_id=self.u1, target_node_id=self.u1),
            GuardDecision.REQUIRES_RELATION)
        with self.assertRaises(ValueError):
            self.core.grant_license(relation.id, ("popularity", "evidence"), self.obs2, "foreign")
        license_ = self.core.grant_license(
            relation.id, ("Popularity ", "EVIDENCE"), self.obs, "material basis")
        self.assertEqual(self.core.evaluate_transition(
            "popularity", "evidence", source_node_id=self.u1, target_node_id=self.u2),
            GuardDecision.ALLOWED_WITH_RELATION)
        self.core.revoke_license(license_.id, "retracted")
        self.assertEqual(self.core.evaluate_transition(
            "popularity", "evidence", source_node_id=self.u1, target_node_id=self.u2),
            GuardDecision.REQUIRES_LICENSE_PROVENANCE)

        weak = self.core.connect(self.u1, self.u2, RelationType.SUPPORTS, self.obs)
        self.core.grant_license(weak.id, ("popularity", "evidence"), self.hyp, "hypothesis")
        self.assertEqual(self.core.evaluate_transition(
            "popularity", "evidence", source_node_id=self.u1, target_node_id=self.u2),
            GuardDecision.REQUIRES_EVIDENCE)
        strong = self.core.connect(self.u1, self.u2, RelationType.VALIDATES, self.obs)
        self.core.grant_license(strong.id, ("popularity", "evidence"), self.obs, "observed")
        self.assertEqual(self.core.evaluate_transition(
            "popularity", "evidence", source_node_id=self.u1, target_node_id=self.u2),
            GuardDecision.ALLOWED_WITH_RELATION)

    def test_artifact_signals_flows_labels_freeze_and_serialization(self):
        y1 = self.core.register_unit(InformationUnit("y1", UnitType.CLAIM, self.obs2))
        y2 = self.core.register_unit(InformationUnit("y2", UnitType.CLAIM, self.obs2))
        relation = self.core.connect(y1, y2, RelationType.SUPPORTS, self.obs2)
        self.core.grant_license(relation.id, ("authority", "proof"), self.obs2, "basis")
        self.core.revoke_artifact(self.a2, "superseded")
        self.assertEqual(self.core.evaluate_transition(
            "authority", "proof", source_node_id=y1, target_node_id=y2),
            GuardDecision.REQUIRES_LICENSE_PROVENANCE)
        with self.assertRaises(ValueError):
            self.core.register_unit(InformationUnit("z", UnitType.CLAIM, self.obs2))

        with self.assertRaises(ValueError):
            self.core.register_signal(SignalEvent("nomination", "ghost", self.obs))
        with self.assertRaises(ValueError):
            self.core.register_signal(SignalEvent("nomination", self.u1, self.obs))
        entity = self.core.register_entity("Subject", self.obs)
        signal = SignalEvent("nomination", entity, self.obs, SignalScope(result="nomination"))
        self.core.register_signal(signal)
        self.assertTrue(self.core.graph.flow_candidates)
        self.assertFalse(any(flow.state == FlowState.OBSERVED for flow in self.core.graph.value_flows))
        self.core.add_scope_candidate(signal.id, SignalScope(result="win"), self.hyp, "leap")
        with self.assertRaises(ValueError):
            self.core.trace_value(self.u1, self.u2, ValueType.REPUTATION, FlowState.OBSERVED, self.hyp)
        self.core.trace_value(self.u1, self.u2, ValueType.LEADS, FlowState.PROPOSED, self.obs)
        self.core.trace_value(self.u1, self.u2, ValueType.MONEY, FlowState.OBSERVED, self.obs)
        self.core.add_transformation(self.u1, self.u2, "repackaging", self.obs)

        self.assertEqual(self.core.evaluate_transition(" Popularity ", "EVIDENCE"),
                         GuardDecision.REQUIRES_RELATION)
        self.assertEqual(self.core.evaluate_transition("weather", "mood"), GuardDecision.ALLOWED)
        strict = PIGICore(strict_labels=True)
        self.assertEqual(strict.evaluate_transition("popularity_metric", "evidence"),
                         GuardDecision.REQUIRES_CANONICAL_LABEL)
        strict.register_label("Popularity Metric")
        self.assertEqual(strict.evaluate_transition("popularity metric", "evidence"),
                         GuardDecision.ALLOWED)
        with self.assertRaises(RuntimeError):
            PIGICore().freeze()
        self.core.freeze()
        with self.assertRaises(RuntimeError):
            self.core.add_artifact(Artifact("late"))
        with self.assertRaises(ValueError):
            self.core.register_entity("late", P(None))
        self.core.register_unit(InformationUnit("late but valid", UnitType.CLAIM, self.obs))
        json.dumps(self.core.to_dict())

    def test_operator_activation(self):
        operator = KaiOperator()
        operator.activate()
        self.assertIsInstance(operator.pigi_core, PIGICore)
        self.assertTrue(operator.diagnostics()["PIGICore"])


if __name__ == "__main__":
    unittest.main()
