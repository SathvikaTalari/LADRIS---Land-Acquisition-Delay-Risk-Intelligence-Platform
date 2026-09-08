"""
LandPulse AI — Scenario Input Validator (Phase 4)
==================================================
Validates what-if simulation inputs before they reach the scenario engine.

DESIGN RULES:
  1. Only fields that actually exist in the real project dataset can be simulated.
  2. Each eligible field has a documented physical range and data source.
  3. OOD (out-of-distribution) inputs are allowed but flagged.
  4. Simulation is strictly read-only — this validator never writes to any table.
  5. If insufficient data exists, return a clear degradation message rather than
     allowing a simulation on invalid data.

Eligible Simulation Variables:
  These are derived from REAL project model fields.
  See ml/features/feature_engineering.py for the canonical feature catalog.

  1. compensation_completion_pct
     → Derived from: families_compensated / total_affected_families
     → Physical range: [0.0, 1.0]
     → Requires: total_affected_families > 0

  2. area_acquired_pct
     → Derived from: area_acquired_ha / total_area_ha
     → Physical range: [0.0, 1.0]
     → Requires: total_area_ha > 0

  3. cost_per_ha
     → Derived from: estimated_compensation_inr (Crore) / total_area_ha
     → Physical range: [0.05, 10.0] Crore/ha
     → Based on BhoomiRashi population: min=0.2, max=4.07, p95=3.5

  4. total_affected_families
     → Direct project field
     → Physical range: [1, 10000]

Fields NOT eligible for simulation:
  - notification_interval_days (date-based — simulation not meaningful without calendar)
  - state_code (cannot be simulated — geographically fixed)
  - executing_agency (cannot be simulated — contractually fixed)
  - has_3a_notification / has_3d_notification (legal milestone — cannot be hypothetically reversed)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ─── Eligible Simulation Field Definitions ────────────────────────────────────

SIMULATABLE_FIELDS: Dict[str, Dict[str, Any]] = {
    "compensation_completion_pct": {
        "display_name": "Compensation Completion",
        "description": (
            "Percentage of affected families who have received compensation. "
            "Derived from: families_compensated / total_affected_families."
        ),
        "unit": "proportion [0.0 – 1.0]",
        "display_unit": "%",
        "physical_min": 0.0,
        "physical_max": 1.0,
        "population_min": 0.0,
        "population_max": 1.0,
        "data_source": "Project model fields: families_compensated, total_affected_families",
        "requires_fields": ["total_affected_families"],
        "stage": "COMPENSATION",
        "eligible": True,
        "ood_threshold": None,  # Percentage — bounded naturally
    },
    "area_acquired_pct": {
        "display_name": "Area Acquisition Progress",
        "description": (
            "Percentage of required land area that has been formally acquired. "
            "Derived from: area_acquired_ha / total_area_ha."
        ),
        "unit": "proportion [0.0 – 1.0]",
        "display_unit": "%",
        "physical_min": 0.0,
        "physical_max": 1.0,
        "population_min": 0.0,
        "population_max": 1.0,
        "data_source": "Project model fields: area_acquired_ha, total_area_ha",
        "requires_fields": ["total_area_ha"],
        "stage": "POSSESSION",
        "eligible": True,
        "ood_threshold": None,
    },
    "cost_per_ha": {
        "display_name": "Acquisition Cost Intensity",
        "description": (
            "Estimated compensation cost per hectare in Crore INR. "
            "High values indicate peri-urban/urban land. "
            "BhoomiRashi population range: 0.20 – 4.07 Cr/ha."
        ),
        "unit": "Crore INR per hectare",
        "display_unit": "Cr/ha",
        "physical_min": 0.05,
        "physical_max": 10.0,
        "population_min": 0.20,
        "population_max": 4.07,
        "population_p25": 0.35,
        "population_p50": 0.52,
        "population_p75": 1.20,
        "population_p95": 3.50,
        "data_source": "BhoomiRashi public table (56 records). Derived: estimated_compensation_inr / total_area_ha",
        "requires_fields": ["total_area_ha"],
        "stage": "COMPENSATION",
        "eligible": True,
        "ood_threshold": 4.07,  # Above BhoomiRashi max → OOD warning
    },
    "total_affected_families": {
        "display_name": "Total Affected Families",
        "description": (
            "Total number of families affected by land acquisition. "
            "Influences R&R risk, compensation risk, and overall project complexity."
        ),
        "unit": "integer count",
        "display_unit": "families",
        "physical_min": 1,
        "physical_max": 10000,
        "population_min": 50,
        "population_max": 3000,
        "data_source": "Project model field: total_affected_families",
        "requires_fields": [],
        "stage": "RR",
        "eligible": True,
        "ood_threshold": 3000,  # Above observed project max → OOD warning
    },
}

# Fields explicitly NOT eligible for simulation
NON_SIMULATABLE_FIELDS = {
    "state_code": "Geographically fixed — cannot be hypothetically changed.",
    "executing_agency": "Contractually fixed — cannot be hypothetically changed.",
    "has_3a_notification": "Legal milestone — cannot be hypothetically reversed.",
    "has_3d_notification": "Legal milestone — cannot be hypothetically reversed.",
    "notification_interval_days": (
        "Date-based interval — simulation requires calendar context not available."
    ),
    "land_required_ha": (
        "Project scope is fixed — cannot be hypothetically reduced post-gazette."
    ),
}


# ─── Validation Result ────────────────────────────────────────────────────────

class ValidationError(Exception):
    """Raised when scenario input fails validation."""
    pass


def validate_scenario_inputs(
    scenario_inputs: Dict[str, Any],
    project_features: Dict[str, Any],
    data_completeness_pct: float = 100.0,
) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    Validate a set of scenario inputs.

    Returns
    -------
    (is_valid, validated_inputs, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []
    validated: Dict[str, Any] = {}

    # Check data completeness gate
    if data_completeness_pct < 50.0:
        return False, {}, [
            f"Insufficient data — project completeness {data_completeness_pct:.1f}% is below 50% minimum for simulation."
        ]

    for field, value in scenario_inputs.items():
        # Reject non-simulatable fields
        if field in NON_SIMULATABLE_FIELDS:
            errors.append(
                f"Field '{field}' is not eligible for simulation: "
                f"{NON_SIMULATABLE_FIELDS[field]}"
            )
            continue

        # Reject unknown fields
        if field not in SIMULATABLE_FIELDS:
            errors.append(
                f"Field '{field}' is not a recognised simulatable field. "
                f"Eligible fields: {list(SIMULATABLE_FIELDS.keys())}"
            )
            continue

        spec = SIMULATABLE_FIELDS[field]

        # Type coercion
        try:
            val = float(value)
        except (TypeError, ValueError):
            errors.append(f"Field '{field}': value '{value}' must be numeric.")
            continue

        # Physical range check
        if val < spec["physical_min"] or val > spec["physical_max"]:
            errors.append(
                f"Field '{field}': value {val} is outside physical range "
                f"[{spec['physical_min']}, {spec['physical_max']}]."
            )
            continue

        # Requires-field check
        for req in spec.get("requires_fields", []):
            if not project_features.get(req):
                warnings.append(
                    f"Field '{field}' simulation: required project field '{req}' "
                    f"is missing — simulation result will use fallback defaults."
                )

        # OOD warning (not rejection)
        if spec.get("ood_threshold") and val > spec["ood_threshold"]:
            warnings.append(
                f"Field '{field}': value {val} exceeds population maximum "
                f"({spec['ood_threshold']} {spec.get('display_unit', '')}). "
                f"Result is extrapolated — treat with caution."
            )

        validated[field] = val

    is_valid = len(errors) == 0 and len(validated) > 0
    if not validated and not errors:
        errors.append("No valid simulation inputs provided.")
        is_valid = False

    return is_valid, validated, warnings + (errors if errors else [])


def get_eligible_fields_for_project(
    project_features: Dict[str, Any],
    data_completeness_pct: float = 100.0,
) -> List[Dict[str, Any]]:
    """
    Return which simulation fields are eligible for this specific project,
    with current value, allowed range, and data source displayed.
    """
    eligible = []
    for field_name, spec in SIMULATABLE_FIELDS.items():
        if not spec.get("eligible"):
            continue

        # Check if project has required data for this field
        data_available = all(
            project_features.get(req) is not None
            for req in spec.get("requires_fields", [])
        )

        # Compute current value if derivable
        current_value = _derive_current_value(field_name, project_features)

        eligible.append({
            "field": field_name,
            "display_name": spec["display_name"],
            "description": spec["description"],
            "unit": spec["unit"],
            "display_unit": spec.get("display_unit", ""),
            "physical_min": spec["physical_min"],
            "physical_max": spec["physical_max"],
            "population_min": spec.get("population_min"),
            "population_max": spec.get("population_max"),
            "population_p25": spec.get("population_p25"),
            "population_p50": spec.get("population_p50"),
            "population_p75": spec.get("population_p75"),
            "population_p95": spec.get("population_p95"),
            "current_value": current_value,
            "data_source": spec["data_source"],
            "stage": spec["stage"],
            "data_available": data_available,
            "simulatable": data_available and data_completeness_pct >= 50.0,
            "not_simulatable_reason": (
                None if data_available and data_completeness_pct >= 50.0
                else (
                    "Insufficient data completeness" if data_completeness_pct < 50.0
                    else f"Required field(s) missing: {spec.get('requires_fields', [])}"
                )
            ),
        })

    return eligible


def _derive_current_value(
    field_name: str,
    features: Dict[str, Any],
) -> Optional[float]:
    """Derive the current value of a simulatable field from project features."""
    try:
        if field_name == "compensation_completion_pct":
            families = features.get("total_affected_families") or 0
            compensated = features.get("families_compensated") or 0
            return round(compensated / families, 4) if families > 0 else None

        if field_name == "area_acquired_pct":
            total = features.get("land_required_ha") or 0
            acquired = features.get("area_acquired_ha") or 0
            return round(acquired / total, 4) if total > 0 else None

        if field_name == "cost_per_ha":
            val = features.get("cost_per_ha")
            return round(float(val), 4) if val is not None else None

        if field_name == "total_affected_families":
            val = features.get("total_affected_families")
            return float(val) if val is not None else None

        return None
    except Exception:
        return None
