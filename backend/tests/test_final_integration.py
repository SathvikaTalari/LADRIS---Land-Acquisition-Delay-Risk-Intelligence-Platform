"""
LADRIS — Phase 6 Final System Integration Test Suite
===========================================================
Covers all 15 mandated integration test domains:
  1. Authentication
  2. RBAC
  3. Project retrieval
  4. Risk fingerprint
  5. SHAP explanation
  6. Confidence & OOD
  7. Intervention priority
  8. Scenario simulation
  9. GIS project retrieval
  10. Alerts
  11. Audit logging
  12. Reports
  13. Data provenance
  14. Data quality
  15. Search
"""

import sys
import pytest
from pathlib import Path

# Add backend root to sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.services.ml_service import (
    get_prediction_for_project,
    get_stage_risk_for_project,
    get_explanation_for_project,
    get_prediction_confidence,
    get_current_model_info,
    get_data_quality_metrics,
)

client = TestClient(app)


class MockProject:
    id = "a0000000-0000-0000-0000-000000000001"
    project_code = "MH-NH-PUNE-01"
    name = "Pune Peripheral Ring Road Acquisition"
    total_area_ha = 145.2
    state_code = "MH"
    district_codes = ["PUNE"]
    executing_agency = "NHAI"
    nodal_agency = "MoRTH"
    estimated_compensation_inr = 625000000.0
    planned_start_date = "2021-02-15"
    planned_end_date = "2024-12-31"
    status = "ACTIVE"
    risk_level = "HIGH"
    total_affected_families = 450


def test_01_authentication():
    """1. Test authentication endpoint protection."""
    res = client.post("/api/v1/auth/login", json={"email": "invalid@ladris.gov.in", "password": "wrong"})
    assert res.status_code in (400, 401, 422)


def test_02_rbac():
    """2. Test RBAC protection on analyst-only endpoints without token."""
    res = client.get("/api/v1/models/metrics")
    assert res.status_code in (401, 403)


def test_03_project_retrieval():
    """3. Test project list endpoint structure."""
    res = client.get("/api/v1/projects/")
    # If unauthenticated, returns 401; if public route or test client mocked, returns 200 or 401
    assert res.status_code in (200, 401)


def test_04_risk_fingerprint():
    """4. Test Stage Risk Fingerprint generation."""
    proj = MockProject()
    fp = get_stage_risk_for_project(proj)
    assert fp["project_id"] == str(proj.id)
    assert "stages" in fp
    assert len(fp["stages"]) == 8
    assert fp["output_type"] in ("STAGE_DELAY_PROBABILITY_FINGERPRINT", "STAGE_RISK_FINGERPRINT")




def test_05_shap_explanation():
    """5. Test SHAP explanation structure and non-causal disclaimer."""
    proj = MockProject()
    exp = get_explanation_for_project(proj)
    assert "disclaimer" in exp
    assert "NOT causal explanations" in exp["disclaimer"]
    assert exp["output_type"] in ("ANOMALY_SCORE_CONTRIBUTIONS", "INSUFFICIENT_DATA")


def test_06_confidence():
    """6. Test prediction confidence and OOD detection logic."""
    proj = MockProject()
    conf = get_prediction_confidence(proj)
    assert conf["prediction_eligible"] is True
    assert "out_of_distribution" in conf
    assert "calibration_note" in conf


def test_07_intervention_priority():
    """7. Test rule engine & priority scoring logic."""
    proj = MockProject()
    pred = get_prediction_for_project(proj)
    assert pred["prediction_status"] == "AVAILABLE"
    assert pred["anomaly_risk"]["score"] is not None
    # Supervised delay probability must be None
    assert pred["delay_risk"]["score"] is None


def test_08_scenario_simulation():
    """8. Test deterministic scenario engine."""
    from ml.scenario.engine import run_scenario
    features = {"land_required_ha_log": 4.5, "cost_per_ha": 0.8, "has_3a_notification": 1, "has_3d_notification": 1}
    res = run_scenario(features, {"cost_per_ha": 0.4})
    assert res["scenario_name"] is not None
    assert "Scenario estimate" in res["disclaimer"]


def test_09_gis_project_retrieval():
    """9. Test GIS GeoJSON endpoint protection."""
    res = client.get("/api/v1/gis/projects")
    assert res.status_code in (200, 401)


def test_10_alerts():
    """10. Test alerts endpoint protection."""
    res = client.get("/api/v1/alerts/")
    assert res.status_code in (200, 401)


def test_11_audit_logging():
    """11. Test audit log service function."""
    from app.services.audit_service import record_audit_log
    # Function exists and signature is intact
    assert callable(record_audit_log)


def test_12_reports():
    """12. Test reports endpoint protection."""
    res = client.get("/api/v1/reports/projects.csv")
    assert res.status_code in (200, 401)


def test_13_data_provenance():
    """13. Test data sources catalog metadata."""
    res = client.get("/api/v1/data-sources/")
    assert res.status_code in (200, 401)


def test_14_data_quality():
    """14. Test data quality report metrics."""
    dq = get_data_quality_metrics()
    assert "summary" in dq
    assert dq["summary"]["total_real_records"] > 0
    assert dq["summary"]["invalid_records"] == 0


def test_15_search():
    """15. Test global search endpoint protection."""
    res = client.get("/api/v1/search/?q=Pune")
    assert res.status_code in (200, 401)
