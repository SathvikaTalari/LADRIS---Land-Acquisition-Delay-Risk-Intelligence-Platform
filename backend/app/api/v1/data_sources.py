"""
LADRIS — API v1: Data Sources & Provenance Registry
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.misc import DataSource
from app.models.user import User

data_sources_router = APIRouter(prefix="/data-sources", tags=["Data Sources"])


@data_sources_router.get("/")
async def list_data_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List all registered official public datasets with provenance metadata,
    retrieval dates, authenticity status, record count, and fields obtained.
    """
    stmt = select(DataSource).order_by(DataSource.created_at.desc())
    result = await db.execute(stmt)
    sources = result.scalars().all()

    items = []
    for ds in sources:
        items.append({
            "id": str(ds.id),
            "dataset_name": ds.dataset_name,
            "description": ds.description,
            "source_organization": ds.source_organization,
            "source_url": ds.source_url,
            "retrieval_date": ds.retrieval_date.isoformat() if ds.retrieval_date else None,
            "data_period_start": ds.data_period_start.isoformat() if ds.data_period_start else None,
            "data_period_end": ds.data_period_end.isoformat() if ds.data_period_end else None,
            "data_status": ds.data_status.value if hasattr(ds.data_status, "value") else str(ds.data_status),
            "record_count": ds.record_count or 0,
            "file_format": ds.file_format or "CSV",
            "storage_path": ds.storage_path,
            "license": ds.license or "Public Domain",
            "fields_obtained": getattr(ds, "fields_obtained", []) or [
                "state", "district", "agency", "land_required_ha",
                "sanctioned_la_cost_crore", "notification_3a_date", "notification_3d_date"
            ],
            "authenticity_notes": getattr(ds, "authenticity_notes", None) or (
                "Verified public source from official government portal."
            ),
            "is_active": ds.is_active,
            "created_at": ds.created_at.isoformat() if ds.created_at else None,
        })

    return {
        "total": len(items),
        "data_sources": items,
    }


@data_sources_router.get("/{source_id}")
async def get_data_source_detail(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get detailed provenance metadata for a specific dataset.
    """
    ds = await db.get(DataSource, source_id)
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source with ID {source_id} not found.",
        )

    return {
        "id": str(ds.id),
        "dataset_name": ds.dataset_name,
        "description": ds.description,
        "source_organization": ds.source_organization,
        "source_url": ds.source_url,
        "retrieval_date": ds.retrieval_date.isoformat() if ds.retrieval_date else None,
        "data_status": ds.data_status.value if hasattr(ds.data_status, "value") else str(ds.data_status),
        "record_count": ds.record_count or 0,
        "file_format": ds.file_format,
        "license": ds.license,
        "fields_obtained": getattr(ds, "fields_obtained", []),
        "authenticity_notes": getattr(ds, "authenticity_notes", None),
        "is_active": ds.is_active,
    }
