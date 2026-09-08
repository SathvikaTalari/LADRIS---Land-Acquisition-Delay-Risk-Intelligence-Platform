"""
LADRIS — Pydantic Schemas: Data Source & Lineage Registry
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class DataSourceResponse(BaseModel):
    id: UUID
    dataset_name: str
    description: Optional[str] = None
    source_organization: str
    source_url: Optional[str] = None
    retrieval_date: Optional[datetime] = None
    data_period_start: Optional[datetime] = None
    data_period_end: Optional[datetime] = None
    data_status: str
    record_count: Optional[int] = None
    file_format: Optional[str] = None
    storage_path: Optional[str] = None
    license: Optional[str] = None
    fields_obtained: List[str] = []
    authenticity_notes: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DataSourceListResponse(BaseModel):
    total: int
    data_sources: List[DataSourceResponse]
