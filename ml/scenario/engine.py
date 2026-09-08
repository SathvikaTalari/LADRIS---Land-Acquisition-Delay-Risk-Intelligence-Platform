"""
LandPulse AI — What-If Scenario Engine (Phase 4)
=================================================
Read-only scenario simulator.

CRITICAL DESIGN RULES:
  1. The engine NEVER writes to project records or any government-data table.
  2. It operates on a COPY of the feature dict — the original is never mutated.
  3. It re-runs the SAME deterministic Phase 3 scoring pipeline on the hypothetical inputs.
  4. All outputs are labeled "Scenario estimate — not a causal prediction."
  5. Multi-scenario comparison is supported (up to 3 scenarios).

Pipeline:
  Original project features (baseline)
      ↓
  Apply scenario overrides to a COPY
      ↓
  Re-run Stage Risk Engine + Anomaly pipeline
      ↓
  Compare: baseline_signals vs scenario_signals
      ↓
  Return delta with explicit "Scenario estimate" label

Method:
  RULE_BASED — uses the same deterministic Stage Risk Engine as Phase 3.
  No supervised model is applied to compute delay probability changes.
  The scenario output is always expressed as a change in anomaly/stage risk signals,
  NEVER as a change in delay probability.
"""

import logging
import math
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ml.scenario.validator import (
    validate_scenario_inputs,
    get_eligible_fields_for_project,
    SIMULATABLE_FIELDS,
)

log = logging.getLogger(__name__)

SCENARIO_DISCLAIMER = (
    "Scenario estimate — not a causal prediction. "
    "This what-if simulation re-runs the same deterministic rule-based risk pipeline "
    "with the hypothetical input values. It does NOT use a supervised delay model. "
    "Changes in risk signals are scenario estimates only — they do not guarantee "
    "actual delay reduction."
)

SCENARIO_METHOD_LABEL = "Model/Rule-Based Scenario"
MODEL_VERSION = "v1.0-phase4-scenario"


def run_scenario(
    project_features: Dict[str, Any],
    scenario_inputs: Dict[str, Any],
    data_completeness_pct: float = 100.0,
    scenario_name: str = "Scenario A",
    anomaly_pipeline: Optional[Any] = None,
    anomaly_norm: Optional[Dict] = None,
    anomaly_feature_cols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run a single what-if scenario.

    Parameters
    ----------
    project_features : dict
        Current project feature values (from _extract_project_features in ml_service.py).
    scenario_inputs : dict
        Hypothetical input overrides (validated fields only).
    data_completeness_pct : float
        Data completeness metric.
    scenario_name : str
        Human label for this scenario.
    anomaly_pipeline, anomaly_norm, anomaly_feature_cols : optional
        If provided, anomaly score is recomputed for the scenario.
        If None, anomaly score is estimated via proxy interpolation.

    Returns
    -------
    dict with baseline_signals, scenario_signals, delta, metadata
    """
    # Validate inputs
    is_valid, validated_inputs, validation_messages = validate_scenario_inputs(
        scenario_inputs, project_features, data_completeness_pct
    )

    if not is_valid:
        return {
            "status": "INVALID_INPUT",
            "scenario_name": scenario_name,
            "validation_errors": validation_messages,
            "baseline_signals": None,
            "scenario_signals": None,
            "delta": None,
        }

    # Compute baseline signals
    baseline_signals = _compute_signals(project_features, data_completeness_pct)

    # Apply scenario overrides to a COPY (never mutate original)
    scenario_features = deepcopy(project_features)
    _apply_scenario_overrides(scenario_features, validated_inputs)

    # Compute scenario signals
    scenario_signals = _compute_signals(scenario_features, data_completeness_pct)

    # Optionally recompute anomaly score if pipeline is available
    if anomaly_pipeline is not None and anomaly_feature_cols:
        baseline_anomaly = _recompute_anomaly(
            project_features, anomaly_pipeline, anomaly_norm or {}, anomaly_feature_cols
        )
        scenario_anomaly = _recompute_anomaly(
            scenario_features, anomaly_pipeline, anomaly_norm or {}, anomaly_feature_cols
        )
        baseline_signals["anomaly_score"] = baseline_anomaly
        scenario_signals["anomaly_score"] = scenario_anomaly

    # Compute deltas
    delta = _compute_delta(baseline_signals, scenario_signals)

    # Determine changed inputs for display
    changed_inputs_display = []
    for field, val in validated_inputs.items():
        spec = SIMULATABLE_FIELDS.get(field, {})
        baseline_val = baseline_signals.get("feature_values", {}).get(field)
        changed_inputs_display.append({
            "field": field,
            "display_name": spec.get("display_name", field),
            "baseline_value": baseline_val,
            "scenario_value": val,
            "unit": spec.get("display_unit", ""),
            "data_source": spec.get("data_source", ""),
        })

    return {
        "status": "AVAILABLE",
        "scenario_name": scenario_name,
        "scenario_method": SCENARIO_METHOD_LABEL,
        "disclaimer": SCENARIO_DISCLAIMER,
        "validation_warnings": [m for m in validation_messages if m],
        "changed_inputs": changed_inputs_display,
        "baseline_signals": baseline_signals,
        "scenario_signals": scenario_signals,
        "delta": delta,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
    }


def compare_scenarios(
    project_features: Dict[str, Any],
    scenario_list: List[Dict[str, Any]],
    data_completeness_pct: float = 100.0,
    anomaly_pipeline: Optional[Any] = None,
    anomaly_norm: Optional[Dict] = None,
    anomaly_feature_cols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compare up to 3 scenarios side by side.

    Parameters
    ----------
    scenario_list : list of dicts with keys:
        - name: str
        - inputs: dict of scenario overrides

    Returns
    -------
    dict with comparison table, best scenario, and disclaimers
    """
    if len(scenario_list) > 3:
        return {
            "status": "ERROR",
            "message": "Maximum 3 scenarios can be compared at once.",
        }

    if not scenario_list:
        return {
            "status": "ERROR",
            "message": "At least one scenario is required.",
        }

    results = []
    for sc in scenario_list:
        res = run_scenario(
            project_features=project_features,
            scenario_inputs=sc.get("inputs", {}),
            data_completeness_pct=data_completeness_pct,
            scenario_name=sc.get("name", "Unnamed Scenario"),
            anomaly_pipeline=anomaly_pipeline,
            anomaly_norm=anomaly_norm,
            anomaly_feature_cols=anomaly_feature_cols,
        )
        results.append(res)

    # Identify best scenario by largest overall risk reduction
    best_scenario = None
    best_reduction = 0.0
    for r in results:
        if r["status"] != "AVAILABLE":
            continue
        reduction = r["delta"].get("overall_fingerprint_risk_delta", 0.0)
        if reduction < best_reduction:  # Negative means reduction
            best_reduction = reduction
            best_scenario = r["scenario_name"]

    comparison_table = _build_comparison_table(results)

    return {
        "status": "AVAILABLE",
        "disclaimer": SCENARIO_DISCLAIMER,
        "scenario_method": SCENARIO_METHOD_LABEL,
        "total_scenarios": len(results),
        "scenarios": results,
        "comparison_table": comparison_table,
        "best_scenario": best_scenario,
        "best_scenario_note": (
            f"'{best_scenario}' shows the highest estimated decision-support benefit "
            f"(largest risk signal reduction). This does NOT guarantee it is the best "
            f"real-world intervention — it is a scenario estimate only."
            if best_scenario else None
        ),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _compute_signals(
    features: Dict[str, Any],
    data_completeness_pct: float,
) -> Dict[str, Any]:
    """
    Compute the full Stage Risk Fingerprint using the Phase 3 Stage Risk Engine.
    This is the SAME pipeline as Phase 3 — no new model introduced.
    """
    try:
        from ml.stage_intelligence.stage_risk_engine import compute_stage_fingerprint
        fingerprint = compute_stage_fingerprint(features)

        stage_risks_map = {}
        for s in fingerprint.get("stages", []):
            stage_risks_map[s["stage_id"]] = s.get("risk")

        return {
            "overall_fingerprint_risk": fingerprint.get("overall_fingerprint_risk"),
            "overall_fingerprint_risk_level": fingerprint.get("overall_fingerprint_risk_level"),
            "peak_risk_stage": fingerprint.get("peak_risk_stage"),
            "peak_risk_value": fingerprint.get("peak_risk_value"),
            "stage_risks": stage_risks_map,
            "stages": fingerprint.get("stages", []),
            "anomaly_score": None,  # Filled by anomaly recompute if available
            "feature_values": _extract_key_features(features),
            "data_completeness_pct": data_completeness_pct,
        }
    except Exception as e:
        log.error("Scenario signal computation error: %s", e)
        return {
            "error": str(e),
            "overall_fingerprint_risk": None,
            "stage_risks": {},
            "feature_values": {},
        }


def _apply_scenario_overrides(
    features: Dict[str, Any],
    validated_inputs: Dict[str, Any],
) -> None:
    """
    Apply validated scenario overrides to the features dict IN PLACE.
    This is always called on a DEEP COPY of the original features.
    """
    for field, value in validated_inputs.items():
        if field == "compensation_completion_pct":
            # Update families_compensated derived from this pct
            families = features.get("total_affected_families") or 0
            features["families_compensated"] = int(round(value * families))

        elif field == "area_acquired_pct":
            land_ha = features.get("land_required_ha") or 0
            features["area_acquired_ha"] = round(value * land_ha, 2)

        elif field == "cost_per_ha":
            features["cost_per_ha"] = float(value)
            # Recompute estimated_compensation_inr if area is available
            land_ha = features.get("land_required_ha") or 0
            if land_ha > 0:
                features["estimated_compensation_inr"] = value * land_ha * 10_000_000

        elif field == "total_affected_families":
            features["total_affected_families"] = int(round(value))


def _compute_delta(
    baseline: Dict[str, Any],
    scenario: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute signal deltas between baseline and scenario."""
    b_overall = baseline.get("overall_fingerprint_risk")
    s_overall = scenario.get("overall_fingerprint_risk")

    overall_delta = None
    if b_overall is not None and s_overall is not None:
        overall_delta = round(s_overall - b_overall, 4)

    stage_deltas = {}
    b_stages = baseline.get("stage_risks", {})
    s_stages = scenario.get("stage_risks", {})
    for stage_id in set(list(b_stages.keys()) + list(s_stages.keys())):
        b_val = b_stages.get(stage_id)
        s_val = s_stages.get(stage_id)
        if b_val is not None and s_val is not None:
            stage_deltas[stage_id] = round(s_val - b_val, 4)

    b_anomaly = baseline.get("anomaly_score")
    s_anomaly = scenario.get("anomaly_score")
    anomaly_delta = None
    if b_anomaly is not None and s_anomaly is not None:
        anomaly_delta = round(s_anomaly - b_anomaly, 4)

    return {
        "overall_fingerprint_risk_delta": overall_delta,
        "anomaly_score_delta": anomaly_delta,
        "stage_risk_deltas": stage_deltas,
        "interpretation": _interpret_delta(overall_delta),
        "disclaimer": SCENARIO_DISCLAIMER,
    }


def _interpret_delta(delta: Optional[float]) -> str:
    """Produce a human-readable interpretation of the overall risk delta."""
    if delta is None:
        return "Unable to compute delta — insufficient data in baseline or scenario."
    if delta < -0.10:
        return "Scenario suggests a substantial estimated reduction in overall risk signal."
    if delta < -0.05:
        return "Scenario suggests a moderate estimated reduction in overall risk signal."
    if delta < 0.0:
        return "Scenario suggests a modest estimated reduction in overall risk signal."
    if delta == 0.0:
        return "Scenario shows no change in risk signal for these inputs."
    if delta > 0.0:
        return "Scenario shows an estimated increase in risk signal — review input values."
    return "Delta inconclusive."


def _extract_key_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key feature values for display in scenario output."""
    return {
        "compensation_completion_pct": _safe_div(
            features.get("families_compensated"), features.get("total_affected_families")
        ),
        "area_acquired_pct": _safe_div(
            features.get("area_acquired_ha"), features.get("land_required_ha")
        ),
        "cost_per_ha": features.get("cost_per_ha"),
        "total_affected_families": features.get("total_affected_families"),
        "land_required_ha": features.get("land_required_ha"),
        "state_code": features.get("state_code"),
    }


def _safe_div(numerator: Any, denominator: Any) -> Optional[float]:
    try:
        n = float(numerator)
        d = float(denominator)
        if d > 0:
            return round(n / d, 4)
    except (TypeError, ValueError):
        pass
    return None


def _recompute_anomaly(
    features: Dict[str, Any],
    pipeline: Any,
    norm: Dict,
    feature_cols: List[str],
) -> Optional[float]:
    """Recompute anomaly score using the trained IsolationForest pipeline."""
    try:
        feature_dict = {}
        for col in feature_cols:
            val = features.get(col)
            if col == "land_required_ha_log":
                ha = features.get("land_required_ha")
                val = math.log1p(ha) if ha and ha > 0 else None
            feature_dict[col] = val if val is not None else 0.0

        from ml.training.anomaly_scorer import predict_single
        res = predict_single(pipeline, norm, feature_dict, feature_cols)
        return res.get("anomaly_score")
    except Exception as e:
        log.debug("Scenario anomaly recompute failed (non-critical): %s", e)
        return None


def _build_comparison_table(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build a flat comparison table row per scenario."""
    rows = []
    for r in results:
        if r["status"] != "AVAILABLE":
            rows.append({
                "scenario_name": r.get("scenario_name", ""),
                "status": r["status"],
                "error": r.get("validation_errors", []),
            })
            continue

        b = r.get("baseline_signals", {})
        s = r.get("scenario_signals", {})
        d = r.get("delta", {})

        rows.append({
            "scenario_name": r["scenario_name"],
            "status": "AVAILABLE",
            "changed_inputs": r.get("changed_inputs", []),
            "baseline_overall_risk": b.get("overall_fingerprint_risk"),
            "scenario_overall_risk": s.get("overall_fingerprint_risk"),
            "overall_risk_delta": d.get("overall_fingerprint_risk_delta"),
            "baseline_anomaly_score": b.get("anomaly_score"),
            "scenario_anomaly_score": s.get("anomaly_score"),
            "anomaly_delta": d.get("anomaly_score_delta"),
            "stage_risk_deltas": d.get("stage_risk_deltas", {}),
            "disclaimer": SCENARIO_DISCLAIMER,
        })
    return rows


def get_eligible_simulation_fields(
    project_features: Dict[str, Any],
    data_completeness_pct: float = 100.0,
) -> List[Dict[str, Any]]:
    """Public entry point — return eligible simulation fields for a project."""
    return get_eligible_fields_for_project(project_features, data_completeness_pct)
