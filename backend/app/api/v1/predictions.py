"""
LADRIS — API v1: Risk Predictions & Model Registry (Phase 3)

Phase 3 New Endpoints:
  GET /api/v1/predictions/{project_id}           — dual-signal risk prediction
  GET /api/v1/predictions/{project_id}/stages    — stage risk fingerprint
  GET /api/v1/predictions/{project_id}/explanation — SHAP explanation
  GET /api/v1/predictions/{project_id}/confidence  — prediction reliability

  GET /api/v1/models/current                     — current model metadata
  GET /api/v1/models/metrics                     — evaluation metrics
  GET /api/v1/models/features                    — feature catalog

  GET /api/v1/data-quality/                      — data quality metrics

RBAC:
  - All prediction endpoints require authenticated user
  - Model management endpoints (metrics, features) require analyst-level access
"""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_analyst
from app.models.project import Project
from app.models.user import User
from app.services.ml_service import (
    get_current_model_info,
    get_data_quality_metrics,
    get_explanation_for_project,
    get_model_features,
    get_model_metrics,
    get_prediction_confidence,
    get_prediction_for_project,
    get_stage_risk_for_project,
)

predictions_router = APIRouter(prefix="/predictions", tags=["Risk Predictions"])
models_router = APIRouter(prefix="/models", tags=["ML Models"])
data_quality_router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


# ─── Prediction Endpoints ─────────────────────────────────────────────────────

@predictions_router.get("/{project_id}")
async def get_project_prediction(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get risk prediction for a project.

    Returns two clearly separated signals:
    - **anomaly_risk**: IsolationForest structural anomaly score (trained on BhoomiRashi data)
    - **delay_risk**: null — supervised delay prediction DEFERRED (no fabricated scores)

    Also returns SHAP feature contributions, data completeness, and provenance.
    If project lacks sufficient data, returns INSUFFICIENT_DATA status.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )
    return get_prediction_for_project(project)


@predictions_router.get("/{project_id}/stages")
async def get_project_stage_prediction(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get Stage Risk Fingerprint for a project.

    Returns proxy-derived risk signals for all 6 acquisition lifecycle stages:
    - NOTIFICATION (real signal from BhoomiRashi 3A/3D dates)
    - OBJECTION, AWARD, COMPENSATION, R&R, POSSESSION (proxy signals)

    All stage signals are clearly labeled as proxy-derived where applicable.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )
    return get_stage_risk_for_project(project)


@predictions_router.get("/{project_id}/explanation")
async def get_prediction_explanation(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get SHAP feature contribution explanation for a project's anomaly risk score.

    Returns model-supported risk contributors (positive and negative) with
    human-readable interpretations. These are NOT causal explanations of delay.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )
    return get_explanation_for_project(project)


@predictions_router.get("/{project_id}/confidence")
async def get_prediction_confidence_endpoint(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get prediction reliability assessment for a project.

    Returns:
    - data_completeness_pct
    - out_of_distribution indicator (z-score based)
    - confidence_assessment (HIGH / MEDIUM / LOW)
    - calibration notes
    - prediction_eligible flag
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )
    return get_prediction_confidence(project)


# ─── Model Management Endpoints ───────────────────────────────────────────────

@models_router.get("/current")
async def get_current_model(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get metadata for the currently active ML model.
    Returns model version, training date, dataset version, feature list.
    """
    return get_current_model_info()


@models_router.get("/metrics")
async def get_model_metrics_endpoint(
    current_user: User = Depends(require_analyst),
) -> Dict[str, Any]:
    """
    Get evaluation metrics for the current model.

    Supervised metrics (precision, recall, F1, AUC, Brier) are N/A while
    supervised training is deferred. Anomaly scorer metrics are available.

    Requires analyst-level access or higher.
    """
    return get_model_metrics()


@models_router.get("/features")
async def get_model_features_endpoint(
    current_user: User = Depends(require_analyst),
) -> Dict[str, Any]:
    """
    Get the feature catalog for the current model.

    Returns: available features, unavailable features, leakage annotations,
    and feature descriptions.

    Requires analyst-level access or higher.
    """
    return get_model_features()


# ─── Data Quality Endpoint ────────────────────────────────────────────────────

@data_quality_router.get("/")
async def get_data_quality_report(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get data quality summary metrics computed from actual ingested public datasets.
    """
    return get_data_quality_metrics()
