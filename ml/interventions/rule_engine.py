"""
LandPulse AI — Intervention Rule Engine (Phase 4)
===================================================
Transparent rule engine mapping:
    Risk Signal → Risk Driver → Affected Stage → Candidate Intervention → Priority Score

DESIGN PRINCIPLE:
  Rules are explicit data structures — not hidden in frontend logic.
  Every rule is auditable and references real data signals.

Pipeline:
  1. Receive stage risk fingerprint from Phase 3 Stage Risk Engine
  2. Receive anomaly score + SHAP contributors
  3. Apply eligibility rules from catalog
  4. Return ranked list of candidate interventions with priority scores
"""

import logging
from typing import Any, Dict, List, Optional

from ml.interventions.catalog import INTERVENTION_CATALOG, CATALOG_METADATA
from ml.interventions.priority_scorer import compute_priority_score

log = logging.getLogger(__name__)

# ─── Rule Definitions ─────────────────────────────────────────────────────────
# Each rule maps a stage+signal condition to a set of candidate intervention IDs.
# Rules are stored here — not buried in frontend or service code.

INTERVENTION_RULES: List[Dict[str, Any]] = [
    # ── NOTIFICATION rules ───────────────────────────────────────────────────
    {
        "rule_id": "RULE-N001",
        "description": "Notification interval exceeds population median (194d) — escalate 3D publication",
        "stage": "NOTIFICATION",
        "trigger_condition": lambda stage_risks, features: (
            _get_stage_risk(stage_risks, "NOTIFICATION") >= 0.50
            and features.get("has_3a_notification", False)
            and not features.get("has_3d_notification", False)
        ),
        "candidate_interventions": ["NOTIF-001"],
        "risk_driver": "High notification interval duration (proxy: 3A→3D gap)",
        "data_basis": "BhoomiRashi 3A/3D notification dates — REAL SIGNAL",
    },
    {
        "rule_id": "RULE-N002",
        "description": "3A notification not yet issued — review pipeline entry",
        "stage": "NOTIFICATION",
        "trigger_condition": lambda stage_risks, features: (
            not features.get("has_3a_notification", True)
        ),
        "candidate_interventions": ["NOTIF-002"],
        "risk_driver": "Missing 3A notification (project may not have entered acquisition pipeline)",
        "data_basis": "BhoomiRashi project status data — REAL SIGNAL",
    },
    {
        "rule_id": "RULE-N003",
        "description": "Notification stage CRITICAL — both notification interventions apply",
        "stage": "NOTIFICATION",
        "trigger_condition": lambda stage_risks, features: (
            _get_stage_risk(stage_risks, "NOTIFICATION") >= 0.80
        ),
        "candidate_interventions": ["NOTIF-001", "NOTIF-002"],
        "risk_driver": "Critical notification delay signal",
        "data_basis": "BhoomiRashi notification interval — REAL SIGNAL",
    },

    # ── COMPENSATION rules ───────────────────────────────────────────────────
    {
        "rule_id": "RULE-C001",
        "description": "High compensation risk with large family count — prioritize disbursement review",
        "stage": "COMPENSATION",
        "trigger_condition": lambda stage_risks, features: (
            _get_stage_risk(stage_risks, "COMPENSATION") >= 0.55
            and (features.get("total_affected_families") or 0) > 0
        ),
        "candidate_interventions": ["COMP-001"],
        "risk_driver": "High compensation stage risk (proxy: cost intensity + family count)",
        "data_basis": "Proxy — DataGov.in delay patterns + BhoomiRashi cost data",
    },
    {
        "rule_id": "RULE-C002",
        "description": "High cost per ha in high-risk state — escalate valuation dispute review",
        "stage": "COMPENSATION",
        "trigger_condition": lambda stage_risks, features: (
            (features.get("cost_per_ha") or 0) > 1.2
            and features.get("state_code", "XX") in ["MH", "KA", "TN", "WB", "DL"]
        ),
        "candidate_interventions": ["COMP-002"],
        "risk_driver": "Cost intensity above population p75 in high-risk state",
        "data_basis": "BhoomiRashi cost data (p75=1.2 Cr/ha) + DataGov delay state patterns",
    },

    # ── LEGAL / OBJECTION rules ───────────────────────────────────────────────
    {
        "rule_id": "RULE-L001",
        "description": "Objection risk elevated — review outstanding 3C hearings",
        "stage": "OBJECTION",
        "trigger_condition": lambda stage_risks, features: (
            _get_stage_risk(stage_risks, "OBJECTION") >= 0.50
        ),
        "candidate_interventions": ["LEGAL-001"],
        "risk_driver": "Elevated objection risk (proxy: cost intensity + state contestation profile)",
        "data_basis": "Proxy — BhoomiRashi cost_per_ha + DataGov state delay patterns",
    },

    # ── AWARD / DOCUMENTATION rules ───────────────────────────────────────────
    {
        "rule_id": "RULE-D001",
        "description": "Large project area — award documentation complexity elevated",
        "stage": "AWARD",
        "trigger_condition": lambda stage_risks, features: (
            _get_stage_risk(stage_risks, "AWARD") >= 0.50
            or (features.get("land_required_ha") or 0) > 135
        ),
        "candidate_interventions": ["DOC-001"],
        "risk_driver": "High award stage risk (proxy: land area above population median 135ha)",
        "data_basis": "BhoomiRashi land area data (population median=135ha)",
    },

    # ── R&R rules ────────────────────────────────────────────────────────────
    {
        "rule_id": "RULE-R001",
        "description": "High R&R risk with displaced families — prioritize entitlement review",
        "stage": "RR",
        "trigger_condition": lambda stage_risks, features: (
            _get_stage_risk(stage_risks, "RR") >= 0.50
            and (features.get("total_affected_families") or 0) > 100
        ),
        "candidate_interventions": ["RR-001"],
        "risk_driver": "High R&R stage risk (proxy: family count + state R&R profile)",
        "data_basis": "Proxy — DataGov.in R&R delay patterns (WB, BR, MH high-risk states)",
    },
    {
        "rule_id": "RULE-R002",
        "description": "Large displacement (>500 families) — accelerate resettlement colony allotment",
        "stage": "RR",
        "trigger_condition": lambda stage_risks, features: (
            (features.get("total_affected_families") or 0) > 500
            and _get_stage_risk(stage_risks, "RR") >= 0.60
        ),
        "candidate_interventions": ["RR-002"],
        "risk_driver": "Large-scale displacement requiring dedicated resettlement colony review",
        "data_basis": "Proxy — DataGov.in large R&R displacement records",
    },
]


# ─── Helper ───────────────────────────────────────────────────────────────────

def _get_stage_risk(stage_risks: List[Dict[str, Any]], stage_id: str) -> float:
    """Extract risk score for a specific stage from the stage fingerprint list."""
    for s in stage_risks:
        if s.get("stage_id") == stage_id:
            return float(s.get("risk") or 0.0)
    return 0.0


def _get_intervention_by_id(intervention_id: str) -> Optional[Dict[str, Any]]:
    """Fetch intervention definition from the catalog."""
    for item in INTERVENTION_CATALOG:
        if item["intervention_id"] == intervention_id:
            return item
    return None


# ─── Rule Engine Entry Point ──────────────────────────────────────────────────

def map_risks_to_interventions(
    stage_risks: List[Dict[str, Any]],
    anomaly_score: Optional[float],
    shap_contributors: List[Dict[str, Any]],
    project_features: Dict[str, Any],
    data_completeness_pct: float = 100.0,
) -> Dict[str, Any]:
    """
    Apply rule engine: map stage risk signals → candidate interventions.

    Parameters
    ----------
    stage_risks : list of stage dicts from Stage Risk Engine
    anomaly_score : float from IsolationForest [0,1]
    shap_contributors : list of SHAP feature contributions
    project_features : dict of project feature values
    data_completeness_pct : float, data quality metric

    Returns
    -------
    dict with:
        - candidate_interventions: list of intervention dicts with priority scores
        - rules_fired: list of matched rules
        - input_signals_summary: summary of input signals used
        - methodology_note: non-causal disclaimer
    """
    if data_completeness_pct < 50.0:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": (
                "Intervention simulation unavailable — insufficient verified data. "
                f"Data completeness: {data_completeness_pct:.1f}%."
            ),
            "candidate_interventions": [],
            "rules_fired": [],
        }

    matched_intervention_ids: set = set()
    rules_fired: List[Dict[str, Any]] = []

    # Evaluate each rule
    for rule in INTERVENTION_RULES:
        try:
            triggered = rule["trigger_condition"](stage_risks, project_features)
            if triggered:
                rules_fired.append({
                    "rule_id": rule["rule_id"],
                    "description": rule["description"],
                    "stage": rule["stage"],
                    "risk_driver": rule["risk_driver"],
                    "data_basis": rule["data_basis"],
                    "interventions_triggered": rule["candidate_interventions"],
                })
                for iid in rule["candidate_interventions"]:
                    matched_intervention_ids.add(iid)
        except Exception as e:
            log.warning("Rule %s evaluation error: %s", rule["rule_id"], e)

    # Build scored intervention list
    candidate_interventions = []
    for iid in matched_intervention_ids:
        item = _get_intervention_by_id(iid)
        if item is None:
            continue

        # Find rules that triggered this intervention
        triggering_rules = [
            r for r in rules_fired if iid in r["interventions_triggered"]
        ]

        # Get stage risk for this intervention's stage
        stage_risk = _get_stage_risk(stage_risks, item["stage"])

        # Compute priority score
        priority_result = compute_priority_score(
            risk_severity=anomaly_score or stage_risk,
            stage_risk=stage_risk,
            urgency=item["urgency"],
            potential_impact=_estimate_impact(item, project_features),
            feasibility=item["implementation_feasibility"],
            data_confidence=_confidence_to_float(item["confidence"]),
            data_completeness_pct=data_completeness_pct,
        )

        # Connect SHAP contributors to this intervention
        shap_connections = _connect_shap_to_intervention(
            item["applicable_risk_factors"], shap_contributors
        )

        candidate_interventions.append({
            "intervention_id": item["intervention_id"],
            "category": item["category"],
            "stage": item["stage"],
            "display_name": item["display_name"],
            "action_description": item["action_description"],
            "urgency": item["urgency"],
            "confidence": item["confidence"],
            "evidence": item["evidence"],
            "provenance": item["provenance"],
            "non_causal_note": item["non_causal_note"],
            "priority_score": priority_result["priority_score"],
            "priority_label": priority_result["priority_label"],
            "score_components": priority_result["score_components"],
            "stage_risk": stage_risk,
            "triggering_rules": [r["rule_id"] for r in triggering_rules],
            "risk_drivers": [r["risk_driver"] for r in triggering_rules],
            "model_supported_contributors": shap_connections,
            "recommendation_type": "RULE_BASED",
            "output_label": "Rule-based recommendation",
        })

    # Sort by priority score descending
    candidate_interventions.sort(key=lambda x: x["priority_score"], reverse=True)

    # Overall input signal summary
    overall_stage_risk = max(
        (_get_stage_risk(stage_risks, s["stage_id"]) for s in stage_risks),
        default=0.0,
    )

    return {
        "status": "AVAILABLE",
        "candidate_interventions": candidate_interventions,
        "top_intervention": candidate_interventions[0] if candidate_interventions else None,
        "rules_fired": rules_fired,
        "total_rules_evaluated": len(INTERVENTION_RULES),
        "total_interventions_matched": len(candidate_interventions),
        "input_signals_summary": {
            "anomaly_score": anomaly_score,
            "overall_stage_risk": round(overall_stage_risk, 4),
            "stage_risks": {
                s["stage_id"]: s.get("risk") for s in stage_risks
            },
            "data_completeness_pct": data_completeness_pct,
        },
        "methodology_note": (
            "Interventions are RULE-BASED DECISION-SUPPORT SUGGESTIONS. "
            "They are mapped from real risk signals in the Phase 3 Stage Risk Engine "
            "using explicit, auditable rules. They are NOT causal predictions and do NOT "
            "guarantee that acting on them will prevent project delay."
        ),
        "catalog_version": CATALOG_METADATA["catalog_version"],
    }


def _estimate_impact(
    intervention: Dict[str, Any],
    features: Dict[str, Any],
) -> float:
    """
    Estimate the potential scope/impact of an intervention.
    Based on: affected families, land area, cost intensity.
    Returns float [0.0, 1.0].
    """
    families = features.get("total_affected_families") or 0
    land_ha = features.get("land_required_ha") or 0
    cost = features.get("cost_per_ha") or 0

    # Normalize to [0, 1] using population benchmarks
    family_score = min(families / 2000.0, 1.0)   # 2000 families → max impact
    area_score = min(land_ha / 280.0, 1.0)        # 280ha = BhoomiRashi p95
    cost_score = min(cost / 3.5, 1.0)             # 3.5 Cr/ha = BhoomiRashi p95

    # Stage-specific impact weighting
    stage = intervention["stage"]
    if stage == "COMPENSATION":
        return round(0.5 * family_score + 0.3 * cost_score + 0.2 * area_score, 4)
    elif stage == "RR":
        return round(0.7 * family_score + 0.2 * area_score + 0.1 * cost_score, 4)
    elif stage in ("NOTIFICATION", "AWARD"):
        return round(0.4 * area_score + 0.3 * cost_score + 0.3 * family_score, 4)
    elif stage == "OBJECTION":
        return round(0.5 * cost_score + 0.3 * area_score + 0.2 * family_score, 4)
    else:
        return round(0.33 * family_score + 0.33 * area_score + 0.33 * cost_score, 4)


def _confidence_to_float(confidence: str) -> float:
    """Convert confidence label to numeric weight."""
    mapping = {"HIGH": 0.90, "MEDIUM": 0.65, "LOW": 0.40}
    return mapping.get(confidence.upper(), 0.50)


def _connect_shap_to_intervention(
    applicable_features: List[str],
    shap_contributors: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Find SHAP contributors that overlap with this intervention's applicable features.
    Returns the matching SHAP entries for display — clearly labeled as
    'Model-supported risk contributor' (NOT intervention cause).
    """
    connections = []
    for contrib in shap_contributors:
        feature_name = contrib.get("raw_feature", contrib.get("factor", ""))
        if any(
            af.replace("_", "").lower() in feature_name.replace("_", "").lower()
            or feature_name.replace("_", "").lower() in af.replace("_", "").lower()
            for af in applicable_features
        ):
            connections.append({
                "factor": contrib.get("factor", feature_name),
                "contribution": contrib.get("contribution", 0),
                "direction": contrib.get("direction", "UNKNOWN"),
                "contributor_label": "Model-supported risk contributor",
                "causal_warning": (
                    "This is a SHAP feature contribution — it reflects the model's "
                    "anomaly scoring, NOT a causal explanation of delay."
                ),
            })
    return connections


# ─── Rule Catalog Export ──────────────────────────────────────────────────────

def get_rule_definitions() -> List[Dict[str, Any]]:
    """Return auditable rule definitions (without lambda functions)."""
    return [
        {
            "rule_id": r["rule_id"],
            "description": r["description"],
            "stage": r["stage"],
            "risk_driver": r["risk_driver"],
            "data_basis": r["data_basis"],
            "candidate_interventions": r["candidate_interventions"],
        }
        for r in INTERVENTION_RULES
    ]
