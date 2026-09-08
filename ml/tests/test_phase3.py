"""
LandPulse AI — Phase 3 ML Unit Tests
======================================
Tests for:
  1. Target definition documentation & data gap report
  2. Stage Risk Fingerprint computation & stage eligibility
  3. Feature engineering & temporal leakage prevention
  4. SHAP XAI explanation formatting & contributor labeling
  5. Prediction confidence & out-of-distribution (OOD) check
  6. Dual-signal separation (anomaly_risk vs delay_risk)
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Ensure ML package is in import path
ML_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ML_DIR.parent))

from ml.features.feature_engineering import get_model_features
from ml.features.leakage_check import check_feature_set, FORBIDDEN_PROSPECTIVE_FEATURES
from ml.stage_intelligence.stage_risk_engine import (
    compute_stage_fingerprint,
    compute_notification_stage_risk,
    compute_objection_stage_risk,
    score_to_risk_level,
)
from ml.evaluation.shap_explainer import (
    _get_feature_description,
    SHAP_DISCLAIMER,
)


def test_target_definition_and_data_gap_report():
    """Verify data gap report exists and documents target requirement correctly."""
    from ml.training.data_gap_report import REPORT
    assert REPORT["version"] == "1.1.0"
    assert REPORT["ml_decision"]["supervised_training"] == "DEFERRED"
    assert REPORT["supervised_target_definition"]["required_sample_count"] == 200
    assert "delay_event = 1" in REPORT["supervised_target_definition"]["canonical_target_formula"]


def test_leakage_check_prospective_mode():
    """Verify prospective feature set contains no forbidden post-event features."""
    features = get_model_features(mode="prospective")
    res = check_feature_set(features, mode="prospective")
    assert res["leakage_detected"] is False
    assert len(res["violations"]) == 0

    # Test that forbidden feature raises violation
    res_leak = check_feature_set(["land_required_ha_log", "actual_end_date"], mode="prospective")
    assert res_leak["leakage_detected"] is True
    assert res_leak["violations"][0]["feature"] == "actual_end_date"


def test_stage_risk_engine_fingerprint():
    """Test full Stage Risk Fingerprint computation across 6 stages."""
    sample_features = {
        "state_code": "MH",
        "executing_agency": "NHAI",
        "has_3a_notification": True,
        "has_3d_notification": True,
        "notification_interval_days": 194.0,  # Median interval
        "cost_per_ha": 0.85,
        "land_required_ha": 145.2,
        "total_affected_families": 450,
    }

    fp = compute_stage_fingerprint(sample_features)

    assert "stages" in fp
    assert len(fp["stages"]) == 6

    stage_ids = [s["stage_id"] for s in fp["stages"]]
    assert stage_ids == ["NOTIFICATION", "OBJECTION", "AWARD", "COMPENSATION", "RR", "POSSESSION"]

    # All stages should be eligible with non-null risk
    for stage in fp["stages"]:
        assert stage["eligible"] is True
        assert stage["risk"] is not None
        assert 0.0 <= stage["risk"] <= 1.0
        assert stage["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    assert fp["overall_fingerprint_risk"] is not None
    assert fp["peak_risk_stage"] is not None
    assert fp["output_type"] == "STAGE_RISK_FINGERPRINT"


def test_notification_stage_risk_real_signal():
    """Test NOTIFICATION stage risk derived from 3A->3D interval."""
    # Median interval (194d) -> MEDIUM risk
    res_mid = compute_notification_stage_risk(194.0, True, True)
    assert res_mid["eligible"] is True
    assert res_mid["risk_level"] in ("LOW", "MEDIUM")

    # Long interval (240d > p95) -> HIGH risk
    res_high = compute_notification_stage_risk(240.0, True, True)
    assert res_high["risk_level"] in ("HIGH", "CRITICAL")

    # No 3A date -> ineligible
    res_no3a = compute_notification_stage_risk(None, False, False)
    assert res_no3a["eligible"] is False


def test_score_to_risk_level_mapping():
    """Verify threshold score to risk level string mapping."""
    assert score_to_risk_level(0.10) == "LOW"
    assert score_to_risk_level(0.45) == "MEDIUM"
    assert score_to_risk_level(0.70) == "HIGH"
    assert score_to_risk_level(0.85) == "CRITICAL"


def test_shap_feature_descriptions():
    """Verify SHAP human-readable feature descriptions contain no causal claims."""
    desc_high = _get_feature_description("cost_per_ha", is_high_risk=True)
    assert "caused" not in desc_high.lower()
    assert "cost per hectare" in desc_high.lower() or "cost" in desc_high.lower()

    desc_low = _get_feature_description("land_required_ha_log", is_high_risk=False)
    assert "caused" not in desc_low.lower()
    assert "typical" in desc_low.lower()


def test_dual_signal_separation_in_ml_service():
    """Test that ml_service.get_prediction_for_project returns dual-signal format."""
    from backend.app.services.ml_service import get_prediction_for_project

    class MockProject:
        id = "12345678-1234-5678-1234-567812345678"
        total_area_ha = 145.2
        state_code = "MH"
        executing_agency = "NHAI"
        estimated_compensation_inr = 625000000.0
        planned_start_date = "2021-02-15"
        status = "ACTIVE"
        total_affected_families = 450

    res = get_prediction_for_project(MockProject())

    assert "anomaly_risk" in res
    assert "delay_risk" in res

    # Signal 1: Anomaly Risk must be present
    assert res["anomaly_risk"]["label"] == "Structural Anomaly Score"
    assert 0.0 <= res["anomaly_risk"]["score"] <= 1.0

    # Signal 2: Delay Risk must be DEFERRED (null score)
    assert res["delay_risk"]["score"] is None
    assert res["delay_risk"]["supervised_training_status"] == "DEFERRED"

    # Legacy delay_probability must be null, NOT equal to anomaly score
    assert res["delay_probability"] is None
    assert res["predicted_delay_days"] is None
