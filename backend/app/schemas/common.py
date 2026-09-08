"""
LADRIS — Pydantic Schemas: Common
"""
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Generic paginated API response wrapper."""
    items: List[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int


class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response envelope."""
    success: bool = True
    message: str = "OK"
    data: Optional[DataT] = None


class HealthCheck(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    timestamp: datetime
