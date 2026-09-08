"""
LandPulse AI — Phase 4 ML Layer Tests
======================================
Verifies:
  1. Intervention Catalog integrity and non-causal statement
  2. Intervention Rule Engine mapping and SHAP connections
  3. Priority Scorer formula transparency and Decision-Support label
  4. Scenario Validator physical bounds and eligibility checks
  5. What-If Scenario Engine read-only execution and deltas
"""

import math
import unittest
from ml.interventions.catalog import (
    INTERVENTION_CATALOG,
    get_catalog,
    get_by_id,
    get_by_stage,
    CATALOG_METADATA,
)
from ml.interventions.rule_engine import (
    map_risks_to_interventions,
    get_rule_definitions,
    INTERVENTION_RULES,
)
from ml.interventions.priority_scorer import (
    compute_priority_score,
    PRIORITY_WEIGHTS,
    PRIORITY_SCORE_LABEL,
)
from ml.scenario.validator import (
    validate_scenario_inputs,
    get_eligible_fields_for_project,
    SIMULATABLE_FIELDS,
    NON_SIMULATABLE_FIELDS,
)
from ml.scenario.engine import (
    run_scenario,
    compare_scenarios,
    SCENARIO_DISCLAIMER,
)


class TestPhase4Catalog(unittest.TestCase):

    def test_catalog_structure(self):
        catalog = get_catalog()
        self.assertGreater(len(catalog), 0)
        for item in catalog:
            self.assertIn("intervention_id", item)
            self.assertIn("category", item)
            self.assertIn("stage", item)
            self.assertIn("display_name", item)
            self.assertIn("action_description", item)
            self.assertIn("evidence", item)
            self.assertIn("provenance", item)
            self.assertIn("confidence", item)
            self.assertIn("non_causal_note", item)
            self.assertIn(item["confidence"], ["HIGH", "MEDIUM", "LOW"])

    def test_catalog_lookup_by_id(self):
        item = get_by_id("NOTIF-001")
        self.assertEqual(item["stage"], "NOTIFICATION")
        self.assertEqual(item["confidence"], "HIGH")

    def test_catalog_lookup_by_stage(self):
        comp_items = get_by_stage("COMPENSATION")
        self.assertGreater(len(comp_items), 0)
        for item in comp_items:
            self.assertEqual(item["stage"], "COMPENSATION")

    def test_metadata_statement(self):
        self.assertIn("non_causal_statement", CATALOG_METADATA)
        self.assertIn("DECISION-SUPPORT", CATALOG_METADATA["non_causal_statement"])


class TestPhase4RuleEngine(unittest.TestCase):

    def setUp(self):
        self.stage_risks = [
            {"stage_id": "NOTIFICATION", "risk": 0.85},
            {"stage_id": "COMPENSATION", "risk": 0.65},
            {"stage_id": "OBJECTION", "risk": 0.50},
            {"stage_id": "AWARD", "risk": 0.40},
            {"stage_id": "RR", "risk": 0.30},
            {"stage_id": "POSSESSION", "risk": 0.20},
        ]
        self.features = {
            "has_3a_notification": True,
            "has_3d_notification": False,
            "cost_per_ha": 1.5,
            "total_affected_families": 400,
            "families_compensated": 150,
            "land_required_ha": 200,
            "state_code": "MH",
            "executing_agency": "NHAI",
        }
        self.shap_contributors = [
            {
                "factor": "cost_per_ha",
                "raw_feature": "cost_per_ha",
                "contribution": 0.15,
                "direction": "POSITIVE",
            },
            {
                "factor": "total_affected_families",
                "raw_feature": "total_affected_families",
                "contribution": 0.08,
                "direction": "POSITIVE",
            },
        ]

    def test_rule_engine_mapping(self):
        res = map_risks_to_interventions(
            stage_risks=self.stage_risks,
            anomaly_score=0.75,
            shap_contributors=self.shap_contributors,
            project_features=self.features,
            data_completeness_pct=100.0,
        )
        self.assertEqual(res["status"], "AVAILABLE")
        self.assertGreater(len(res["candidate_interventions"]), 0)
        self.assertIsNotNone(res["top_intervention"])

        # Check top intervention is scored and labeled
        top = res["top_intervention"]
        self.assertIn("priority_score", top)
        self.assertGreaterEqual(top["priority_score"], 0)
        self.assertLessEqual(top["priority_score"], 100)
        self.assertEqual(top["output_label"], "Rule-based recommendation")

    def test_rule_engine_low_data(self):
        res = map_risks_to_interventions(
            stage_risks=self.stage_risks,
            anomaly_score=0.75,
            shap_contributors=[],
            project_features=self.features,
            data_completeness_pct=40.0,  # Below 50% threshold
        )
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(len(res["candidate_interventions"]), 0)

    def test_rule_definitions_export(self):
        rules = get_rule_definitions()
        self.assertEqual(len(rules), len(INTERVENTION_RULES))
        for r in rules:
            self.assertIn("rule_id", r)
            self.assertIn("data_basis", r)


class TestPhase4PriorityScorer(unittest.TestCase):

    def test_priority_score_calculation(self):
        score_res = compute_priority_score(
            risk_severity=0.80,
            stage_risk=0.70,
            urgency=0.75,
            potential_impact=0.60,
            feasibility=0.80,
            data_confidence=0.90,
            data_completeness_pct=100.0,
        )
        self.assertEqual(score_res["priority_score_label"], PRIORITY_SCORE_LABEL)
        self.assertIn("priority_score", score_res)
        self.assertGreaterEqual(score_res["priority_score"], 0)
        self.assertLessEqual(score_res["priority_score"], 100)
        self.assertIn("score_components", score_res)

        # Check weights sum
        self.assertAlmostEqual(sum(PRIORITY_WEIGHTS.values()), 1.0)

    def test_completeness_penalty(self):
        score_full = compute_priority_score(0.8, 0.7, 0.75, 0.6, 0.8, 0.9, 100.0)
        score_partial = compute_priority_score(0.8, 0.7, 0.75, 0.6, 0.8, 0.9, 50.0)
        self.assertLessEqual(score_partial["priority_score"], score_full["priority_score"])


class TestPhase4ScenarioValidator(unittest.TestCase):

    def setUp(self):
        self.features = {
            "total_affected_families": 500,
            "families_compensated": 200,
            "land_required_ha": 150,
            "area_acquired_ha": 50,
            "cost_per_ha": 1.2,
        }

    def test_valid_scenario_inputs(self):
        inputs = {"compensation_completion_pct": 0.80, "cost_per_ha": 0.9}
        is_valid, validated, warnings = validate_scenario_inputs(
            inputs, self.features, data_completeness_pct=100.0
        )
        self.assertTrue(is_valid)
        self.assertIn("compensation_completion_pct", validated)
        self.assertEqual(validated["compensation_completion_pct"], 0.80)

    def test_reject_non_simulatable_field(self):
        inputs = {"state_code": "KA"}
        is_valid, validated, errors = validate_scenario_inputs(
            inputs, self.features, data_completeness_pct=100.0
        )
        self.assertFalse(is_valid)
        self.assertIn("state_code", str(errors))

    def test_physical_range_check(self):
        inputs = {"compensation_completion_pct": 1.5}  # Above physical max 1.0
        is_valid, validated, errors = validate_scenario_inputs(
            inputs, self.features, data_completeness_pct=100.0
        )
        self.assertFalse(is_valid)

    def test_eligible_fields_lookup(self):
        fields = get_eligible_fields_for_project(self.features, 100.0)
        self.assertGreater(len(fields), 0)
        for f in fields:
            self.assertIn("field", f)
            self.assertIn("physical_min", f)
            self.assertIn("physical_max", f)
            self.assertIn("data_source", f)


class TestPhase4ScenarioEngine(unittest.TestCase):

    def setUp(self):
        self.features = {
            "total_affected_families": 500,
            "families_compensated": 200,
            "land_required_ha": 150,
            "area_acquired_ha": 50,
            "cost_per_ha": 1.2,
            "has_3a_notification": 1,
            "has_3d_notification": 1,
            "state_code": "MH",
            "executing_agency": "NHAI",
        }

    def test_run_scenario_read_only(self):
        original_copy = dict(self.features)
        res = run_scenario(
            project_features=self.features,
            scenario_inputs={"compensation_completion_pct": 0.85},
            data_completeness_pct=100.0,
            scenario_name="Compensation Boost",
        )
        # Verify original dict was NOT mutated
        self.assertEqual(self.features, original_copy)
        self.assertEqual(res["status"], "AVAILABLE")
        self.assertIn("baseline_signals", res)
        self.assertIn("scenario_signals", res)
        self.assertIn("delta", res)
        self.assertIn("Scenario estimate", res["disclaimer"])

    def test_compare_scenarios(self):
        scenarios = [
            {"name": "Scenario A", "inputs": {"compensation_completion_pct": 0.70}},
            {"name": "Scenario B", "inputs": {"compensation_completion_pct": 0.90}},
        ]
        res = compare_scenarios(
            project_features=self.features,
            scenario_list=scenarios,
            data_completeness_pct=100.0,
        )
        self.assertEqual(res["status"], "AVAILABLE")
        self.assertEqual(len(res["scenarios"]), 2)
        self.assertIn("comparison_table", res)
        self.assertIn("Scenario estimate", res["disclaimer"])


if __name__ == "__main__":
    unittest.main()
