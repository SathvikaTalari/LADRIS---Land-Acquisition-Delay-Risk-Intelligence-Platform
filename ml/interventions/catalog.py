"""
LandPulse AI — Intervention Catalog (Phase 4)
==============================================
Structured, auditable catalog of candidate interventions.

DESIGN RULES:
  - Every entry is traceable to a real stage signal in the Phase 3 Stage Risk Engine.
  - No intervention is invented from scratch — each maps to a real acquisition stage
    defined by NH Act 1956 / RFCTLARR 2013.
  - action_description is framed as a DECISION-SUPPORT SUGGESTION, not a legal order.
  - confidence reflects data basis quality (REAL_SIGNAL vs PROXY).
  - eligibility_conditions define WHEN this intervention is surfaced.
  - evidence/provenance references real data sources only.

Stage mapping:
  NOTIFICATION  → real 3A/3D signal from BhoomiRashi
  OBJECTION     → proxy (cost_per_ha + state risk)
  AWARD         → proxy (land_ha + state + agency)
  COMPENSATION  → proxy (cost + families + state)
  RR            → proxy (families + state)
  POSSESSION    → proxy (upstream cascade)
"""

from typing import Any, Dict, List

# ─── Intervention Catalog ──────────────────────────────────────────────────────

INTERVENTION_CATALOG: List[Dict[str, Any]] = [

    # ── NOTIFICATION INTERVENTIONS ────────────────────────────────────────────
    {
        "intervention_id": "NOTIF-001",
        "category": "NOTIFICATION",
        "stage": "NOTIFICATION",
        "display_name": "Expedite 3D Notification Publication",
        "action_description": (
            "Review status of pending Section 3D (Final Notification) publication. "
            "Identify administrative bottlenecks in gazette printing or competent authority "
            "sign-off. Escalate to State NHAI/MoRTH liaison if interval exceeds population "
            "median (194 days from 3A)."
        ),
        "applicable_risk_factors": ["notification_interval_days", "has_3d_notification"],
        "required_inputs": ["has_3a_notification", "notification_interval_days"],
        "urgency": 0.75,
        "implementation_feasibility": 0.80,
        "affected_stage": "NOTIFICATION",
        "evidence": (
            "BhoomiRashi public table: population median 3A→3D interval = 194 days across "
            "56 BhoomiRashi national highway records (2020-2024)."
        ),
        "provenance": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "confidence": "HIGH",  # Real signal — actual date data
        "eligibility_conditions": {
            "required": ["has_3a_notification == True"],
            "trigger": "risk_level in ['HIGH', 'CRITICAL'] AND stage == 'NOTIFICATION'",
            "data_requirement": "notification_interval_days OR (has_3a AND NOT has_3d)",
        },
        "non_causal_note": (
            "This is a rule-based decision-support suggestion. "
            "It does not guarantee that acting on this intervention will prevent delay."
        ),
    },

    {
        "intervention_id": "NOTIF-002",
        "category": "NOTIFICATION",
        "stage": "NOTIFICATION",
        "display_name": "Review Pending 3A Notification Milestones",
        "action_description": (
            "Verify that Section 3A (Preliminary Notification) has been issued for all "
            "project sub-sections. Check whether gazette publication is pending at DPIIT "
            "or State Secretariat. Coordinate with nodal officer."
        ),
        "applicable_risk_factors": ["has_3a_notification"],
        "required_inputs": ["has_3a_notification"],
        "urgency": 0.60,
        "implementation_feasibility": 0.85,
        "affected_stage": "NOTIFICATION",
        "evidence": (
            "BhoomiRashi records indicate all 56 national highway projects have a 3A date, "
            "confirming 3A issuance is the standard entry point to the acquisition pipeline."
        ),
        "provenance": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "confidence": "HIGH",
        "eligibility_conditions": {
            "required": [],
            "trigger": "has_3a_notification == False",
            "data_requirement": "project_status in ['DRAFT', 'UNDER_REVIEW', 'APPROVED']",
        },
        "non_causal_note": (
            "Rule-based recommendation — triggered by absence of 3A date in project record."
        ),
    },

    # ── COMPENSATION INTERVENTIONS ─────────────────────────────────────────────
    {
        "intervention_id": "COMP-001",
        "category": "COMPENSATION",
        "stage": "COMPENSATION",
        "display_name": "Prioritize Pending Compensation Case Review",
        "action_description": (
            "Review the compensation disbursement pipeline for this project. "
            "Identify families with pending award payment and initiate reconciliation "
            "with Land Acquisition Collector (LAC) office. "
            "Prioritise unresolved payment records, especially where families_compensated "
            "is substantially below total_affected_families."
        ),
        "applicable_risk_factors": ["cost_per_ha", "affected_families", "state_code"],
        "required_inputs": ["total_affected_families", "families_compensated", "cost_per_ha"],
        "urgency": 0.80,
        "implementation_feasibility": 0.70,
        "affected_stage": "COMPENSATION",
        "evidence": (
            "DataGov.in delayed project records (10 records, 2023-2025): compensation disputes "
            "cited in Bihar (BR) and Uttar Pradesh (UP) delay cases. "
            "High cost_per_ha (>1.5 Cr/ha) correlates with urban land compensation complexity."
        ),
        "provenance": "DATAGOV_DELAYED_PROJECTS",
        "confidence": "MEDIUM",  # Proxy signal — no direct compensation completion data
        "eligibility_conditions": {
            "required": ["total_affected_families IS NOT NULL"],
            "trigger": "compensation_stage_risk >= 0.60 OR (families_compensated / total_affected_families < 0.70)",
            "data_requirement": "total_affected_families > 0",
        },
        "non_causal_note": (
            "Rule-based recommendation using proxy-derived compensation stage risk. "
            "Actual compensation completion data not yet available from public datasets."
        ),
    },

    {
        "intervention_id": "COMP-002",
        "category": "COMPENSATION",
        "stage": "COMPENSATION",
        "display_name": "Resolve High-Value Compensation Disputes",
        "action_description": (
            "Identify and fast-track high-value compensation objections. "
            "For projects with cost_per_ha above the national p75 (1.2 Cr/ha), "
            "engage a dedicated valuation officer to resolve pending dispute cases. "
            "Consider RFCTLARR Section 64 reference proceedings if disputes are unresolved "
            "beyond 60 days of award announcement."
        ),
        "applicable_risk_factors": ["cost_per_ha", "state_code"],
        "required_inputs": ["cost_per_ha", "state_code"],
        "urgency": 0.70,
        "implementation_feasibility": 0.65,
        "affected_stage": "COMPENSATION",
        "evidence": (
            "BhoomiRashi data: p75 cost_per_ha = 1.2 Cr/ha. "
            "DataGov.in records: MH and KA projects show high-value compensation as a "
            "cited delay factor (100% of DELAYED records in MH, 2023-2025 dataset)."
        ),
        "provenance": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE + DATAGOV_DELAYED_PROJECTS",
        "confidence": "MEDIUM",
        "eligibility_conditions": {
            "required": ["cost_per_ha IS NOT NULL"],
            "trigger": "cost_per_ha > 1.2 AND state_code in ['MH', 'KA', 'TN', 'WB']",
            "data_requirement": "cost_per_ha > 0",
        },
        "non_causal_note": (
            "Rule-based recommendation from cost intensity proxy. "
            "Does not confirm actual dispute existence — decision-support only."
        ),
    },

    # ── LEGAL / OBJECTION INTERVENTIONS ───────────────────────────────────────
    {
        "intervention_id": "LEGAL-001",
        "category": "LEGAL",
        "stage": "OBJECTION",
        "display_name": "Escalate Unresolved Ownership/Objection Cases",
        "action_description": (
            "Review pending Section 3C objection hearings. "
            "Identify cases where objection hearings have not been scheduled or disposals "
            "are overdue. Coordinate with the District Collector or Competent Authority "
            "to expedite hearing dates. Flag cases with unresolved title disputes to "
            "MoRTH legal cell."
        ),
        "applicable_risk_factors": ["cost_per_ha", "state_code"],
        "required_inputs": ["cost_per_ha", "state_code"],
        "urgency": 0.75,
        "implementation_feasibility": 0.60,
        "affected_stage": "OBJECTION",
        "evidence": (
            "DataGov.in delayed projects: gazette/valuation objections cited as delay "
            "factor in TN, MH, KA cases. High cost_per_ha projects have higher contestation "
            "probability (peri-urban / urban land). Source: 10 records, 2023-2025."
        ),
        "provenance": "DATAGOV_DELAYED_PROJECTS",
        "confidence": "MEDIUM",
        "eligibility_conditions": {
            "required": [],
            "trigger": "objection_stage_risk >= 0.55 OR cost_per_ha > 0.5",
            "data_requirement": "cost_per_ha IS NOT NULL OR state_code IS NOT NULL",
        },
        "non_causal_note": (
            "Rule-based recommendation — objection risk is proxy-derived from cost intensity. "
            "Actual objection records not available in current public datasets."
        ),
    },

    # ── DOCUMENTATION INTERVENTIONS ────────────────────────────────────────────
    {
        "intervention_id": "DOC-001",
        "category": "DOCUMENTATION",
        "stage": "AWARD",
        "display_name": "Resolve Incomplete Award Documentation",
        "action_description": (
            "Review the Declaration/Award documentation completeness for this project. "
            "Verify that Section 3D declaration gazette copies, land schedule, and "
            "title verification documents are complete and filed with LAC office. "
            "Flag missing survey numbers or title irregularities for correction."
        ),
        "applicable_risk_factors": ["land_required_ha", "state_code", "executing_agency"],
        "required_inputs": ["land_required_ha", "state_code"],
        "urgency": 0.65,
        "implementation_feasibility": 0.75,
        "affected_stage": "AWARD",
        "evidence": (
            "BhoomiRashi data: projects with land_required_ha > 185 ha (p75) "
            "span more survey numbers and are more prone to documentation gaps. "
            "DataGov.in: land schedule errors cited in WB delayed project."
        ),
        "provenance": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE + DATAGOV_DELAYED_PROJECTS",
        "confidence": "MEDIUM",
        "eligibility_conditions": {
            "required": ["land_required_ha IS NOT NULL"],
            "trigger": "award_stage_risk >= 0.50 OR land_required_ha > 135",
            "data_requirement": "land_required_ha > 0",
        },
        "non_causal_note": (
            "Rule-based recommendation from area-based proxy. "
            "Actual documentation completeness data not in public datasets."
        ),
    },

    # ── R&R INTERVENTIONS ──────────────────────────────────────────────────────
    {
        "intervention_id": "RR-001",
        "category": "RR",
        "stage": "RR",
        "display_name": "Prioritize Pending R&R Cases",
        "action_description": (
            "Review R&R entitlement disbursement and resettlement colony allotment status. "
            "Identify families where resettlement is pending beyond RFCTLARR 2013 timelines. "
            "Coordinate with State R&R authority and Social Impact Management Plan (SIMP) "
            "nodal officer to expedite pending allotments."
        ),
        "applicable_risk_factors": ["affected_families", "state_code"],
        "required_inputs": ["total_affected_families", "families_rehabilitated", "state_code"],
        "urgency": 0.70,
        "implementation_feasibility": 0.65,
        "affected_stage": "RR",
        "evidence": (
            "DataGov.in delayed projects: R&R delays are specifically noted in "
            "Bihar (BR) and West Bengal (WB) cases (highest state R&R risk in training data). "
            "RFCTLARR 2013 mandates R&R completion before possession."
        ),
        "provenance": "DATAGOV_DELAYED_PROJECTS",
        "confidence": "MEDIUM",
        "eligibility_conditions": {
            "required": ["total_affected_families IS NOT NULL"],
            "trigger": "rr_stage_risk >= 0.55 OR state_code in ['WB', 'BR', 'MH', 'KA']",
            "data_requirement": "total_affected_families > 0",
        },
        "non_causal_note": (
            "Rule-based recommendation from family count proxy + state profile. "
            "Actual R&R completion data not in public datasets."
        ),
    },

    {
        "intervention_id": "RR-002",
        "category": "RR",
        "stage": "RR",
        "display_name": "Accelerate Resettlement Colony Allotment",
        "action_description": (
            "For large displacement projects (total_affected_families > 500), "
            "initiate a dedicated review of resettlement colony readiness. "
            "Confirm that constructed housing units match allotment demand. "
            "Engage District Collector for encumbrance clearance on resettlement sites."
        ),
        "applicable_risk_factors": ["affected_families", "land_required_ha"],
        "required_inputs": ["total_affected_families"],
        "urgency": 0.65,
        "implementation_feasibility": 0.60,
        "affected_stage": "RR",
        "evidence": (
            "DataGov.in records: large R&R displacement cited in WB and MH delays. "
            "RFCTLARR 2013 Section 31: R&R entitlements must be completed before "
            "physical possession can proceed."
        ),
        "provenance": "DATAGOV_DELAYED_PROJECTS",
        "confidence": "LOW",  # Proxy only — small sample
        "eligibility_conditions": {
            "required": ["total_affected_families > 500"],
            "trigger": "rr_stage_risk >= 0.65",
            "data_requirement": "total_affected_families IS NOT NULL",
        },
        "non_causal_note": (
            "Rule-based from displacement proxy. Small sample basis — confidence LOW."
        ),
    },
]


# ─── Catalog Lookup Helpers ────────────────────────────────────────────────────

def get_catalog() -> List[Dict[str, Any]]:
    """Return the full intervention catalog."""
    return INTERVENTION_CATALOG


def get_by_id(intervention_id: str) -> Dict[str, Any]:
    """Return a single intervention by ID."""
    for item in INTERVENTION_CATALOG:
        if item["intervention_id"] == intervention_id:
            return item
    raise KeyError(f"Intervention '{intervention_id}' not found in catalog.")


def get_by_stage(stage: str) -> List[Dict[str, Any]]:
    """Return all interventions applicable to a given acquisition stage."""
    return [item for item in INTERVENTION_CATALOG if item["stage"] == stage.upper()]


def get_by_category(category: str) -> List[Dict[str, Any]]:
    """Return all interventions in a category."""
    return [item for item in INTERVENTION_CATALOG if item["category"] == category.upper()]


# Catalog metadata
CATALOG_METADATA = {
    "catalog_version": "v1.0-phase4",
    "total_interventions": len(INTERVENTION_CATALOG),
    "categories": list({item["category"] for item in INTERVENTION_CATALOG}),
    "stages_covered": list({item["stage"] for item in INTERVENTION_CATALOG}),
    "data_provenance": [
        "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "DATAGOV_DELAYED_PROJECTS",
        "MORTH_ANNUAL_REPORT_AGGREGATE",
    ],
    "framework": "NH Act 1956 / RFCTLARR 2013",
    "non_causal_statement": (
        "All interventions are RULE-BASED DECISION-SUPPORT SUGGESTIONS. "
        "They are derived from real risk signals in the Phase 3 Stage Risk Engine. "
        "They are NOT causal predictions, NOT legal orders, and do NOT guarantee "
        "that acting on them will prevent project delay."
    ),
}
