"""
LADRIS — Pydantic Schemas: Data Quality Dashboard
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class DataQualitySummary(BaseModel):
    total_real_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_value_rate: float
    source_coverage_count: int
    prediction_eligible_records: int
    quality_issues_count: int
    generated_at: datetime
    data_authenticity_statement: str


class DataQualityResponse(BaseModel):
    summary: DataQualitySummary
    recent_issues: List[Dict[str, Any]] = []
    field_null_rates: Dict[str, float] = {}
    sources: List[Dict[str, Any]] = []
