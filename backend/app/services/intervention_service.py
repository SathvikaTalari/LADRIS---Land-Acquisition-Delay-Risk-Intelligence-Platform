"""
LADRIS — Intervention Intelligence Service (Phase 4)
==========================================================
Core bridge connecting ML intervention engine to the FastAPI application.

Functions:
  get_interventions_for_project(project, db) — maps stage risks → candidate interventions
  get_intervention_priority(project, db) — ranked interventions with score breakdown
  simulate_scenario(project, scenario_inputs, db, user_id) — read-only what-if simulation
  compare_scenarios(project, scenario_list, db, user_id) — multi-scenario comparison
  get_intervention_catalog() — full catalog
  get_intervention_evidence(project_id, project, db) — provenance per recommendation

IMPORTANT:
  - Simulation is STRICTLY read-only. No project records are modified.
  - All scenario records stored in intervention_scenarios table have
    record_type = 'SCENARIO — NOT ACTUAL GOVERNMENT ACTION'.
  - The intervention service calls the Phase 3 ML service for risk signals —
    it does not reimplement or override the Phase 3 pipeline.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

log = logging.getLogger(__name__)

# Resolve ML package path
BACKEND_DIR = Path(__file__).parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent
ML_DIR = Path("/ml") if Path("/ml").exists() else (ROOT_DIR / "ml")

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ML_DIR.parent))

MODEL_VERSION = "v1.0-phase4"


# ─── Internal: Extract Extended Features ─────────────────────────────────────

def _extract_extended_features(project: Any) -> Dict[str, Any]:
    """
    Extract features for intervention engine, extending Phase 3 feature set
    with additional fields needed by the scenario engine.
    """
    import math

    area_ha = float(project.total_area_ha) if project.total_area_ha else None
    comp_inr = float(project.estimated_compensation_inr) if project.estimated_compensation_inr else None
    cost_crore = comp_inr / 10_000_000.0 if comp_inr else None
    cost_per_ha = cost_crore / max(area_ha, 0.01) if (cost_crore and area_ha) else None

    state_str = (getattr(project, "state_code", None) or "MH").upper().strip()
    agency_str = (getattr(project, "executing_agency", None) or "NHAI").upper().strip()

    has_3d = str(getattr(project, "status", "")).upper() in (
        "APPROVED", "ACTIVE", "DELAYED", "COMPLETED"
    )

    families = getattr(project, "total_affected_families", None)
    compensated = getattr(project, "families_compensated", None)
    rehabilitated = getattr(project, "families_rehabilitated", None)
    area_acquired = float(getattr(project, "area_acquired_ha", None) or 0)
    area_in_possession = float(getattr(project, "area_in_possession_ha", None) or 0)

    return {
        # Phase 3 features
        "land_required_ha_log": math.log1p(area_ha) if area_ha and area_ha > 0 else None,
        "cost_per_ha": cost_per_ha,
        "has_3a_notification": 1,
        "has_3d_notification": 1 if has_3d else 0,
        "state_encoded": 10,  # fallback
        "agency_encoded": 0,
        # Raw values
        "land_required_ha": area_ha,
        "state_code": state_str,
        "executing_agency": agency_str,
        "total_affected_families": int(families) if families else None,
        "families_compensated": int(compensated) if compensated else None,
        "families_rehabilitated": int(rehabilitated) if rehabilitated else None,
        "area_acquired_ha": area_acquired,
        "area_in_possession_ha": area_in_possession,
        "notification_interval_days": None,
    }


# ─── Get Interventions ────────────────────────────────────────────────────────

async def get_interventions_for_project(project: Any) -> Dict[str, Any]:
    """
    Map project risk signals → candidate interventions using the rule engine.
    """
    from app.services.ml_service import (
        get_prediction_for_project,
        get_stage_risk_for_project,
        calculate_project_completeness,
    )

    project_id = str(project.id)
    completeness_pct, _ = calculate_project_completeness(project)
    features = _extract_extended_features(project)

    # Get Phase 3 signals
    prediction = get_prediction_for_project(project)
    anomaly_score = None
    if prediction.get("anomaly_risk"):
        anomaly_score = prediction["anomaly_risk"].get("score")

    fingerprint = get_stage_risk_for_project(project)
    stage_risks = fingerprint.get("stages", [])

    # Get SHAP contributors
    shap_contributors = []
    shap_exp = prediction.get("shap_explanation") or {}
    if isinstance(shap_exp, dict):
        shap_contributors = (
            shap_exp.get("top_positive_contributors", []) +
            shap_exp.get("top_negative_contributors", [])
        )
    else:
        shap_contributors = prediction.get("feature_contributions", [])

    try:
        from ml.interventions.rule_engine import map_risks_to_interventions
        result = map_risks_to_interventions(
            stage_risks=stage_risks,
            anomaly_score=anomaly_score,
            shap_contributors=shap_contributors,
            project_features=features,
            data_completeness_pct=completeness_pct,
        )
    except Exception as e:
        log.error("Intervention mapping error for %s: %s", project_id, e)
        result = {
            "status": "ERROR",
            "message": f"Intervention engine error: {str(e)}",
            "candidate_interventions": [],
            "rules_fired": [],
        }

    result["project_id"] = project_id
    result["data_completeness_pct"] = completeness_pct
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ─── Get Priority ─────────────────────────────────────────────────────────────

async def get_intervention_priority(project: Any) -> Dict[str, Any]:
    """
    Return ranked intervention list with full priority score breakdown.
    """
    from app.services.ml_service import calculate_project_completeness
    completeness_pct, _ = calculate_project_completeness(project)

    base = await get_interventions_for_project(project)
    interventions = base.get("candidate_interventions", [])

    from ml.interventions.priority_scorer import PRIORITY_WEIGHTS, PRIORITY_SCORE_NOTE

    return {
        "project_id": str(project.id),
        "status": base.get("status", "AVAILABLE"),
        "ranked_interventions": interventions,
        "top_priority": interventions[0] if interventions else None,
        "priority_score_label": "Decision-Support Priority Score",
        "scoring_methodology": PRIORITY_SCORE_NOTE,
        "weights": PRIORITY_WEIGHTS,
        "data_completeness_pct": completeness_pct,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Simulate Scenario ────────────────────────────────────────────────────────

async def simulate_scenario(
    project: Any,
    scenario_name: str,
    inputs: Dict[str, float],
    db: Any,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a single what-if scenario. Strictly read-only — no project records modified.
    Writes an audit record to intervention_scenarios.
    """
    from app.services.ml_service import calculate_project_completeness
    completeness_pct, _ = calculate_project_completeness(project)
    features = _extract_extended_features(project)
    project_id = str(project.id)

    # Load anomaly pipeline for optional recompute
    pipeline, meta, norm = _load_anomaly_pipeline()
    feature_cols = meta.get("feature_list", []) if meta else []

    try:
        from ml.scenario.engine import run_scenario
        result = run_scenario(
            project_features=features,
            scenario_inputs=inputs,
            data_completeness_pct=completeness_pct,
            scenario_name=scenario_name,
            anomaly_pipeline=pipeline,
            anomaly_norm=norm,
            anomaly_feature_cols=feature_cols,
        )
    except Exception as e:
        log.error("Scenario engine error for %s: %s", project_id, e)
        result = {
            "status": "ERROR",
            "scenario_name": scenario_name,
            "validation_errors": [str(e)],
            "baseline_signals": None,
            "scenario_signals": None,
            "delta": None,
            "changed_inputs": [],
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "model_version": MODEL_VERSION,
            "disclaimer": "Scenario estimate — not a causal prediction.",
            "scenario_method": "Model/Rule-Based Scenario",
            "validation_warnings": [],
        }

    # Get eligible fields for display
    from ml.scenario.engine import get_eligible_simulation_fields
    eligible_fields = get_eligible_simulation_fields(features, completeness_pct)

    # Write audit trail (non-blocking)
    audit_id = None
    try:
        audit_id = await _write_scenario_audit(
            db=db,
            project_id=project_id,
            scenario_name=scenario_name,
            scenario_inputs=inputs,
            result=result,
            user_id=user_id,
        )
    except Exception as ae:
        log.warning("Scenario audit write failed (non-critical): %s", ae)

    return {
        "project_id": project_id,
        "scenario_result": result,
        "eligible_fields": eligible_fields,
        "audit_id": audit_id,
        "scenario_estimate_notice": (
            "Scenario estimate — not a causal prediction. "
            "This simulation re-runs the deterministic rule-based risk pipeline "
            "with hypothetical inputs. It does not use a supervised delay model."
        ),
    }


# ─── Compare Scenarios ────────────────────────────────────────────────────────

async def compare_scenarios(
    project: Any,
    scenario_list: List[Dict[str, Any]],
    db: Any,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare up to 3 what-if scenarios side by side.
    """
    from app.services.ml_service import calculate_project_completeness
    completeness_pct, _ = calculate_project_completeness(project)
    features = _extract_extended_features(project)
    project_id = str(project.id)

    pipeline, meta, norm = _load_anomaly_pipeline()
    feature_cols = meta.get("feature_list", []) if meta else []

    try:
        from ml.scenario.engine import compare_scenarios as engine_compare
        result = engine_compare(
            project_features=features,
            scenario_list=scenario_list,
            data_completeness_pct=completeness_pct,
            anomaly_pipeline=pipeline,
            anomaly_norm=norm,
            anomaly_feature_cols=feature_cols,
        )
    except Exception as e:
        log.error("Multi-scenario comparison error for %s: %s", project_id, e)
        return {
            "project_id": project_id,
            "status": "ERROR",
            "message": str(e),
        }

    result["project_id"] = project_id
    result["scenario_estimate_notice"] = (
        "Scenario estimates — not causal predictions. "
        "Best scenario is labeled 'Highest estimated decision-support benefit' only."
    )

    return result


# ─── Get Catalog ──────────────────────────────────────────────────────────────

def get_intervention_catalog() -> Dict[str, Any]:
    """Return the full intervention catalog with metadata."""
    from ml.interventions.catalog import INTERVENTION_CATALOG, CATALOG_METADATA
    return {
        **CATALOG_METADATA,
        "interventions": INTERVENTION_CATALOG,
    }


# ─── Get Evidence ─────────────────────────────────────────────────────────────

async def get_intervention_evidence(project: Any) -> Dict[str, Any]:
    """Return evidence/provenance for all recommendations for this project."""
    from app.services.ml_service import calculate_project_completeness
    completeness_pct, _ = calculate_project_completeness(project)

    base = await get_interventions_for_project(project)
    interventions = base.get("candidate_interventions", [])

    evidence_records = [
        {
            "intervention_id": item["intervention_id"],
            "category": item["category"],
            "stage": item["stage"],
            "evidence": item["evidence"],
            "provenance": item["provenance"],
            "confidence": item["confidence"],
            "applicable_risk_factors": [],
            "non_causal_note": item["non_causal_note"],
        }
        for item in interventions
    ]

    return {
        "project_id": str(project.id),
        "recommendations_count": len(evidence_records),
        "evidence_records": evidence_records,
        "data_completeness_pct": completeness_pct,
        "provenance_disclaimer": (
            "All evidence references are from official public data sources: "
            "BhoomiRashi (MoRTH), Data.gov.in, and MoRTH Annual Reports. "
            "No evidence is fabricated."
        ),
    }


# ─── Get District Intelligence ────────────────────────────────────────────────

async def get_district_intelligence(db: Any) -> Dict[str, Any]:
    """
    Compute district-level bottleneck summary from available project data.
    Only surfaces results where sample size is sufficient.
    Always displays sample size prominently.
    """
    from sqlalchemy import select, func
    from app.models.project import Project

    try:
        result = await db.execute(
            select(
                Project.state_code,
                func.count(Project.id).label("project_count"),
            )
            .where(Project.deleted_at.is_(None))
            .group_by(Project.state_code)
            .order_by(func.count(Project.id).desc())
        )
        rows = result.fetchall()
    except Exception as e:
        log.error("District intelligence DB error: %s", e)
        return {"status": "ERROR", "message": str(e)}

    if not rows:
        return {
            "status": "NO_DATA",
            "message": "No project data available for district intelligence.",
            "districts": [],
        }

    total_projects = sum(r.project_count for r in rows)
    districts = []
    for row in rows:
        n = row.project_count
        districts.append({
            "state_code": row.state_code,
            "project_count": n,
            "sample_size_note": (
                f"Based on {n} project(s). "
                + ("Patterns may not be statistically robust." if n < 5 else "")
            ),
            "sufficient_sample": n >= 3,
        })

    return {
        "status": "AVAILABLE",
        "total_projects": total_projects,
        "districts": districts,
        "sample_size_warning": (
            "All district-level statistics reflect the available project sample only. "
            "Do not make policy claims from small samples. "
            "Sample sizes are displayed prominently for each district."
        ),
    }


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _load_anomaly_pipeline():
    """Load the Phase 3 IsolationForest pipeline for optional scenario recompute."""
    try:
        import json
        from pathlib import Path
        models_dir = ML_DIR / "models"
        meta_file = models_dir / "current_model.json"
        if not meta_file.exists():
            return None, None, None
        meta = json.loads(meta_file.read_bytes().decode("utf-8", errors="replace"))
        model_path = models_dir / Path(meta.get("model_path", "")).name
        norm_path = models_dir / Path(meta.get("preprocessing_path", "")).name
        if not model_path.exists():
            return None, meta, None
        import pickle
        with model_path.open("rb") as f:
            pipeline = pickle.load(f)
        norm = json.loads(norm_path.read_bytes().decode("utf-8", errors="replace")) if norm_path.exists() else {}
        return pipeline, meta, norm
    except Exception as e:
        log.debug("Pipeline load (non-critical): %s", e)
        return None, None, None


async def _write_scenario_audit(
    db: Any,
    project_id: str,
    scenario_name: str,
    scenario_inputs: Dict[str, Any],
    result: Dict[str, Any],
    user_id: Optional[str],
) -> Optional[str]:
    """
    Write a scenario audit record to intervention_scenarios.
    Returns the created record ID.
    """
    from uuid import uuid4
    from app.models.ml_models import InterventionScenario

    baseline = result.get("baseline_signals") or {}
    scenario = result.get("scenario_signals") or {}
    delta = result.get("delta") or {}

    record = InterventionScenario(
        id=uuid4(),
        project_id=project_id,
        scenario_name=scenario_name,
        scenario_inputs=scenario_inputs,
        baseline_signals=baseline,
        scenario_signals=scenario,
        delta_signals=delta,
        model_version=MODEL_VERSION,
        data_version="v1.0-bhoomirashi-2024",
        created_by=UUID(user_id) if user_id else None,
        record_type="SCENARIO — NOT ACTUAL GOVERNMENT ACTION",
    )
    db.add(record)
    await db.flush()
    return str(record.id)
