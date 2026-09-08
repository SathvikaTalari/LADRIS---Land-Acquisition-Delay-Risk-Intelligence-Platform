"""
LandPulse AI — Intervention Priority Scorer (Phase 4)
======================================================
Computes a transparent, explainable "Decision-Support Priority Score" (0–100)
for each candidate intervention.

IMPORTANT LABELING:
  The output is labeled "Decision-Support Priority Score" — NOT a scientifically
  validated causal optimization score. Individual components are always exposed
  so officers can understand exactly why an intervention ranked highly.

Formula:
  raw = (risk_severity × w_risk)
      + (urgency × w_urgency)
      + (potential_impact × w_impact)
      + (feasibility × w_feasibility)
      + (data_confidence × w_confidence)

  priority_score = clip(raw × 100, 0, 100)

Weights (sum to 1.0):
  w_risk        = 0.30  — how severe is the underlying risk signal
  w_urgency     = 0.25  — how urgent is the intervention per catalog
  w_impact      = 0.20  — estimated scope/number of people affected
  w_feasibility = 0.15  — how actionable is the intervention
  w_confidence  = 0.10  — data quality backing the recommendation

Each component is individually returned for full transparency.
"""

import logging
from typing import Any, Dict

import numpy as np

log = logging.getLogger(__name__)

# ─── Priority Score Weights ────────────────────────────────────────────────────
# These are EXPLICITLY documented. If weights are changed in future,
# the change must be reflected in docs/intervention-engine.md.

PRIORITY_WEIGHTS = {
    "risk_severity": 0.35,
    "urgency": 0.20,
    "potential_impact": 0.15,
    "risk_velocity": 0.10,
    "feasibility": 0.10,
    "data_confidence": 0.10,
}

assert abs(sum(PRIORITY_WEIGHTS.values()) - 1.0) < 1e-9, (
    "Priority weights must sum to 1.0"
)

PRIORITY_SCORE_LABEL = "Decision-Support Priority Score"
PRIORITY_SCORE_NOTE = (
    "This score is a transparent, rule-based decision-support tool. "
    "It is computed from measurable inputs: current risk severity (35%), urgency (20%), "
    "estimated impact (15%), risk velocity (10%), actionability (10%), and data confidence (10%). "
    "Projects with rapidly rising risk velocity receive higher priority rankings. "
    "It is NOT a scientifically validated causal optimization score."
)


def compute_priority_score(
    risk_severity: float,
    stage_risk: float,
    urgency: float,
    potential_impact: float,
    feasibility: float,
    data_confidence: float,
    data_completeness_pct: float = 100.0,
    risk_velocity_score: float = 0.5,
) -> Dict[str, Any]:
    """
    Compute Decision-Support Priority Score for one intervention/project.
    """
    # Clamp all inputs
    risk_sev = float(np.clip(risk_severity, 0.0, 1.0))
    stage_r = float(np.clip(stage_risk, 0.0, 1.0))
    urg = float(np.clip(urgency, 0.0, 1.0))
    impact = float(np.clip(potential_impact, 0.0, 1.0))
    vel_score = float(np.clip(risk_velocity_score, 0.0, 1.0))
    feas = float(np.clip(feasibility, 0.0, 1.0))
    conf = float(np.clip(data_confidence, 0.0, 1.0))

    # Use max(anomaly_score, stage_risk) as effective risk severity
    effective_risk = max(risk_sev, stage_r)

    # Apply data completeness penalty (projects with < 75% data lose up to 20% score)
    completeness_factor = 1.0
    if data_completeness_pct < 75.0:
        completeness_factor = 0.80 + 0.20 * (data_completeness_pct / 75.0)

    # Weighted sum
    raw = (
        PRIORITY_WEIGHTS["risk_severity"] * effective_risk
        + PRIORITY_WEIGHTS["urgency"] * urg
        + PRIORITY_WEIGHTS["potential_impact"] * impact
        + PRIORITY_WEIGHTS["risk_velocity"] * vel_score
        + PRIORITY_WEIGHTS["feasibility"] * feas
        + PRIORITY_WEIGHTS["data_confidence"] * conf
    ) * completeness_factor

    # Normalize to 0–100 integer
    priority_score = int(round(float(np.clip(raw * 100.0, 0.0, 100.0))))

    # Priority label bands
    if priority_score >= 80:
        priority_label = "CRITICAL PRIORITY"
    elif priority_score >= 65:
        priority_label = "HIGH PRIORITY"
    elif priority_score >= 45:
        priority_label = "MEDIUM PRIORITY"
    else:
        priority_label = "LOW PRIORITY"

    return {
        "priority_score": priority_score,
        "priority_label": priority_label,
        "priority_score_label": PRIORITY_SCORE_LABEL,
        "score_components": {
            "risk_severity": {
                "value": round(effective_risk, 4),
                "weight": PRIORITY_WEIGHTS["risk_severity"],
                "weighted_contribution": round(PRIORITY_WEIGHTS["risk_severity"] * effective_risk * 100, 1),
                "label": "Risk Severity (35%)",
                "description": "Combined anomaly/stage risk signal from ML pipeline",
            },
            "urgency": {
                "value": round(urg, 4),
                "weight": PRIORITY_WEIGHTS["urgency"],
                "weighted_contribution": round(PRIORITY_WEIGHTS["urgency"] * urg * 100, 1),
                "label": "Stage Urgency (20%)",
                "description": "Intervention urgency weight from structured catalog",
            },
            "potential_impact": {
                "value": round(impact, 4),
                "weight": PRIORITY_WEIGHTS["potential_impact"],
                "weighted_contribution": round(PRIORITY_WEIGHTS["potential_impact"] * impact * 100, 1),
                "label": "Potential Scope / Impact (15%)",
                "description": "Estimated number of families/hectares affected",
            },
            "risk_velocity": {
                "value": round(vel_score, 4),
                "weight": PRIORITY_WEIGHTS["risk_velocity"],
                "weighted_contribution": round(PRIORITY_WEIGHTS["risk_velocity"] * vel_score * 100, 1),
                "label": "Risk Velocity (10%)",
                "description": "Rate of risk escalation over 7 days (Rapidly Rising gives higher priority)",
            },
            "feasibility": {
                "value": round(feas, 4),
                "weight": PRIORITY_WEIGHTS["feasibility"],
                "weighted_contribution": round(PRIORITY_WEIGHTS["feasibility"] * feas * 100, 1),
                "label": "Implementation Feasibility (10%)",
                "description": "Catalog-defined actionability of the intervention",
            },
            "data_confidence": {
                "value": round(conf, 4),
                "weight": PRIORITY_WEIGHTS["data_confidence"],
                "weighted_contribution": round(PRIORITY_WEIGHTS["data_confidence"] * conf * 100, 1),
                "label": "Data Confidence (10%)",
                "description": "Quality of data backing this recommendation",
            },
        },
        "completeness_penalty_applied": completeness_factor < 1.0,
        "data_completeness_pct": data_completeness_pct,
        "weights": PRIORITY_WEIGHTS,
        "scoring_note": PRIORITY_SCORE_NOTE,
    }

