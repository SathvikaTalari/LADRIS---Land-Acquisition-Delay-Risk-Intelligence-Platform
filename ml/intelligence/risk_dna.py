"""
LandPulse AI — Risk DNA Composer (Phase 7)
===========================================
Combines existing intelligence signals into a structured Risk DNA profile.

WHAT THIS IS:
  A composite multi-dimensional risk profile assembled from real existing
  signals. Not a new ML model. No new training.

OUTPUT TYPE LABELS (per government transparency standard):
  - anomaly_score: C (ML/Model Signal — IsolationForest)
  - stage_fingerprint_risk: C (ML/Model Signal — Stage Risk Engine)
  - shap_top_driver: C (ML/Model Signal — SHAP attribution)
  - data_completeness: A (Derived from Official Source Data fields)
  - temporal_observation_count: A (Real logged prediction count)
  - reliability_assessment: B (Derived Analytics)
  - dna_composite: D (Decision-Support aggregation)

IMPORTANT LABELING:
  Risk DNA is an AGGREGATED DECISION-SUPPORT PROFILE.
  It is NOT a new prediction model.
  It does NOT claim causal linkage between any dimension and actual delay.
  Every component is individually labeled with its source type.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

DNA_DISCLAIMER = (
    "Risk DNA is a multi-dimensional decision-support profile assembled from "
    "existing intelligence signals. It is NOT a new ML model or a delay prediction. "
    "Each dimension is independently labeled with its evidence type. "
    "The composite DNA score is a weighted aggregation for decision-support only — "
    "NOT a calibrated probability of project failure or delay."
)

# DNA component weights (must sum to 1.0)
# Weights are EXPLICITLY documented for auditability
DNA_WEIGHTS = {
    "anomaly_signal": 0.30,          # IsolationForest structural anomaly
    "stage_fingerprint": 0.30,       # Peak stage risk across 6 stages
    "data_completeness": 0.15,       # How complete the project data is
    "shap_driver_severity": 0.15,    # Severity of top SHAP contributor
    "reliability_penalty": 0.10,     # Inverted OOD/low-confidence penalty
}

assert abs(sum(DNA_WEIGHTS.values()) - 1.0) < 1e-9, "DNA weights must sum to 1.0"

# Stage coverage labels for provenance transparency
STAGE_COVERAGE = {
    "NOTIFICATION": "REAL_SIGNAL",
    "OBJECTION": "PROXY",
    "AWARD": "PROXY",
    "COMPENSATION": "PROXY",
    "RR": "PROXY",
    "POSSESSION": "PROXY (upstream cascade)",
}


def compose_risk_dna(
    project_id: str,
    anomaly_result: Dict[str, Any],
    stage_fingerprint: Dict[str, Any],
    shap_explanation: Optional[Dict[str, Any]],
    prediction_confidence: Optional[Dict[str, Any]],
    temporal_observations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compose the Risk DNA profile for a project.

    Parameters
    ----------
    project_id : str
    anomaly_result : dict
        Output of get_prediction_for_project() — contains anomaly_risk.score
    stage_fingerprint : dict
        Output of get_stage_risk_for_project() — contains stages + overall_fingerprint_risk
    shap_explanation : dict or None
        Output of get_explanation_for_project()
    prediction_confidence : dict or None
        Output of get_prediction_confidence()
    temporal_observations : list or None
        Real timestamped observations from monitoring log (may be empty)

    Returns
    -------
    dict with full Risk DNA profile
    """
    # ── Extract anomaly signal ────────────────────────────────────────────────
    anomaly_score = 0.5  # Safe default
    anomaly_risk_level = "UNKNOWN"
    anomaly_available = False

    if anomaly_result and anomaly_result.get("prediction_status") == "AVAILABLE":
        ar = anomaly_result.get("anomaly_risk") or {}
        score_val = ar.get("score")
        if score_val is not None:
            anomaly_score = float(score_val)
            anomaly_risk_level = ar.get("risk_level", "UNKNOWN")
            anomaly_available = True

    # ── Extract stage fingerprint ─────────────────────────────────────────────
    stage_risk = 0.5  # Safe default
    peak_stage = None
    peak_stage_value = None
    stage_details = []
    stage_available = False

    if stage_fingerprint and stage_fingerprint.get("stages"):
        overall = stage_fingerprint.get("overall_fingerprint_risk")
        if overall is not None:
            stage_risk = float(overall)
            stage_available = True
        peak_stage = stage_fingerprint.get("peak_risk_stage")
        peak_stage_value = stage_fingerprint.get("peak_risk_value")
        stage_details = [
            {
                "stage_id": s.get("stage_id"),
                "risk": s.get("risk"),
                "risk_level": s.get("risk_level"),
                "data_basis": s.get("data_basis", "PROXY"),
                "data_completeness": s.get("data_completeness"),
                "coverage": STAGE_COVERAGE.get(s.get("stage_id", ""), "PROXY"),
            }
            for s in stage_fingerprint.get("stages", [])
            if s.get("eligible") and s.get("risk") is not None
        ]

    # ── Extract SHAP driver severity ──────────────────────────────────────────
    top_driver_name = None
    top_driver_contribution = 0.0
    shap_driver_severity = 0.5  # Neutral default when unavailable

    if shap_explanation:
        pos_contributors = shap_explanation.get("top_positive_contributors") or []
        if pos_contributors:
            top = pos_contributors[0]
            top_driver_name = top.get("display_name") or top.get("feature", "")
            top_contribution = abs(top.get("shap_contribution", 0.0))
            top_driver_contribution = round(top_contribution, 4)
            # Map contribution magnitude to [0,1] severity
            # Typical SHAP magnitude range in our model: 0 to ~0.3
            shap_driver_severity = float(np.clip(top_contribution / 0.3, 0.0, 1.0))

    # ── Extract data completeness ─────────────────────────────────────────────
    completeness_pct = 100.0
    if anomaly_result:
        completeness_pct = float(anomaly_result.get("data_completeness_pct") or 100.0)
    completeness_score = completeness_pct / 100.0  # [0,1]

    # ── Extract reliability / OOD penalty ────────────────────────────────────
    reliability_score = 0.75  # Default: medium reliability
    confidence_assessment = "MEDIUM"
    is_ood = False
    ood_details = {}

    if prediction_confidence:
        conf = prediction_confidence.get("confidence_assessment", "MEDIUM")
        confidence_assessment = conf
        ood = prediction_confidence.get("out_of_distribution") or {}
        is_ood = ood.get("is_ood", False)
        ood_details = ood

        # Higher reliability = lower OOD penalty
        if conf == "HIGH":
            reliability_score = 0.90
        elif conf == "MEDIUM":
            reliability_score = 0.65
        else:
            reliability_score = 0.40

    # Inverted reliability penalty: low confidence → penalty reduces composite score
    reliability_component = reliability_score  # Used as-is in weighted sum

    # ── Temporal observations ─────────────────────────────────────────────────
    obs_list = temporal_observations or []
    obs_count = len(obs_list)
    temporal_available = obs_count > 0

    # Detect risk trend from real observations (if ≥ 2 exist)
    risk_trend = None
    risk_trend_label = "INSUFFICIENT_DATA"
    if len(obs_list) >= 2:
        # Sort by timestamp
        sorted_obs = sorted(
            obs_list,
            key=lambda x: x.get("timestamp", ""),
        )
        first_score = sorted_obs[0].get("anomaly_score", 0.0) or 0.0
        last_score = sorted_obs[-1].get("anomaly_score", 0.0) or 0.0
        delta = last_score - first_score
        risk_trend = round(delta, 4)
        if delta > 0.05:
            risk_trend_label = "ESCALATING"
        elif delta < -0.05:
            risk_trend_label = "DE_ESCALATING"
        else:
            risk_trend_label = "STABLE"

    # ── Compose DNA score ─────────────────────────────────────────────────────
    dna_raw = (
        DNA_WEIGHTS["anomaly_signal"] * anomaly_score
        + DNA_WEIGHTS["stage_fingerprint"] * stage_risk
        + DNA_WEIGHTS["data_completeness"] * (1.0 - completeness_score)  # Incomplete data = higher DNA risk
        + DNA_WEIGHTS["shap_driver_severity"] * shap_driver_severity
        + DNA_WEIGHTS["reliability_penalty"] * (1.0 - reliability_component)
    )
    dna_composite = round(float(np.clip(dna_raw, 0.0, 1.0)), 4)

    # DNA risk tier
    if dna_composite >= 0.75:
        dna_tier = "CRITICAL"
    elif dna_composite >= 0.55:
        dna_tier = "HIGH"
    elif dna_composite >= 0.35:
        dna_tier = "MEDIUM"
    else:
        dna_tier = "LOW"

    # ── Assemble Risk DNA profile ─────────────────────────────────────────────
    return {
        "project_id": project_id,
        "output_type": "RISK_DNA",
        "output_label": "Decision-Support Risk Profile",
        "dna_composite_score": dna_composite,
        "dna_tier": dna_tier,
        "disclaimer": DNA_DISCLAIMER,

        # ── DNA Dimensions ────────────────────────────────────────────────────
        "dimensions": {
            "anomaly_signal": {
                "score": round(anomaly_score, 4),
                "risk_level": anomaly_risk_level,
                "weight": DNA_WEIGHTS["anomaly_signal"],
                "contribution": round(DNA_WEIGHTS["anomaly_signal"] * anomaly_score * 100, 1),
                "available": anomaly_available,
                "output_type": "C",
                "output_type_label": "ML/Model Signal — IsolationForest Anomaly Score",
                "description": (
                    "Structural unusualness relative to BhoomiRashi national population. "
                    "HIGH anomaly ≠ delayed project."
                ),
            },
            "stage_fingerprint": {
                "score": round(stage_risk, 4),
                "peak_stage": peak_stage,
                "peak_stage_value": round(peak_stage_value, 4) if peak_stage_value is not None else None,
                "stage_details": stage_details,
                "weight": DNA_WEIGHTS["stage_fingerprint"],
                "contribution": round(DNA_WEIGHTS["stage_fingerprint"] * stage_risk * 100, 1),
                "available": stage_available,
                "output_type": "C",
                "output_type_label": "ML/Model Signal — Stage Risk Fingerprint (6 acquisition stages)",
                "description": (
                    "Stage-by-stage risk across the NH Act / RFCTLARR acquisition lifecycle. "
                    "NOTIFICATION stage uses real BhoomiRashi temporal data. "
                    "Other stages use proxy signals."
                ),
            },
            "data_completeness": {
                "score": round(completeness_score, 4),
                "completeness_pct": completeness_pct,
                "risk_contribution": round(DNA_WEIGHTS["data_completeness"] * (1.0 - completeness_score) * 100, 1),
                "weight": DNA_WEIGHTS["data_completeness"],
                "output_type": "A",
                "output_type_label": "Derived from Official Source Data — field availability check",
                "description": (
                    "How complete the project's data record is. Incomplete data increases uncertainty."
                ),
            },
            "shap_driver_severity": {
                "score": round(shap_driver_severity, 4),
                "top_driver_name": top_driver_name,
                "top_driver_contribution": top_driver_contribution,
                "weight": DNA_WEIGHTS["shap_driver_severity"],
                "contribution": round(DNA_WEIGHTS["shap_driver_severity"] * shap_driver_severity * 100, 1),
                "output_type": "C",
                "output_type_label": "ML/Model Signal — SHAP Feature Attribution",
                "description": (
                    "Severity of the dominant SHAP contributor to the anomaly score. "
                    "High value = one feature is disproportionately driving the anomaly signal."
                ),
            },
            "reliability": {
                "score": round(reliability_component, 4),
                "confidence_assessment": confidence_assessment,
                "is_out_of_distribution": is_ood,
                "ood_details": ood_details,
                "weight": DNA_WEIGHTS["reliability_penalty"],
                "risk_contribution": round(DNA_WEIGHTS["reliability_penalty"] * (1.0 - reliability_component) * 100, 1),
                "output_type": "B",
                "output_type_label": "Derived Analytics — Prediction Reliability Assessment",
                "description": (
                    "How reliable the ML prediction is given this project's characteristics. "
                    "Out-of-distribution projects receive a low-reliability flag."
                ),
            },
        },

        # ── Temporal Intelligence ─────────────────────────────────────────────
        "temporal": {
            "observations_available": temporal_available,
            "observation_count": obs_count,
            "observations": obs_list[:50],  # Cap at 50 for payload size
            "risk_trend": risk_trend,
            "risk_trend_label": risk_trend_label,
            "temporal_disclaimer": (
                "Risk history is derived ONLY from real logged prediction observations. "
                "Observations are created when the project detail page is accessed via the API. "
                "No historical points are fabricated or inferred."
                if temporal_available else
                "No temporal observation history available for this project yet. "
                "History will accumulate as the system processes future API requests. "
                "Check back after the project has been assessed multiple times."
            ),
            "output_type": "A",
            "output_type_label": "Official Source Data — real logged prediction timestamps",
        },

        # ── Metadata ──────────────────────────────────────────────────────────
        "weights": DNA_WEIGHTS,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "anomaly_model": "IsolationForest v1.0-anomaly — trained on BhoomiRashi public data (56 records)",
            "stage_engine": "Stage Risk Engine — 1 real signal (NOTIFICATION) + 5 proxy signals",
            "shap": "SHAP TreeExplainer on IsolationForest",
            "data_source": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE + DATAGOV_DELAYED_PROJECTS",
        },
    }
