"""
LADRIS — Pydantic Schemas: Risk Predictions & Model Registry
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RiskFactorSchema(BaseModel):
    factor_name: str
    factor_category: Optional[str] = "STRUCTURAL"
    importance_score: float
    direction: str  # INCREASES_ANOMALY / DECREASES_ANOMALY
    feature_value: Optional[float] = None
    description: Optional[str] = None


class PredictionResponse(BaseModel):
    prediction_id: Optional[UUID] = None
    project_id: UUID
    prediction_status: str  # AVAILABLE / INSUFFICIENT_DATA / ERROR
    overall_risk_score: float = Field(..., ge=0.0, le=1.0, description="Anomaly / Outlier score between 0.0 and 1.0")
    delay_probability: float = Field(..., ge=0.0, le=1.0, description="Anomaly probability score")
    risk_level: str  # CRITICAL / HIGH / MEDIUM / LOW / UNKNOWN
    predicted_delay_days: Optional[int] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    model_version: str
    model_type: str  # ANOMALY_SCORER / BINARY_CLASSIFIER
    prediction_timestamp: datetime
    data_completeness_pct: float
    as_of_date: Optional[datetime] = None
    authenticity_statement: str
    data_provenance_reference: Dict[str, Any]
    feature_contributions: List[RiskFactorSchema] = []
    message: Optional[str] = None


class InsufficientDataResponse(BaseModel):
    project_id: UUID
    prediction_status: str = "INSUFFICIENT_DATA"
    message: str
    missing_fields: List[str] = []
    data_completeness_pct: float
    recommendation: str


class ExplanationResponse(BaseModel):
    project_id: UUID
    model_version: str
    output_type: str
    disclaimer: str
    top_drivers: List[Dict[str, Any]]
    all_contributions: List[Dict[str, Any]]


class CurrentModelResponse(BaseModel):
    model_name: str
    model_version: str
    model_type: str
    training_date: datetime
    dataset_version: Optional[str]
    record_count_used: int
    evaluation_metrics: Dict[str, Any]
    feature_list: List[str]
    authenticity_statement: str
    data_sources_used: List[str]
    status: str
