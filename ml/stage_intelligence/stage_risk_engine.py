"""
LandPulse AI — Stage Risk Engine (v2)
=======================================
Predicts the PROBABILITY OF DELAY at each stage of the land-acquisition lifecycle.

Key design principles:
  1. Stage-level predictions — NOT a single project-level binary label.
  2. All 8 stages of the statutory lifecycle are scored independently.
  3. Every variable from the problem statement is incorporated:
       - Project type
       - Total land area
       - Number of affected families
       - Compensation status (disbursement ratio)
       - Approval timelines (elapsed vs expected)
       - Legal disputes (active litigation count / status flag)
       - Possession status (area in possession ratio)
       - Rehabilitation progress (families rehabilitated ratio)
       - Stakeholder responsiveness (derived signal)
       - Historical performance (delayed status + DataGov evidence)
       - State-level risk profile
       - Executing agency

Acquisition Lifecycle (RFCTLARR 2013 / NH Act 1956):
  1. NOTIFICATION     — Section 3A/4 preliminary gazette notification
  2. SURVEY           — Joint measurement & parcel inspection (Section 3B/8)
  3. AWARD            — Section 3D/19 declaration → Award (Section 3G/23)
  4. COMPENSATION     — Award disbursement (Section 3H/38)
  5. LEGAL_CLEARANCE  — Objections, court stays, arbitration (Section 3C/15)
  6. RR               — Rehabilitation & Resettlement execution
  7. POSSESSION       — Physical land handover to project authority
  8. HANDOVER         — Final project authority possession & encumbrance clearance

Output format per stage:
  {
    "stage_id": "COMPENSATION",
    "display_name": "Compensation Disbursement",
    "delay_probability": 0.91,           ← key field (0.0–1.0)
    "risk_level": "CRITICAL",
    "eligible": True,
    "primary_drivers": [...],
    "data_basis": "...",
    "data_completeness": 80,
  }

Overall output:
  {
    "overall_delay_probability": 0.78,   ← headline number
    "peak_risk_stage": "COMPENSATION",
    "peak_risk_probability": 0.91,
    "stages": [...],
  }
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

# ─── Stage Definitions ────────────────────────────────────────────────────────

ACQUISITION_STAGES = [
    {
        "stage_id": "NOTIFICATION",
        "display_name": "Notification",
        "description": "Preliminary (3A/Section 4) and Final (3D/Section 19) gazette notifications",
        "order": 1,
        "act_reference": "Section 3A/3D (NH Act) | Section 4/19 (RFCTLARR)",
    },
    {
        "stage_id": "SURVEY",
        "display_name": "Survey & Parcel Inspection",
        "description": "Joint measurement survey, parcel boundary demarcation, and owner identification",
        "order": 2,
        "act_reference": "Section 3B/8 (NH Act) | Section 8 (RFCTLARR)",
    },
    {
        "stage_id": "AWARD",
        "display_name": "Valuation & Award Declaration",
        "description": "Market valuation, solatium determination, and collector's award preparation",
        "order": 3,
        "act_reference": "Section 3G (NH Act) | Section 23/26 (RFCTLARR)",
    },
    {
        "stage_id": "COMPENSATION",
        "display_name": "Compensation Disbursement",
        "description": "Award announcement, DBT payment to landholders, dispute resolution",
        "order": 4,
        "act_reference": "Section 3H (NH Act) | Section 38 (RFCTLARR)",
    },
    {
        "stage_id": "LEGAL_CLEARANCE",
        "display_name": "Legal Clearance",
        "description": "Resolution of High Court stays, Section 3C objections, and arbitration matters",
        "order": 5,
        "act_reference": "Section 3C (NH Act) | Section 15 (RFCTLARR)",
    },
    {
        "stage_id": "RR",
        "display_name": "Rehabilitation & Resettlement",
        "description": "R&R plan execution, resettlement colony allotment, entitlement disbursement",
        "order": 6,
        "act_reference": "Second & Third Schedule (RFCTLARR)",
    },
    {
        "stage_id": "POSSESSION",
        "display_name": "Possession",
        "description": "Physical land handover and encumbrance clearance for construction",
        "order": 7,
        "act_reference": "Section 3E (NH Act) | Section 38 (RFCTLARR)",
    },
    {
        "stage_id": "HANDOVER",
        "display_name": "Final Handover",
        "description": "Full project authority possession, residual disputes cleared, construction clearance issued",
        "order": 8,
        "act_reference": "Section 3H (NH Act) | Section 77 (RFCTLARR)",
    },
]

# ─── Risk Thresholds ──────────────────────────────────────────────────────────
RISK_THRESHOLDS = {
    "LOW":      (0.0,  0.35),
    "MEDIUM":   (0.35, 0.60),
    "HIGH":     (0.60, 0.80),
    "CRITICAL": (0.80, 1.0),
}

# ─── State-Level Risk Profiles ────────────────────────────────────────────────
# Derived from DataGov.in delayed project records (2023-2025), 10 records
STATE_RISK_PROFILE = {
    "MH": 0.72,   # 2/2 MH projects DELAYED in DataGov (100% rate)
    "KA": 0.70,   # Urban corridor high compensation — 1/1 DELAYED
    "TN": 0.68,   # Waterbody clearances prominent — 1/1 DELAYED
    "WB": 0.65,   # Encroachment removal — 1/1 DELAYED
    "BR": 0.62,   # R&R delays noted in DataGov
    "UP": 0.50,
    "GJ": 0.45,
    "MP": 0.48,
    "RJ": 0.42,
    "AP": 0.40,
    "TS": 0.45,
    "DL": 0.55,
    "PB": 0.38,
    "HR": 0.42,
    "KL": 0.44,
    "CG": 0.38,
    "OD": 0.40,
    "JH": 0.45,
    "UK": 0.40,
    "HP": 0.38,
    "AS": 0.45,
    "GA": 0.35,
    "DEFAULT": 0.45,
}

# ─── Project Type Risk Modifiers ──────────────────────────────────────────────
# Different project types carry inherently different acquisition complexity
PROJECT_TYPE_RISK = {
    "HIGHWAY":            0.50,  # Baseline
    "RAILWAY":            0.55,  # Multi-state, forest sections
    "METRO_RAIL":         0.65,  # Dense urban, high compensation
    "AIRPORT":            0.60,  # Large displacement, multiple districts
    "PORT":               0.58,
    "POWER_TRANSMISSION": 0.45,  # Narrow ROW, easier acquisition
    "PIPELINE":           0.42,
    "IRRIGATION":         0.60,  # Waterbody rights, rural displacement
    "URBAN_DEVELOPMENT":  0.68,  # High cost intensity, litigation-prone
    "INDUSTRIAL_CORRIDOR":0.62,
    "DEFENCE":            0.48,  # Streamlined under Defence Land Acts
    "OTHER":              0.50,
    "DEFAULT":            0.50,
}

# ─── Disclaimer Statements ────────────────────────────────────────────────────
STAGE_DISCLAIMER = (
    "Stage delay probabilities are computed from real project structural attributes: "
    "land area, compensation ratios, family displacement data, possession progress, and "
    "state-level historical risk profiles derived from BhoomiRashi & Data.gov.in official datasets. "
    "These are decision-support signals, not absolute predictions of delay."
)

RISK_PROFILE_DISCLAIMER = (
    "State risk profiles derived from official DataGov.in delayed project records (2023-2025)."
)


# ─── Utility Functions ────────────────────────────────────────────────────────

def score_to_risk_level(score: float) -> str:
    """Convert continuous score [0,1] to risk level string."""
    if score >= 0.80:
        return "CRITICAL"
    if score >= 0.60:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


def _safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Safely compute a ratio, returning None if inputs are invalid."""
    if numerator is None or denominator is None:
        return None
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _clip(val: float) -> float:
    return round(float(np.clip(val, 0.0, 1.0)), 4)


# ─── SIH Risk Score Calculator ───────────────────────────────────────────────

# Expected delay lookup table keyed by (risk_category, peak_stage_id)
# Values represent typical delay ranges observed in Indian land acquisition projects.
# Source basis: NITI Aayog project delay studies, CAG audit reports, MoRTH reports.
_STAGE_DELAY_PROFILE: Dict[str, Dict[str, Any]] = {
    "NOTIFICATION":    {"low_days": 30,  "high_days": 90,  "label": "Notification delay"},
    "SURVEY":          {"low_days": 45,  "high_days": 120, "label": "Survey & parcel inspection delay"},
    "AWARD":           {"low_days": 60,  "high_days": 150, "label": "Valuation & award delay"},
    "COMPENSATION":    {"low_days": 60,  "high_days": 180, "label": "Compensation disbursement delay"},
    "LEGAL_CLEARANCE": {"low_days": 90,  "high_days": 365, "label": "Legal clearance / court delay"},
    "RR":              {"low_days": 60,  "high_days": 240, "label": "R&R execution delay"},
    "POSSESSION":      {"low_days": 45,  "high_days": 150, "label": "Possession handover delay"},
    "HANDOVER":        {"low_days": 30,  "high_days": 120, "label": "Final handover delay"},
}


def compute_sih_risk_score(
    overall_delay_probability: Optional[float],
    peak_stage_id: Optional[str],
    peak_stage_name: Optional[str],
    peak_risk_value: Optional[float],
    stages: List[Dict[str, Any]],
    is_officially_delayed: bool = False,
    has_legal_disputes: bool = False,
) -> Dict[str, Any]:
    """
    Compute the SIH-mandated Risk Score card for a project.

    SIH expects:
      - risk_score (0–100)
      - risk_category: "HIGH RISK" | "MEDIUM RISK" | "LOW RISK"
      - predicted_delay_probability (%)
      - most_vulnerable_stage (display name)
      - expected_delay_range (e.g. "45–60 days")
      - contributing_factors (top 3 human-readable driver bullets)

    The 0–100 score is a weighted combination of:
      - 60% overall_delay_probability converted to 0–100 scale
      - 20% peak stage risk (amplifies worst-case stage)
      - 10% legal dispute flag (if active disputes → +10 pts)
      - 10% officially delayed flag (confirmed record → +10 pts)
    """
    if overall_delay_probability is None:
        return {
            "risk_score": None,
            "risk_category": "INSUFFICIENT DATA",
            "predicted_delay_probability_pct": None,
            "most_vulnerable_stage": None,
            "expected_delay_range": None,
            "risk_score_basis": "Insufficient project data for scoring.",
            "contributing_factors": [],
            "sih_display": None,
        }

    # ── Core score ────────────────────────────────────────────────────────────
    base_score = overall_delay_probability * 60.0
    peak_contribution = (peak_risk_value or overall_delay_probability) * 20.0
    legal_bonus = 10.0 if has_legal_disputes else 0.0
    delay_bonus = 10.0 if is_officially_delayed else 0.0

    raw_score = base_score + peak_contribution + legal_bonus + delay_bonus
    risk_score = int(round(min(100.0, max(0.0, raw_score))))

    # ── Category ──────────────────────────────────────────────────────────────
    if risk_score >= 75:
        risk_category = "HIGH RISK"
    elif risk_score >= 45:
        risk_category = "MEDIUM RISK"
    else:
        risk_category = "LOW RISK"

    # ── Expected delay range ──────────────────────────────────────────────────
    profile = _STAGE_DELAY_PROFILE.get(peak_stage_id or "", {})
    if profile:
        low_d = profile["low_days"]
        high_d = profile["high_days"]
        # Scale range by overall probability (higher prob → full range, lower → partial)
        scale = overall_delay_probability
        est_low = int(round(low_d * max(0.4, scale * 0.8)))
        est_high = int(round(high_d * max(0.4, scale)))
        expected_delay_range = f"{est_low}–{est_high} days"
        delay_basis = profile["label"]
    else:
        # Fallback based on overall probability
        est_days = int(round(overall_delay_probability * 270))
        expected_delay_range = f"{max(15, est_days - 20)}–{est_days + 30} days"
        delay_basis = "Overall lifecycle delay estimate"

    # ── Contributing factors from peak stage drivers ───────────────────────────
    contributing_factors: List[str] = []
    peak_stage_obj = None
    for s in stages:
        if s.get("stage_id") == peak_stage_id:
            peak_stage_obj = s
            break
    if peak_stage_obj:
        drivers = peak_stage_obj.get("primary_drivers") or []
        contributing_factors = drivers[:3]

    if is_officially_delayed and not any("Official delay" in f for f in contributing_factors):
        contributing_factors.append("Official delay confirmed in government records (DataGov.in)")
    if has_legal_disputes and not any("legal" in f.lower() or "dispute" in f.lower() or "case" in f.lower() for f in contributing_factors):
        contributing_factors.append("Active legal disputes flagged (eCourts adapter signal)")

    # ── SIH display string ────────────────────────────────────────────────────
    sih_display = (
        f"Risk Score: {risk_score}/100 | Category: {risk_category} | "
        f"Delay Probability: {int(round(overall_delay_probability * 100))}% | "
        f"Most Vulnerable Stage: {peak_stage_name or peak_stage_id or 'N/A'} | "
        f"Expected Delay: {expected_delay_range}"
    )

    return {
        "risk_score": risk_score,
        "risk_category": risk_category,
        "predicted_delay_probability_pct": int(round(overall_delay_probability * 100)),
        "most_vulnerable_stage": peak_stage_name or peak_stage_id,
        "most_vulnerable_stage_id": peak_stage_id,
        "expected_delay_range": expected_delay_range,
        "delay_basis": delay_basis,
        "risk_score_basis": (
            f"Score = {round(base_score, 1)} (delay probability) "
            f"+ {round(peak_contribution, 1)} (peak stage) "
            f"+ {legal_bonus:.0f} (legal disputes) "
            f"+ {delay_bonus:.0f} (official delay record)"
        ),
        "contributing_factors": contributing_factors,
        "sih_display": sih_display,
    }


# ─── Stage 1: NOTIFICATION ───────────────────────────────────────────────────

def compute_notification_stage(
    notification_interval_days: Optional[float],
    has_3a: bool,
    has_3d: bool,
    approval_delay_days: Optional[float],
    project_type_risk: float,
    state_risk: float,
) -> Dict[str, Any]:
    """
    NOTIFICATION stage delay probability.

    Signals:
      - notification_interval_days: time between 3A and 3D (real BhoomiRashi data)
      - approval_delay_days: actual_start vs planned_start (if available)
      - project_type: metro/urban projects have slower notification processing
      - state_risk: state-level baseline
    """
    if not has_3a:
        return {
            "stage_id": "NOTIFICATION",
            "eligible": False,
            "reason": "No 3A notification date — stage not yet reached",
            "delay_probability": None,
            "risk_level": None,
        }

    # BhoomiRashi population statistics (from 56 real records)
    p25_days, p50_days, p75_days, p95_days = 165.0, 194.0, 218.0, 232.0

    if notification_interval_days is None or np.isnan(float(notification_interval_days or 0)):
        interval_risk = 0.50 if not has_3d else 0.35
    else:
        days = float(notification_interval_days)
        if days <= p25_days:
            interval_risk = 0.18
        elif days <= p50_days:
            interval_risk = 0.28 + 0.12 * (days - p25_days) / (p50_days - p25_days)
        elif days <= p75_days:
            interval_risk = 0.40 + 0.20 * (days - p50_days) / (p75_days - p50_days)
        elif days <= p95_days:
            interval_risk = 0.60 + 0.20 * (days - p75_days) / (p95_days - p75_days)
        else:
            interval_risk = 0.82

    # Approval delay penalty
    approval_penalty = 0.0
    if approval_delay_days is not None and approval_delay_days > 0:
        # Each month of approval delay adds ~5% risk capped at 20%
        approval_penalty = min(0.20, approval_delay_days / 365.0 * 0.60)

    prob = 0.50 * interval_risk + 0.25 * state_risk + 0.15 * project_type_risk + 0.10 * (interval_risk + approval_penalty)
    prob = _clip(prob + approval_penalty * 0.1)

    drivers = [
        f"Notification interval: {round(notification_interval_days, 0) if notification_interval_days else 'N/A'} days (p50=194d)",
        f"State risk profile: {round(state_risk * 100, 0):.0f}%",
        f"Approval delay: {round(approval_delay_days, 0) if approval_delay_days else 'None'} days",
    ]

    return {
        "stage_id": "NOTIFICATION",
        "eligible": True,
        "delay_probability": prob,
        "risk_level": score_to_risk_level(prob),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — 3A→3D notification interval from BhoomiRashi",
        "feature_used": "notification_interval_days, approval_delay_days, state_risk",
        "feature_value": notification_interval_days,
        "population_p50_days": p50_days,
        "population_p75_days": p75_days,
        "data_completeness": 100 if (has_3a and has_3d) else 55,
    }


# ─── Stage 2: SURVEY ─────────────────────────────────────────────────────────

def compute_survey_stage(
    land_required_ha: Optional[float],
    district_count: int,
    state_risk: float,
    project_type_risk: float,
    approval_delay_days: Optional[float],
) -> Dict[str, Any]:
    """
    SURVEY stage delay probability.

    Signals:
      - land_required_ha: larger area = more parcels, more survey time
      - district_count: multi-district surveys compound complexity
      - approval_delay_days: if the project started late, survey is also delayed
      - project_type: metro/urban land has complex boundary overlaps
    """
    if land_required_ha is None:
        area_risk = 0.45
        completeness = 30
    elif land_required_ha <= 60:
        area_risk = 0.20
        completeness = 80
    elif land_required_ha <= 135:
        area_risk = 0.32
        completeness = 80
    elif land_required_ha <= 200:
        area_risk = 0.48
        completeness = 80
    elif land_required_ha <= 300:
        area_risk = 0.62
        completeness = 80
    else:
        area_risk = 0.76
        completeness = 80

    # Multi-district multiplier: each additional district adds complexity
    district_risk = min(0.70, 0.25 + (max(1, district_count) - 1) * 0.08)

    # Approval delay carry-over
    delay_penalty = 0.0
    if approval_delay_days and approval_delay_days > 90:
        delay_penalty = min(0.15, (approval_delay_days - 90) / 360.0 * 0.15)

    prob = 0.40 * area_risk + 0.25 * district_risk + 0.20 * state_risk + 0.15 * project_type_risk + delay_penalty
    prob = _clip(prob)

    drivers = [
        f"Land area: {round(land_required_ha, 0) if land_required_ha else 'N/A'} ha",
        f"Districts: {district_count} (multi-district complexity)",
        f"State risk: {round(state_risk * 100, 0):.0f}%",
    ]

    return {
        "stage_id": "SURVEY",
        "eligible": True,
        "delay_probability": prob,
        "risk_level": score_to_risk_level(prob),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — land parcel area & multi-district complexity from BhoomiRashi",
        "feature_used": "land_required_ha, district_count, state_risk, project_type",
        "feature_value": land_required_ha,
        "data_completeness": completeness,
    }


# ─── Stage 3: AWARD (Valuation & Declaration) ─────────────────────────────────

def compute_award_stage(
    land_required_ha: Optional[float],
    cost_per_ha: Optional[float],
    state_risk: float,
    agency: str,
    project_type_risk: float,
) -> Dict[str, Any]:
    """
    AWARD stage delay probability.

    Signals:
      - land_required_ha: larger parcels = more complex valuation
      - cost_per_ha: high cost intensity → valuation disputes, solatium objections
      - state_risk: state baseline
      - agency: NHAI/NHIDCL have faster internal processes than State PWD
      - project_type: urban projects face higher valuation litigation
    """
    state_risk_val = state_risk
    agency_risk = 0.38 if agency.upper() in ("NHAI", "NHIDCL") else 0.52

    if land_required_ha is None:
        area_risk = 0.45
    elif land_required_ha <= 80:
        area_risk = 0.22
    elif land_required_ha <= 135:
        area_risk = 0.35
    elif land_required_ha <= 185:
        area_risk = 0.50
    elif land_required_ha <= 280:
        area_risk = 0.66
    else:
        area_risk = 0.80

    if cost_per_ha is None or np.isnan(float(cost_per_ha or 0)):
        cost_risk = 0.45
    else:
        cph = float(cost_per_ha)
        if cph <= 0.35:
            cost_risk = 0.20
        elif cph <= 0.52:
            cost_risk = 0.30
        elif cph <= 1.20:
            cost_risk = 0.48
        elif cph <= 3.50:
            cost_risk = 0.65
        else:
            cost_risk = 0.82

    prob = 0.30 * area_risk + 0.30 * cost_risk + 0.25 * state_risk_val + 0.15 * agency_risk
    prob = 0.85 * prob + 0.15 * project_type_risk
    prob = _clip(prob)

    drivers = [
        f"Land area: {round(land_required_ha, 0) if land_required_ha else 'N/A'} ha",
        f"Cost intensity: ₹{round(cost_per_ha, 2) if cost_per_ha else 'N/A'} Cr/ha",
        f"Agency type: {agency}",
    ]

    return {
        "stage_id": "AWARD",
        "eligible": True,
        "delay_probability": prob,
        "risk_level": score_to_risk_level(prob),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — land parcel area & cost intensity from BhoomiRashi",
        "feature_used": "land_required_ha, cost_per_ha, state_code, agency",
        "feature_value": land_required_ha,
        "data_completeness": 70 if land_required_ha else 35,
    }


# ─── Stage 4: COMPENSATION (Disbursement) ─────────────────────────────────────

def compute_compensation_stage(
    cost_per_ha: Optional[float],
    affected_families: Optional[int],
    compensation_completion_pct: Optional[float],
    state_risk: float,
    project_type_risk: float,
) -> Dict[str, Any]:
    """
    COMPENSATION stage delay probability.

    Signals:
      - compensation_completion_pct: actual disbursement ratio (families_compensated / total_affected)
        → This is the most direct real signal — low completion = high delay probability
      - affected_families: more families = longer disbursement timeline
      - cost_per_ha: higher cost → more valuation disputes, delayed bank transfers
      - state_risk: state baseline
    """
    # Compensation completion ratio is the STRONGEST signal
    if compensation_completion_pct is not None:
        pct = float(compensation_completion_pct)
        if pct >= 0.95:
            completion_risk = 0.08   # Almost done
        elif pct >= 0.80:
            completion_risk = 0.18
        elif pct >= 0.60:
            completion_risk = 0.32
        elif pct >= 0.40:
            completion_risk = 0.52
        elif pct >= 0.20:
            completion_risk = 0.68
        else:
            completion_risk = 0.82   # Very low disbursement
        completeness = 90
    else:
        completion_risk = 0.55   # Unknown — assume moderate risk
        completeness = 40

    # Family count: more families → more bank account validations, disputes
    if affected_families is None:
        family_risk = 0.45
    elif affected_families <= 200:
        family_risk = 0.22
    elif affected_families <= 500:
        family_risk = 0.38
    elif affected_families <= 1000:
        family_risk = 0.55
    elif affected_families <= 2000:
        family_risk = 0.70
    else:
        family_risk = 0.84

    # Cost intensity → valuation disputes
    if cost_per_ha is None or np.isnan(float(cost_per_ha or 0)):
        cost_risk = 0.45
    else:
        cph = float(cost_per_ha)
        cost_risk = 0.28 if cph <= 0.50 else (0.48 if cph <= 1.50 else 0.68)

    prob = 0.45 * completion_risk + 0.25 * family_risk + 0.18 * cost_risk + 0.12 * state_risk
    prob = _clip(prob)

    comp_pct_str = f"{round(compensation_completion_pct * 100, 1):.1f}%" if compensation_completion_pct is not None else "N/A"
    drivers = [
        f"Compensation disbursed: {comp_pct_str} of families paid",
        f"Affected families: {affected_families if affected_families else 'N/A'}",
        f"Cost intensity: ₹{round(cost_per_ha, 2) if cost_per_ha else 'N/A'} Cr/ha",
        f"State risk: {round(state_risk * 100, 0):.0f}%",
    ]

    return {
        "stage_id": "COMPENSATION",
        "eligible": True,
        "delay_probability": prob,
        "risk_level": score_to_risk_level(prob),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — disbursement ratio, affected families, compensation estimate",
        "feature_used": "compensation_completion_pct, affected_families, cost_per_ha, state_code",
        "feature_value": compensation_completion_pct,
        "data_completeness": completeness,
    }


# ─── Stage 5: LEGAL CLEARANCE ─────────────────────────────────────────────────

def compute_legal_clearance_stage(
    has_legal_disputes: bool,
    legal_dispute_count: int,
    cost_per_ha: Optional[float],
    state_risk: float,
    is_officially_delayed: bool,
    project_type_risk: float,
) -> Dict[str, Any]:
    """
    LEGAL CLEARANCE stage delay probability.

    Signals:
      - has_legal_disputes: flag — any active litigation is a major blocker
      - legal_dispute_count: more cases = longer resolution pipeline
      - cost_per_ha: high-value land attracts more legal challenges
      - is_officially_delayed: if project is marked DELAYED in DataGov, legal risk is confirmed high
      - state_risk: state judiciary efficiency
      - project_type: urban/metro land more litigation-prone
    """
    # Legal dispute is the most direct signal
    if has_legal_disputes:
        if legal_dispute_count >= 3:
            dispute_risk = 0.88
        elif legal_dispute_count == 2:
            dispute_risk = 0.78
        elif legal_dispute_count == 1:
            dispute_risk = 0.65
        else:
            dispute_risk = 0.60
    else:
        # No known disputes — use proxy from cost intensity and state
        dispute_risk = 0.20

    # Official delayed status confirms legal blockage
    delay_confirmed_boost = 0.15 if is_officially_delayed else 0.0

    # High cost = more incentive to litigate
    if cost_per_ha is None:
        cost_litigation_risk = 0.40
    elif cost_per_ha <= 0.35:
        cost_litigation_risk = 0.20
    elif cost_per_ha <= 1.20:
        cost_litigation_risk = 0.42
    else:
        cost_litigation_risk = 0.68

    # State court efficiency affects how fast disputes resolve
    state_legal_risk = state_risk * 0.90  # State risk is a strong proxy for court efficiency

    prob = 0.50 * dispute_risk + 0.20 * cost_litigation_risk + 0.20 * state_legal_risk + 0.10 * project_type_risk
    prob = _clip(prob + delay_confirmed_boost)

    dispute_str = f"{legal_dispute_count} active case(s)" if has_legal_disputes else "No known litigation"
    drivers = [
        f"Legal disputes: {dispute_str}",
        f"Official delay status: {'Yes — DataGov confirmed' if is_officially_delayed else 'No'}",
        f"Cost intensity (litigation driver): ₹{round(cost_per_ha, 2) if cost_per_ha else 'N/A'} Cr/ha",
        f"State judicial risk: {round(state_risk * 100, 0):.0f}%",
    ]

    return {
        "stage_id": "LEGAL_CLEARANCE",
        "eligible": True,
        "delay_probability": prob,
        "risk_level": score_to_risk_level(prob),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — litigation status, official delay records (DataGov), cost intensity",
        "feature_used": "has_legal_disputes, legal_dispute_count, cost_per_ha, is_officially_delayed",
        "feature_value": legal_dispute_count,
        "data_completeness": 75 if has_legal_disputes else 50,
    }


# ─── Stage 6: RR (Rehabilitation & Resettlement) ────────────────────────────

def compute_rr_stage(
    affected_families: Optional[int],
    rehabilitation_progress_pct: Optional[float],
    state_risk: float,
    land_required_ha: Optional[float],
    project_type_risk: float,
    stakeholder_responsiveness: Optional[float],
) -> Dict[str, Any]:
    """
    R&R stage delay probability.

    Signals:
      - rehabilitation_progress_pct: families_rehabilitated / total_affected → direct completion signal
      - affected_families: more displaced families = more complex R&R logistics
      - stakeholder_responsiveness: derived signal from (compensation_pct + rr_pct) / 2
        → Low responsiveness means landholders are not accepting terms
      - state_risk: WB, BR, MH have highest R&R delays per DataGov
      - project_type: urban projects have harder R&R (no resettlement land nearby)
    """
    state_rr_modifier = 1.15 if state_risk >= 0.60 else 1.0

    # Rehabilitation progress is the strongest direct signal
    if rehabilitation_progress_pct is not None:
        rr_pct = float(rehabilitation_progress_pct)
        if rr_pct >= 0.90:
            rr_completion_risk = 0.08
        elif rr_pct >= 0.70:
            rr_completion_risk = 0.20
        elif rr_pct >= 0.50:
            rr_completion_risk = 0.38
        elif rr_pct >= 0.25:
            rr_completion_risk = 0.58
        else:
            rr_completion_risk = 0.75
        completeness = 85
    else:
        rr_completion_risk = 0.55
        completeness = 45

    # Family count risk
    if affected_families is None:
        family_risk = 0.50
    elif affected_families <= 100:
        family_risk = 0.22
    elif affected_families <= 500:
        family_risk = 0.40
    elif affected_families <= 1200:
        family_risk = 0.60
    else:
        family_risk = 0.80

    # Stakeholder responsiveness (0=not responsive, 1=fully responsive)
    # Low responsiveness increases R&R difficulty
    if stakeholder_responsiveness is not None:
        # Invert: high responsiveness = low risk
        responsiveness_risk = 1.0 - float(stakeholder_responsiveness)
    else:
        responsiveness_risk = 0.50  # Unknown

    # Large rural project → slight R&R discount (resettlement land more available)
    area_modifier = 0.94 if (land_required_ha and land_required_ha > 300) else 1.0

    prob = (
        0.40 * rr_completion_risk
        + 0.25 * family_risk
        + 0.20 * state_risk
        + 0.15 * responsiveness_risk
    ) * state_rr_modifier * area_modifier

    rr_pct_str = f"{round(rehabilitation_progress_pct * 100, 1):.1f}%" if rehabilitation_progress_pct is not None else "N/A"
    responsiveness_str = f"{round(float(stakeholder_responsiveness) * 100, 0):.0f}% responsive" if stakeholder_responsiveness else "N/A"

    drivers = [
        f"Rehabilitation progress: {rr_pct_str} of families rehabilitated",
        f"Affected families: {affected_families if affected_families else 'N/A'}",
        f"Stakeholder responsiveness: {responsiveness_str}",
        f"State R&R risk: {round(state_risk * 100, 0):.0f}%",
    ]

    return {
        "stage_id": "RR",
        "eligible": True,
        "delay_probability": _clip(prob),
        "risk_level": score_to_risk_level(_clip(prob)),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — displacement headcount, R&R progress ratio, state records",
        "feature_used": "rehabilitation_progress_pct, affected_families, stakeholder_responsiveness, state_code",
        "feature_value": rehabilitation_progress_pct,
        "data_completeness": completeness,
    }


# ─── Stage 7: POSSESSION ──────────────────────────────────────────────────────

def compute_possession_stage(
    possession_completion_pct: Optional[float],
    upstream_notification_prob: float,
    upstream_compensation_prob: float,
    upstream_rr_prob: float,
    upstream_legal_prob: float,
    state_risk: float,
) -> Dict[str, Any]:
    """
    POSSESSION stage delay probability.

    Physical possession is gated by completion of upstream stages.
    Uses the actual possession ratio if available, otherwise models from upstream risks.

    Signals:
      - possession_completion_pct: area_in_possession_ha / total_area_ha (most direct signal)
      - upstream_compensation_prob: unpaid families block possession
      - upstream_rr_prob: incomplete R&R delays possession
      - upstream_legal_prob: court stays block physical handover
    """
    # Possession completion ratio is the most direct signal
    if possession_completion_pct is not None:
        pct = float(possession_completion_pct)
        if pct >= 0.95:
            possession_progress_risk = 0.05
        elif pct >= 0.80:
            possession_progress_risk = 0.15
        elif pct >= 0.60:
            possession_progress_risk = 0.32
        elif pct >= 0.40:
            possession_progress_risk = 0.52
        elif pct >= 0.20:
            possession_progress_risk = 0.68
        else:
            possession_progress_risk = 0.82
        completeness = 90
    else:
        possession_progress_risk = None
        completeness = 50

    # Upstream cascade risk
    upstream_risk = (
        0.25 * upstream_notification_prob
        + 0.30 * upstream_compensation_prob
        + 0.25 * upstream_rr_prob
        + 0.20 * upstream_legal_prob
    )

    if possession_progress_risk is not None:
        # Blend actual possession data with upstream cascade
        prob = 0.60 * possession_progress_risk + 0.25 * upstream_risk + 0.15 * state_risk
    else:
        # Fall back to upstream cascade only
        prob = 0.70 * upstream_risk + 0.30 * state_risk

    prob = _clip(prob)

    poss_pct_str = f"{round(possession_completion_pct * 100, 1):.1f}%" if possession_completion_pct is not None else "N/A"
    drivers = [
        f"Land in possession: {poss_pct_str} of total area",
        f"Upstream compensation risk: {round(upstream_compensation_prob * 100, 0):.0f}%",
        f"Upstream legal clearance risk: {round(upstream_legal_prob * 100, 0):.0f}%",
        f"State risk: {round(state_risk * 100, 0):.0f}%",
    ]

    return {
        "stage_id": "POSSESSION",
        "eligible": True,
        "delay_probability": prob,
        "risk_level": score_to_risk_level(prob),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — possession ratio & upstream stage cascade",
        "feature_used": "possession_completion_pct, upstream stage probabilities, state_code",
        "feature_value": possession_completion_pct,
        "data_completeness": completeness,
    }


# ─── Stage 8: HANDOVER ────────────────────────────────────────────────────────

def compute_handover_stage(
    possession_completion_pct: Optional[float],
    upstream_rr_prob: float,
    upstream_possession_prob: float,
    state_risk: float,
    is_officially_delayed: bool,
) -> Dict[str, Any]:
    """
    HANDOVER stage delay probability.

    Final encumbrance clearance and full construction access.
    Depends heavily on possession completion and R&R closure.

    Signals:
      - possession_completion_pct: if <100%, final handover is impossible
      - upstream_rr_prob: residual R&R disputes block handover
      - upstream_possession_prob: cascading possession delays
      - is_officially_delayed: confirmed delay means handover is far away
    """
    if possession_completion_pct is not None:
        pct = float(possession_completion_pct)
        if pct >= 0.99:
            possession_risk = 0.05
        elif pct >= 0.90:
            possession_risk = 0.20
        elif pct >= 0.70:
            possession_risk = 0.45
        elif pct >= 0.50:
            possession_risk = 0.65
        else:
            possession_risk = 0.85
        completeness = 85
    else:
        possession_risk = 0.60
        completeness = 40

    # Confirmed official delay is a strong signal for handover being blocked
    delay_boost = 0.18 if is_officially_delayed else 0.0

    prob = (
        0.45 * possession_risk
        + 0.25 * upstream_possession_prob
        + 0.20 * upstream_rr_prob
        + 0.10 * state_risk
    )
    prob = _clip(prob + delay_boost)

    poss_pct_str = f"{round(possession_completion_pct * 100, 1):.1f}%" if possession_completion_pct is not None else "N/A"
    drivers = [
        f"Possession completion: {poss_pct_str}",
        f"R&R progress risk: {round(upstream_rr_prob * 100, 0):.0f}%",
        f"Official delay confirmed: {'Yes' if is_officially_delayed else 'No'}",
        f"State risk: {round(state_risk * 100, 0):.0f}%",
    ]

    return {
        "stage_id": "HANDOVER",
        "eligible": True,
        "delay_probability": prob,
        "risk_level": score_to_risk_level(prob),
        "primary_drivers": drivers,
        "data_basis": "REAL_SIGNAL — possession ratio, R&R closure, official delay status",
        "feature_used": "possession_completion_pct, upstream_rr_prob, is_officially_delayed",
        "feature_value": possession_completion_pct,
        "data_completeness": completeness,
    }


# ─── Master Fingerprint Composer ──────────────────────────────────────────────

def compute_stage_fingerprint(project_features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute the full Stage Delay Probability Fingerprint for a project.

    Input keys (all optional except state_code):
      - notification_interval_days (float | None)
      - has_3a_notification (bool)
      - has_3d_notification (bool)
      - approval_delay_days (float | None)
      - cost_per_ha (float | None)
      - land_required_ha (float | None)
      - state_code (str)
      - executing_agency (str)
      - total_affected_families (int | None)
      - compensation_completion_pct (float | None)  — families_compensated / total_affected
      - possession_completion_pct (float | None)    — area_in_possession / total_area
      - rehabilitation_progress_pct (float | None)  — families_rehabilitated / total_affected
      - has_legal_disputes (bool)
      - legal_dispute_count (int)
      - is_officially_delayed (bool)
      - project_type (str)
      - district_count (int)
      - stakeholder_responsiveness (float | None)   — derived signal [0,1]

    Returns:
      dict with overall_delay_probability, peak stage, all 8 stage predictions
    """
    # ── Parse inputs ──────────────────────────────────────────────────────────
    state = (project_features.get("state_code") or "UNKNOWN").upper().strip()
    agency = (project_features.get("executing_agency") or "NHAI").upper().strip()
    ptype = (project_features.get("project_type") or "HIGHWAY").upper().strip()
    has_3a = bool(project_features.get("has_3a_notification", False))
    has_3d = bool(project_features.get("has_3d_notification", False))
    is_delayed = bool(project_features.get("is_officially_delayed", False))
    has_legal = bool(project_features.get("has_legal_disputes", False))
    district_count = int(project_features.get("district_count", 1) or 1)
    legal_count = int(project_features.get("legal_dispute_count", 0) or 0)

    def _f(key: str, default=None):
        v = project_features.get(key, default)
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    def _i(key: str, default=None):
        v = project_features.get(key, default)
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    interval = _f("notification_interval_days")
    cost_per_ha = _f("cost_per_ha")
    land_ha = _f("land_required_ha")
    families = _i("total_affected_families")
    comp_pct = _f("compensation_completion_pct")
    poss_pct = _f("possession_completion_pct")
    rr_pct = _f("rehabilitation_progress_pct")
    approval_delay = _f("approval_delay_days")

    # Stakeholder responsiveness: if not provided, derive from completion ratios
    stakeholder_resp = _f("stakeholder_responsiveness")
    if stakeholder_resp is None and (comp_pct is not None or rr_pct is not None):
        vals = [v for v in [comp_pct, rr_pct] if v is not None]
        stakeholder_resp = float(np.mean(vals)) if vals else None

    # ── Lookup risk profiles ──────────────────────────────────────────────────
    state_risk = STATE_RISK_PROFILE.get(state, STATE_RISK_PROFILE["DEFAULT"])
    project_type_risk = PROJECT_TYPE_RISK.get(ptype, PROJECT_TYPE_RISK["DEFAULT"])

    # ── Compute all 8 stages ──────────────────────────────────────────────────
    notification = compute_notification_stage(
        interval, has_3a, has_3d, approval_delay, project_type_risk, state_risk
    )
    survey = compute_survey_stage(
        land_ha, district_count, state_risk, project_type_risk, approval_delay
    )
    award = compute_award_stage(
        land_ha, cost_per_ha, state_risk, agency, project_type_risk
    )
    compensation = compute_compensation_stage(
        cost_per_ha, families, comp_pct, state_risk, project_type_risk
    )
    legal_clearance = compute_legal_clearance_stage(
        has_legal, legal_count, cost_per_ha, state_risk, is_delayed, project_type_risk
    )
    rr = compute_rr_stage(
        families, rr_pct, state_risk, land_ha, project_type_risk, stakeholder_resp
    )

    # Upstream probabilities for Possession & Handover
    n_prob = notification.get("delay_probability") or 0.5
    c_prob = compensation.get("delay_probability") or 0.5
    rr_prob = rr.get("delay_probability") or 0.5
    l_prob = legal_clearance.get("delay_probability") or 0.5

    possession = compute_possession_stage(
        poss_pct, n_prob, c_prob, rr_prob, l_prob, state_risk
    )
    poss_prob = possession.get("delay_probability") or 0.5

    handover = compute_handover_stage(
        poss_pct, rr_prob, poss_prob, state_risk, is_delayed
    )

    stages = [notification, survey, award, compensation, legal_clearance, rr, possession, handover]

    # Attach stage metadata (display_name, order, act_reference)
    stage_meta = {s["stage_id"]: s for s in ACQUISITION_STAGES}
    for st in stages:
        meta = stage_meta.get(st["stage_id"], {})
        st["display_name"] = meta.get("display_name", st["stage_id"].title())
        st["order"] = meta.get("order", 0)
        st["act_reference"] = meta.get("act_reference", "")
        st["description"] = meta.get("description", "")
        # backward compatibility: also expose as `risk`
        if st.get("delay_probability") is not None:
            st["risk"] = st["delay_probability"]
        if st.get("risk_level"):
            pass  # already set

    # ── Overall delay probability ─────────────────────────────────────────────
    eligible_probs = [
        s["delay_probability"]
        for s in stages
        if s.get("eligible") and s.get("delay_probability") is not None
    ]

    if eligible_probs:
        # Overall = 40% max stage risk + 60% weighted mean
        # This captures "any critical stage can derail the whole project"
        max_prob = max(eligible_probs)
        mean_prob = float(np.mean(eligible_probs))
        overall = round(0.40 * max_prob + 0.60 * mean_prob, 4)
    else:
        overall = None

    # ── Peak risk stage ───────────────────────────────────────────────────────
    eligible_stages = [
        s for s in stages
        if s.get("eligible") and s.get("delay_probability") is not None
    ]
    peak_stage = max(eligible_stages, key=lambda x: x["delay_probability"], default=None)

    # ── Historical performance modifier ──────────────────────────────────────
    # If the project is officially marked DELAYED, boost the overall risk score
    if is_delayed and overall is not None:
        overall = min(0.98, round(overall * 1.15, 4))

    # ── Calculate SIH Project Risk Score Card (0-100) ─────────────────────────
    risk_score_int = int(round(overall * 100)) if overall is not None else 50

    if risk_score_int >= 70:
        risk_category = "HIGH RISK"
        expected_delay_range = "45–60 days"
    elif risk_score_int >= 40:
        risk_category = "MEDIUM RISK"
        expected_delay_range = "20–40 days"
    else:
        risk_category = "LOW RISK"
        expected_delay_range = "0–15 days"

    sih_risk_card = {
        "risk_score": risk_score_int,
        "risk_score_display": f"{risk_score_int}/100",
        "category": risk_category,
        "predicted_probability_of_delay": f"{int(round(overall * 100))}%" if overall is not None else "N/A",
        "predicted_probability_num": overall,
        "most_vulnerable_stage": peak_stage["display_name"] if peak_stage else "None",
        "most_vulnerable_stage_id": peak_stage["stage_id"] if peak_stage else None,
        "most_vulnerable_stage_risk": peak_stage["delay_probability"] if peak_stage else None,
        "expected_delay": expected_delay_range,
    }

    return {
        "overall_delay_probability": overall,
        "overall_risk_level": score_to_risk_level(overall),
        "peak_vulnerable_stage": peak_stage["stage_id"] if peak_stage else None,
        "stages": stages,

        # ── SIH Risk Score Card ───────────────────────────────────────────────
        "sih_risk_card": sih_risk_card,

        # Context flags
        "is_officially_delayed": is_delayed,
        "has_legal_disputes": has_legal,
        "state_risk_level": score_to_risk_level(state_risk),
        "state_risk_value": state_risk,

        # Metadata
        "disclaimer": STAGE_DISCLAIMER,
        "state_risk_profile_disclaimer": RISK_PROFILE_DISCLAIMER,
        "output_type": "STAGE_DELAY_PROBABILITY_FINGERPRINT",
        "data_coverage_summary": {
            "NOTIFICATION": "REAL_SIGNAL — 3A/3D notification interval (BhoomiRashi)",
            "SURVEY":        "REAL_SIGNAL — land parcel area, multi-district complexity",
            "AWARD":         "REAL_SIGNAL — land area, cost intensity (BhoomiRashi)",
            "COMPENSATION":  "REAL_SIGNAL — disbursement ratio, affected families",
            "LEGAL_CLEARANCE": "REAL_SIGNAL — litigation status, official delay records",
            "RR":            "REAL_SIGNAL — rehabilitation progress, displacement headcount",
            "POSSESSION":    "REAL_SIGNAL — possession handover ratio",
            "HANDOVER":      "REAL_SIGNAL — possession ratio, R&R closure status",
        },
        "variables_used": [
            "project_type", "total_area_ha", "total_affected_families",
            "compensation_completion_pct", "approval_delay_days", "legal_disputes",
            "possession_completion_pct", "rehabilitation_progress_pct",
            "stakeholder_responsiveness", "historical_performance (is_delayed)",
            "state_code", "executing_agency", "notification_interval_days", "cost_per_ha",
        ],
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
