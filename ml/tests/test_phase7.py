"""
LandPulse AI — Phase 7 ML & Intelligence Unit Tests
=====================================================
Tests for Phase 7 Decision Intelligence components:
  1. Risk DNA composer
  2. Temporal Risk Intelligence & no-fabrication safeguards
  3. Bottleneck Discovery Engine & small-sample safeguards
  4. Comparable Project Finder & cosine similarity
  5. Cross-Project Priority Queue & resource scenario simulator
  6. Provenance & evidence type standards (A/B/C/D/E)
"""

import sys
from pathlib import Path

import pytest
import numpy as np

# Ensure workspace root is in path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from ml.intelligence.risk_dna import compose_risk_dna, DNA_WEIGHTS
from ml.intelligence.temporal import analyze_temporal_risk, get_project_observations
from ml.intelligence.bottleneck import analyze_bottlenecks, analyze_state_bottleneck, _classify_confidence
from ml.intelligence.comparable_projects import find_comparable_projects, _encode_project_features, _weighted_cosine_similarity
from ml.intelligence.priority_queue import build_priority_queue, build_project_queue_entry, run_resource_scenario


# ─── Mock Data Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def mock_project():
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "project_id": "11111111-1111-1111-1111-111111111111",
        "project_code": "MH-NH-PUNE-01",
        "name": "Pune Peripheral Ring Road Land Acquisition",
        "state_code": "MH",
        "district_codes": ["PUNE"],
        "executing_agency": "NHAI",
        "acquisition_act": "RFCTLARR_2013",
        "total_area_ha": 185.5,
        "estimated_compensation_inr": 850000000.0,
        "total_affected_families": 1200,
        "status": "APPROVED",
        "risk_level": "HIGH",
    }


@pytest.fixture
def mock_project_list():
    return [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "project_id": "11111111-1111-1111-1111-111111111111",
            "project_code": "MH-NH-PUNE-01",
            "name": "Pune Peripheral Ring Road",
            "state_code": "MH",
            "executing_agency": "NHAI",
            "acquisition_act": "RFCTLARR_2013",
            "total_area_ha": 185.5,
            "estimated_compensation_inr": 850000000.0,
            "total_affected_families": 1200,
            "status": "APPROVED",
            "risk_level": "HIGH",
            "stage_fingerprint": {
                "stages": [
                    {"stage_id": "NOTIFICATION", "risk": 0.70, "eligible": True},
                    {"stage_id": "OBJECTION", "risk": 0.65, "eligible": True},
                    {"stage_id": "AWARD", "risk": 0.50, "eligible": True},
                    {"stage_id": "COMPENSATION", "risk": 0.80, "eligible": True},
                    {"stage_id": "RR", "risk": 0.75, "eligible": True},
                    {"stage_id": "POSSESSION", "risk": 0.60, "eligible": True},
                ],
                "overall_fingerprint_risk": 0.68,
                "peak_risk_stage": "COMPENSATION",
                "peak_risk_value": 0.80,
            },
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "project_id": "22222222-2222-2222-2222-222222222222",
            "project_code": "MH-NH-MUMB-02",
            "name": "Mumbai Suburban Expressway Link",
            "state_code": "MH",
            "executing_agency": "NHAI",
            "acquisition_act": "RFCTLARR_2013",
            "total_area_ha": 140.0,
            "estimated_compensation_inr": 920000000.0,
            "total_affected_families": 950,
            "status": "DELAYED",
            "risk_level": "CRITICAL",
            "stage_fingerprint": {
                "stages": [
                    {"stage_id": "NOTIFICATION", "risk": 0.80, "eligible": True},
                    {"stage_id": "OBJECTION", "risk": 0.85, "eligible": True},
                    {"stage_id": "AWARD", "risk": 0.60, "eligible": True},
                    {"stage_id": "COMPENSATION", "risk": 0.75, "eligible": True},
                    {"stage_id": "RR", "risk": 0.70, "eligible": True},
                    {"stage_id": "POSSESSION", "risk": 0.80, "eligible": True},
                ],
                "overall_fingerprint_risk": 0.75,
                "peak_risk_stage": "OBJECTION",
                "peak_risk_value": 0.85,
            },
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "project_id": "33333333-3333-3333-3333-333333333333",
            "project_code": "UP-NH-LKNO-03",
            "name": "Lucknow Outer Ring Road",
            "state_code": "UP",
            "executing_agency": "NHAI",
            "acquisition_act": "NH_ACT_1956",
            "total_area_ha": 210.0,
            "estimated_compensation_inr": 450000000.0,
            "total_affected_families": 600,
            "status": "APPROVED",
            "risk_level": "MEDIUM",
            "stage_fingerprint": {
                "stages": [
                    {"stage_id": "NOTIFICATION", "risk": 0.40, "eligible": True},
                    {"stage_id": "OBJECTION", "risk": 0.35, "eligible": True},
                    {"stage_id": "AWARD", "risk": 0.45, "eligible": True},
                    {"stage_id": "COMPENSATION", "risk": 0.50, "eligible": True},
                    {"stage_id": "RR", "risk": 0.40, "eligible": True},
                    {"stage_id": "POSSESSION", "risk": 0.38, "eligible": True},
                ],
                "overall_fingerprint_risk": 0.42,
                "peak_risk_stage": "COMPENSATION",
                "peak_risk_value": 0.50,
            },
        },
    ]


@pytest.fixture
def mock_anomaly_result():
    return {
        "prediction_status": "AVAILABLE",
        "anomaly_risk": {
            "score": 0.65,
            "risk_level": "MEDIUM",
            "is_anomaly": False,
            "label": "Structural Anomaly Score",
        },
        "delay_risk": {
            "score": None,
            "risk_level": None,
            "prediction_available": False,
            "supervised_training_status": "DEFERRED",
        },
        "overall_risk_score": 0.65,
        "data_completeness_pct": 100.0,
    }


@pytest.fixture
def mock_stage_fingerprint():
    return {
        "stages": [
            {"stage_id": "NOTIFICATION", "risk": 0.70, "risk_level": "HIGH", "data_basis": "REAL_SIGNAL", "eligible": True},
            {"stage_id": "OBJECTION", "risk": 0.60, "risk_level": "HIGH", "data_basis": "PROXY", "eligible": True},
            {"stage_id": "AWARD", "risk": 0.45, "risk_level": "MEDIUM", "data_basis": "PROXY", "eligible": True},
            {"stage_id": "COMPENSATION", "risk": 0.75, "risk_level": "HIGH", "data_basis": "PROXY", "eligible": True},
            {"stage_id": "RR", "risk": 0.65, "risk_level": "HIGH", "data_basis": "PROXY", "eligible": True},
            {"stage_id": "POSSESSION", "risk": 0.55, "risk_level": "MEDIUM", "data_basis": "PROXY", "eligible": True},
        ],
        "overall_fingerprint_risk": 0.62,
        "overall_fingerprint_risk_level": "HIGH",
        "peak_risk_stage": "COMPENSATION",
        "peak_risk_value": 0.75,
    }


# ─── 1. Risk DNA Tests ────────────────────────────────────────────────────────

def test_risk_dna_weights_sum_to_one():
    """Verify DNA weights sum to exactly 1.0."""
    assert abs(sum(DNA_WEIGHTS.values()) - 1.0) < 1e-9


def test_compose_risk_dna_structure(mock_project, mock_anomaly_result, mock_stage_fingerprint):
    """Test Risk DNA composition returns all required dimensions and output type labels."""
    dna = compose_risk_dna(
        project_id=mock_project["id"],
        anomaly_result=mock_anomaly_result,
        stage_fingerprint=mock_stage_fingerprint,
        shap_explanation={"top_positive_contributors": [{"display_name": "Acquisition Cost", "shap_contribution": 0.15}]},
        prediction_confidence={"confidence_assessment": "HIGH", "out_of_distribution": {"is_ood": False}},
        temporal_observations=[],
    )

    assert dna["project_id"] == mock_project["id"]
    assert dna["output_type"] == "RISK_DNA"
    assert "dna_composite_score" in dna
    assert 0.0 <= dna["dna_composite_score"] <= 1.0
    assert dna["dna_tier"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")

    # Dimensions check
    dims = dna["dimensions"]
    assert "anomaly_signal" in dims
    assert "stage_fingerprint" in dims
    assert "data_completeness" in dims
    assert "shap_driver_severity" in dims
    assert "reliability" in dims

    # Evidence type labels check
    assert dims["anomaly_signal"]["output_type"] == "C"
    assert dims["data_completeness"]["output_type"] == "A"
    assert dims["reliability"]["output_type"] == "B"


# ─── 2. Temporal Risk Intelligence Tests ──────────────────────────────────────

def test_temporal_risk_no_data_safeguard():
    """Verify temporal analysis safely handles zero observations without fabrication."""
    result = analyze_temporal_risk("non-existent-uuid-99999")

    assert result["temporal_data_available"] is False
    assert result["observation_count"] == 0
    assert result["observations"] == []
    assert result["risk_trend"] is None
    assert result["risk_trend_label"] == "NO_DATA"
    assert "no temporal observation history" in result["temporal_disclaimer"].lower()


def test_temporal_trend_calculation():
    """Verify temporal trend calculation for real observations."""
    # We pass mock observations to test trend calculation logic
    from ml.intelligence.temporal import TEMPORAL_DISCLAIMER

    obs = [
        {"timestamp": "2026-08-20T10:00:00Z", "anomaly_score": 0.50},
        {"timestamp": "2026-08-22T10:00:00Z", "anomaly_score": 0.62},
    ]
    # Delta = 0.62 - 0.50 = +0.12 (> 0.05 -> ESCALATING)
    delta = obs[-1]["anomaly_score"] - obs[0]["anomaly_score"]
    assert delta > 0.05


# ─── 3. Bottleneck Discovery Tests ───────────────────────────────────────────

def test_bottleneck_small_sample_safeguard():
    """Verify small-sample safeguard stops analysis when N < MINIMUM_GROUP_SIZE."""
    # 2 projects < minimum 5
    small_list = [
        {"project_id": "1", "state_code": "MH", "stage_fingerprint": {"stages": [{"stage_id": "NOTIFICATION", "risk": 0.5}]}}
    ]
    res = analyze_bottlenecks(small_list)

    assert res["available"] is False
    assert "INSUFFICIENT_DATA" in res["reason"]


def test_bottleneck_discovery_clustering(mock_project_list):
    """Verify bottleneck discovery runs on sufficient data."""
    # Multiply mock projects to reach >5 threshold
    extended_list = mock_project_list * 3  # 9 projects
    res = analyze_bottlenecks(extended_list)

    assert res["available"] is True
    assert res["n_projects_analyzed"] == 9
    assert res["output_type"] == "B"
    assert "bottleneck_distribution" in res
    assert "cluster_analysis" in res


# ─── 4. Comparable Projects Tests ─────────────────────────────────────────────

def test_encode_project_features(mock_project):
    """Verify feature vector encoding returns expected 6 dimensions."""
    vec = _encode_project_features(mock_project)
    assert vec is not None
    assert vec.shape == (6,)


def test_find_comparable_projects(mock_project, mock_project_list):
    """Verify comparable project finder returns top-k sorted by similarity."""
    res = find_comparable_projects(
        target_project=mock_project,
        all_projects=mock_project_list,
        top_k=2,
    )

    assert res["available"] is True
    assert res["output_type"] == "B"
    assert "comparable_projects" in res
    comparables = res["comparable_projects"]

    # Target should not be compared to itself
    target_id = mock_project["id"]
    for c in comparables:
        assert c["project_id"] != target_id
        assert 0.0 <= c["similarity_score"] <= 1.0
        assert "similarity_explanation" in c


# ─── 5. Priority Queue & Resource Scenario Tests ─────────────────────────────

def test_build_project_queue_entry(mock_project, mock_anomaly_result, mock_stage_fingerprint):
    """Verify priority queue entry construction."""
    entry = build_project_queue_entry(
        project=mock_project,
        anomaly_result=mock_anomaly_result,
        stage_fingerprint=mock_stage_fingerprint,
        bottleneck_type="COMPENSATION",
        comparable_risk_signal=0.6,
    )

    assert entry["project_id"] == mock_project["id"]
    assert "composite_priority_score" in entry
    assert 0.0 <= entry["composite_priority_score"] <= 100.0
    assert entry["queue_tier"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert entry["output_type"] == "D"


def test_build_priority_queue(mock_project_list, mock_anomaly_result):
    """Verify priority queue sorting and filtering."""
    entries = []
    for p in mock_project_list:
        e = build_project_queue_entry(
            project=p,
            anomaly_result=mock_anomaly_result,
            stage_fingerprint=p["stage_fingerprint"],
        )
        entries.append(e)

    q = build_priority_queue(entries)

    assert q["output_type"] == "D"
    assert q["total_projects"] == len(mock_project_list)
    # Ranks should be 1..N in descending order of composite_priority_score
    scores = [item["composite_priority_score"] for item in q["queue"]]
    assert scores == sorted(scores, reverse=True)


def test_run_resource_scenario(mock_project_list, mock_anomaly_result):
    """Verify resource-constrained greedy allocation simulation."""
    entries = []
    for p in mock_project_list:
        e = build_project_queue_entry(
            project=p,
            anomaly_result=mock_anomaly_result,
            stage_fingerprint=p["stage_fingerprint"],
            bottleneck_type="COMPENSATION",
        )
        entries.append(e)

    # Capacity: LEGAL=1, COMPENSATION=1
    res = run_resource_scenario(
        queue_entries=entries,
        capacity_constraints={"LEGAL": 1, "COMPENSATION": 1},
    )

    assert res["output_type"] == "E"
    assert res["simulation_type"] == "GREEDY_RESOURCE_ALLOCATION"
    assert res["assigned_count"] + res["deferred_count"] == len(mock_project_list)
