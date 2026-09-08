"""
LADRIS — Tests: Predictions & Model Management API (Phase 3)
"""

import sys
from pathlib import Path

# Ensure backend root directory is in sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from app.services.ml_service import (
    get_current_model_info,
    get_data_quality_metrics,
    get_model_features,
    get_model_metrics,
    get_prediction_confidence,
    get_prediction_for_project,
    get_stage_risk_for_project,
)


class DummyProject:
    id = "a0000000-0000-0000-0000-000000000001"
    project_code = "MH-NH-PUNE-01"
    name = "Pune Peripheral Ring Road Acquisition"
    total_area_ha = 145.2
    state_code = "MH"
    executing_agency = "NHAI"
    estimated_compensation_inr = 625000000.0
    planned_start_date = "2021-02-15"
    planned_end_date = "2024-12-31"
    status = "ACTIVE"
    risk_level = "HIGH"
    total_affected_families = 450


def test_get_current_model_info():
    info = get_current_model_info()
    assert "model_name" in info
    assert "model_version" in info
    assert "model_type" in info
    assert info["model_type"] == "ANOMALY_SCORER"
    assert "authenticity_statement" in info
    assert info["supervised_training_status"] == "DEFERRED"


def test_get_data_quality_metrics():
    dq = get_data_quality_metrics()
    assert "summary" in dq
    summary = dq["summary"]
    assert "total_real_records" in summary
    assert "missing_value_rate" in summary
    assert "data_authenticity_statement" in summary
    assert summary["total_real_records"] >= 0


def test_dual_signal_prediction():
    proj = DummyProject()
    pred = get_prediction_for_project(proj)
    assert pred["project_id"] == str(proj.id)
    assert "anomaly_risk" in pred
    assert "delay_risk" in pred
    assert pred["delay_risk"]["score"] is None
    assert pred["delay_probability"] is None
    assert pred["predicted_delay_days"] is None
    assert pred["prediction_status"] == "AVAILABLE"


def test_stage_risk_fingerprint():
    proj = DummyProject()
    fp = get_stage_risk_for_project(proj)
    assert fp["project_id"] == str(proj.id)
    assert "stages" in fp
    assert len(fp["stages"]) == 8
    assert fp["output_type"] in ("STAGE_DELAY_PROBABILITY_FINGERPRINT", "STAGE_RISK_FINGERPRINT")
    assert fp.get("overall_fingerprint_risk") is not None or fp.get("overall_delay_probability") is not None





def test_prediction_confidence():
    proj = DummyProject()
    conf = get_prediction_confidence(proj)
    assert conf["project_id"] == str(proj.id)
    assert conf["prediction_eligible"] is True
    assert conf["confidence_assessment"] in ("HIGH", "MEDIUM", "LOW")
    assert "calibration_note" in conf


def test_get_model_metrics():
    metrics = get_model_metrics()
    assert "supervised_metrics" in metrics
    assert metrics["supervised_metrics"]["available"] is False
    assert metrics["supervised_training_status"] == "DEFERRED"
    assert "anomaly_scorer_metrics" in metrics


def test_get_model_features():
    catalog = get_model_features()
    assert "model_features" in catalog or "available_features" in catalog
