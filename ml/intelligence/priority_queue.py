"""
LandPulse AI — Cross-Project Priority Queue (Phase 7)
======================================================
Extends the existing Phase 4 Priority Scorer to rank ALL projects in
a cross-project priority queue for resource allocation decisions.

ALGORITHM:
  1. Score each project using existing compute_priority_score() from Phase 4
  2. Apply bottleneck signal modifier (+5 points if in high-bottleneck cluster)
  3. Apply comparable-project context signal
  4. Rank by composite score descending
  5. Optional: resource-constrained greedy allocation (simulation only)

IMPORTANT LABELING:
  - Output is a "Decision-Support Priority Queue" — NOT operational orders
  - Resource scenario is labeled "DECISION-SUPPORT SIMULATION"
  - Every output shows the scoring formula and all component weights

OUTPUT TYPE: D (Decision-Support Recommendations)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

QUEUE_DISCLAIMER = (
    "The Cross-Project Priority Queue is a DECISION-SUPPORT tool. "
    "Rankings are computed using a transparent, rule-based scoring formula "
    "that combines risk severity, urgency, estimated impact, feasibility, "
    "and data confidence. Rankings are NOT operational orders. "
    "Human officers must exercise judgment and verify conditions on the ground "
    "before taking any action."
)

SCENARIO_DISCLAIMER = (
    "Resource scenario output is a DECISION-SUPPORT SIMULATION. "
    "It uses a greedy allocation algorithm to suggest project prioritization "
    "given constrained resource capacity. "
    "This is a hypothetical scenario estimate — NOT an actual government resource allocation. "
    "Results depend on the priority scores computed from available data and "
    "are subject to all existing data limitations."
)

# Extended weights for Phase 7 (builds on Phase 4 formula)
QUEUE_WEIGHTS = {
    "base_priority_score": 0.70,     # Phase 4 priority score (0-100)
    "bottleneck_modifier": 0.15,     # Bottleneck cluster signal
    "comparable_context": 0.10,      # Whether comparables have high risk
    "data_freshness": 0.05,          # How recently assessed
}

assert abs(sum(QUEUE_WEIGHTS.values()) - 1.0) < 1e-9, "Queue weights must sum to 1.0"

# Resource type definitions
RESOURCE_TYPES = {
    "LEGAL": {
        "label": "Legal Officers / LA Collectors",
        "relevant_stages": ["NOTIFICATION", "OBJECTION", "AWARD"],
        "relevant_bottlenecks": ["NOTIFICATION", "OBJECTION"],
    },
    "COMPENSATION": {
        "label": "Compensation Disbursement Teams",
        "relevant_stages": ["COMPENSATION"],
        "relevant_bottlenecks": ["COMPENSATION"],
    },
    "RR": {
        "label": "R&R Officers / Social Workers",
        "relevant_stages": ["RR"],
        "relevant_bottlenecks": ["RR"],
    },
    "FIELD": {
        "label": "Field Survey / Possession Teams",
        "relevant_stages": ["POSSESSION"],
        "relevant_bottlenecks": ["MIXED"],
    },
}


def build_project_queue_entry(
    project: Dict[str, Any],
    anomaly_result: Dict[str, Any],
    stage_fingerprint: Dict[str, Any],
    prediction_confidence: Optional[Dict[str, Any]] = None,
    bottleneck_type: Optional[str] = None,
    comparable_risk_signal: float = 0.5,
) -> Dict[str, Any]:
    """
    Build a single priority queue entry for a project.

    Parameters
    ----------
    project : dict — project attributes
    anomaly_result : dict — ML service prediction result
    stage_fingerprint : dict — stage risk fingerprint
    prediction_confidence : dict or None
    bottleneck_type : str or None — identified bottleneck cluster type
    comparable_risk_signal : float [0,1] — mean risk of comparable projects

    Returns
    -------
    dict with priority queue entry
    """
    try:
        from ml.interventions.priority_scorer import compute_priority_score
    except ImportError:
        log.error("Could not import priority_scorer")
        return {}

    project_id = str(project.get("id") or project.get("project_id", ""))
    state_code = project.get("state_code", "UNKNOWN")

    # ── Extract risk severity ─────────────────────────────────────────────────
    anomaly_score = 0.5
    if anomaly_result and anomaly_result.get("prediction_status") == "AVAILABLE":
        ar = anomaly_result.get("anomaly_risk") or {}
        anomaly_score = float(ar.get("score") or 0.5)

    stage_risk = 0.5
    peak_stage = None
    if stage_fingerprint and stage_fingerprint.get("overall_fingerprint_risk") is not None:
        stage_risk = float(stage_fingerprint.get("overall_fingerprint_risk") or 0.5)
        peak_stage = stage_fingerprint.get("peak_risk_stage")

    risk_severity = max(anomaly_score, stage_risk)

    # ── Extract urgency (stage-based proxy) ───────────────────────────────────
    # Projects with high peak stage risk in time-sensitive stages get higher urgency
    STAGE_URGENCY = {
        "COMPENSATION": 0.80,
        "RR": 0.75,
        "NOTIFICATION": 0.70,
        "OBJECTION": 0.65,
        "POSSESSION": 0.85,
        "AWARD": 0.60,
    }
    urgency = STAGE_URGENCY.get(peak_stage, 0.60) if peak_stage else 0.55

    # Increase urgency for DELAYED status
    status = str(project.get("status", "")).upper()
    if status == "DELAYED":
        urgency = min(urgency + 0.15, 1.0)

    # ── Estimate potential impact ─────────────────────────────────────────────
    families = int(project.get("total_affected_families") or 0)
    area_ha = float(project.get("total_area_ha") or 0.0)

    # Impact: combination of families and land scale
    family_impact = float(np.clip(families / 2000.0, 0.0, 1.0))
    area_impact = float(np.clip(area_ha / 500.0, 0.0, 1.0))
    potential_impact = 0.6 * family_impact + 0.4 * area_impact

    # ── Implementation feasibility ────────────────────────────────────────────
    # Default: medium feasibility
    # Projects with more complete data are more actionable
    completeness_pct = float(
        (anomaly_result or {}).get("data_completeness_pct") or 75.0
    )
    feasibility = float(np.clip(completeness_pct / 100.0 * 0.8 + 0.2, 0.0, 1.0))

    # ── Data confidence ───────────────────────────────────────────────────────
    confidence_map = {"HIGH": 0.90, "MEDIUM": 0.65, "LOW": 0.40, "UNAVAILABLE": 0.30}
    conf_label = (prediction_confidence or {}).get("confidence_assessment", "MEDIUM")
    data_confidence = confidence_map.get(conf_label, 0.65)

    # ── Run Phase 4 priority scorer ───────────────────────────────────────────
    phase4_result = compute_priority_score(
        risk_severity=risk_severity,
        stage_risk=stage_risk,
        urgency=urgency,
        potential_impact=potential_impact,
        feasibility=feasibility,
        data_confidence=data_confidence,
        data_completeness_pct=completeness_pct,
    )
    base_score = float(phase4_result["priority_score"])  # 0-100

    # ── Bottleneck modifier ───────────────────────────────────────────────────
    # Projects in high-severity bottleneck clusters get a modifier
    BOTTLENECK_MODIFIERS = {
        "COMPENSATION": 5.0,
        "RR": 5.0,
        "NOTIFICATION": 3.0,
        "OBJECTION": 3.0,
        "MIXED": 2.0,
    }
    bottleneck_modifier = BOTTLENECK_MODIFIERS.get(bottleneck_type or "", 0.0)

    # ── Comparable risk signal ────────────────────────────────────────────────
    # If comparable projects have high anomaly scores, adds context
    comparable_modifier = comparable_risk_signal * 3.0  # Max 3 extra points

    # ── Composite queue score ─────────────────────────────────────────────────
    composite_score = float(np.clip(
        base_score + bottleneck_modifier + comparable_modifier,
        0.0,
        100.0,
    ))

    # Priority tier
    if composite_score >= 80:
        queue_tier = "CRITICAL"
    elif composite_score >= 65:
        queue_tier = "HIGH"
    elif composite_score >= 45:
        queue_tier = "MEDIUM"
    else:
        queue_tier = "LOW"

    # Recommended resource type based on bottleneck
    recommended_resource = None
    if bottleneck_type:
        for rtype, rdef in RESOURCE_TYPES.items():
            if bottleneck_type in rdef["relevant_bottlenecks"]:
                recommended_resource = {"type": rtype, "label": rdef["label"]}
                break

    return {
        "project_id": project_id,
        "project_code": project.get("project_code"),
        "project_name": project.get("name"),
        "state_code": state_code,
        "executing_agency": project.get("executing_agency"),
        "status": project.get("status"),
        "composite_priority_score": round(composite_score, 1),
        "queue_tier": queue_tier,
        "score_breakdown": {
            "base_priority_score": round(base_score, 1),
            "bottleneck_modifier": round(bottleneck_modifier, 1),
            "comparable_context_modifier": round(comparable_modifier, 1),
            "phase4_components": phase4_result.get("score_components"),
        },
        "risk_signals": {
            "anomaly_score": round(anomaly_score, 4),
            "stage_fingerprint_risk": round(stage_risk, 4),
            "peak_risk_stage": peak_stage,
            "effective_risk_severity": round(risk_severity, 4),
        },
        "bottleneck_type": bottleneck_type,
        "recommended_resource": recommended_resource,
        "data_completeness_pct": completeness_pct,
        "output_type": "D",
        "output_type_label": "Decision-Support Recommendation",
        "scoring_note": phase4_result.get("scoring_note"),
    }


def build_priority_queue(
    queue_entries: List[Dict[str, Any]],
    filter_state: Optional[str] = None,
    filter_agency: Optional[str] = None,
    filter_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sort and filter the priority queue entries.

    Parameters
    ----------
    queue_entries : list of dicts from build_project_queue_entry()
    filter_state : str or None — filter by state code
    filter_agency : str or None — filter by executing agency
    filter_tier : str or None — filter by queue tier (CRITICAL, HIGH, MEDIUM, LOW)

    Returns
    -------
    dict with sorted, filtered priority queue
    """
    entries = [e for e in queue_entries if e]  # Remove empty entries

    # Apply filters
    if filter_state:
        entries = [e for e in entries if (e.get("state_code") or "").upper() == filter_state.upper()]
    if filter_agency:
        entries = [e for e in entries if (e.get("executing_agency") or "").upper() == filter_agency.upper()]
    if filter_tier:
        entries = [e for e in entries if e.get("queue_tier") == filter_tier.upper()]

    # Sort by composite score descending
    entries.sort(key=lambda x: -(x.get("composite_priority_score") or 0))

    # Add rank
    for rank, entry in enumerate(entries, 1):
        entry["rank"] = rank

    # Tier summary
    tier_counts: Dict[str, int] = {}
    for e in entries:
        tier = e.get("queue_tier", "LOW")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    return {
        "output_type": "D",
        "output_type_label": "Decision-Support Priority Queue",
        "total_projects": len(entries),
        "tier_summary": tier_counts,
        "active_filters": {
            "state": filter_state,
            "agency": filter_agency,
            "tier": filter_tier,
        },
        "queue": entries,
        "queue_disclaimer": QUEUE_DISCLAIMER,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def run_resource_scenario(
    queue_entries: List[Dict[str, Any]],
    capacity_constraints: Dict[str, int],
) -> Dict[str, Any]:
    """
    Run a constrained resource allocation simulation using greedy assignment.

    Parameters
    ----------
    queue_entries : list — sorted priority queue entries
    capacity_constraints : dict — e.g. {"LEGAL": 3, "COMPENSATION": 2, "RR": 1}

    Returns
    -------
    dict with simulation results and assigned/deferred projects
    """
    if not queue_entries:
        return {
            "output_type": "E",
            "available": False,
            "reason": "No project queue entries available",
        }

    # Validate constraints
    for rtype, cap in capacity_constraints.items():
        if rtype not in RESOURCE_TYPES:
            return {
                "output_type": "E",
                "available": False,
                "reason": f"Unknown resource type: {rtype}. Valid types: {list(RESOURCE_TYPES.keys())}",
            }
        if not isinstance(cap, int) or cap < 0:
            return {
                "output_type": "E",
                "available": False,
                "reason": f"Capacity for {rtype} must be a non-negative integer",
            }

    total_capacity = sum(capacity_constraints.values())
    if total_capacity == 0:
        return {
            "output_type": "E",
            "available": False,
            "reason": "All resource capacities are 0. At least one resource type must have capacity > 0.",
        }

    # Greedy allocation: process projects in priority order
    remaining_capacity = dict(capacity_constraints)
    assigned = []
    deferred = []
    unmatched = []

    for entry in queue_entries:
        bottleneck = entry.get("bottleneck_type")
        recommended_resource = entry.get("recommended_resource")
        project_id = entry.get("project_id")
        project_code = entry.get("project_code")

        # Find which resource type is needed
        needed_resource = None
        if recommended_resource:
            needed_resource = recommended_resource.get("type")

        if needed_resource and needed_resource in remaining_capacity:
            if remaining_capacity[needed_resource] > 0:
                remaining_capacity[needed_resource] -= 1
                assigned.append({
                    **entry,
                    "allocation_status": "ASSIGNED",
                    "assigned_resource_type": needed_resource,
                    "assigned_resource_label": RESOURCE_TYPES[needed_resource]["label"],
                    "allocation_note": (
                        f"Assigned {RESOURCE_TYPES[needed_resource]['label']} "
                        f"based on {bottleneck or 'general'} bottleneck type."
                    ),
                })
            else:
                deferred.append({
                    **entry,
                    "allocation_status": "DEFERRED_CAPACITY",
                    "needed_resource_type": needed_resource,
                    "deferral_reason": (
                        f"No {RESOURCE_TYPES[needed_resource]['label']} capacity remaining. "
                        f"Project queued for next cycle."
                    ),
                })
        elif sum(remaining_capacity.values()) > 0:
            # Assign any available resource
            for rtype, cap in remaining_capacity.items():
                if cap > 0:
                    remaining_capacity[rtype] -= 1
                    assigned.append({
                        **entry,
                        "allocation_status": "ASSIGNED_GENERAL",
                        "assigned_resource_type": rtype,
                        "assigned_resource_label": RESOURCE_TYPES[rtype]["label"],
                        "allocation_note": "Assigned general capacity (no specific bottleneck match).",
                    })
                    break
        else:
            deferred.append({
                **entry,
                "allocation_status": "DEFERRED_NO_CAPACITY",
                "deferral_reason": "All resource capacity exhausted.",
            })

    return {
        "output_type": "E",
        "output_type_label": "Hypothetical Scenario Estimate — Decision-Support Simulation",
        "simulation_type": "GREEDY_RESOURCE_ALLOCATION",
        "disclaimer": SCENARIO_DISCLAIMER,
        "input_constraints": capacity_constraints,
        "total_projects": len(queue_entries),
        "assigned_count": len(assigned),
        "deferred_count": len(deferred),
        "remaining_capacity": remaining_capacity,
        "assigned_projects": assigned,
        "deferred_projects": deferred,
        "simulation_note": (
            "This greedy algorithm assigns resources in priority-score order. "
            "It is a simplistic first-fit simulation — NOT an optimal allocation. "
            "A human officer should review assigned/deferred lists and apply contextual judgment."
        ),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
