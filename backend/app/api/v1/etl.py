"""
LADRIS — ETL Admin API
==============================
Endpoints for triggering and monitoring the real data ETL pipeline.

Prefix: /api/v1/etl/
Requires: SUPER_ADMIN role

Endpoints:
  POST /etl/trigger          — Start full ETL run (background task)
  GET  /etl/status           — Get last ETL run stats & DB data summary
  GET  /etl/districts        — List all loaded district centroids
  GET  /etl/data-sources     — Summary of records per data source
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.etl.db_loader import get_real_data_summary

log = logging.getLogger(__name__)

etl_router = APIRouter(prefix="/etl", tags=["ETL Data Ingestion"])

# In-memory ETL run state (sufficient for single-process deployment)
_etl_state: Dict[str, Any] = {
    "status": "idle",
    "last_run_id": None,
    "last_run_at": None,
    "last_stats": None,
    "running": False,
}


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.SUPER_ADMIN,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ETL operations require SUPER_ADMIN role",
        )
    return current_user


async def _run_etl_background(phases: List[int]):
    """Background task wrapper for the ETL pipeline."""
    global _etl_state
    _etl_state["status"] = "running"
    _etl_state["running"] = True

    try:
        from app.etl.pipeline import ETLPipeline
        pipeline = ETLPipeline(phases=phases)
        stats = await pipeline.run()
        _etl_state["status"] = "completed"
        _etl_state["last_run_id"] = stats.get("run_id")
        _etl_state["last_run_at"] = stats.get("completed_at")
        _etl_state["last_stats"] = stats
        log.info(f"ETL pipeline completed: {stats.get('run_id')}")
    except Exception as e:
        _etl_state["status"] = "failed"
        _etl_state["last_stats"] = {"error": str(e)}
        log.error(f"ETL pipeline failed: {e}")
    finally:
        _etl_state["running"] = False


@etl_router.post("/trigger")
async def trigger_etl(
    background_tasks: BackgroundTasks,
    phases: str = Query(
        default="1,2,3,4,5",
        description="Comma-separated phase numbers: 1=GIS/Census, 2=data.gov.in, 3=BhoomiRashi, 4=Normalize, 5=DB",
    ),
    current_user: User = Depends(_require_admin),
) -> Dict[str, Any]:
    """
    Trigger the real data ETL pipeline as a background task.

    Phases:
    - **1** — Load GIS district centroids & Census 2011 from bundled files
    - **2** — Fetch data.gov.in open datasets (requires DATA_GOV_IN_API_KEY in .env)
    - **3** — Scrape BhoomiRashi public Highway Register (all states, all agencies)
    - **4** — Normalize & deduplicate all collected project records
    - **5** — Upsert everything into PostgreSQL (projects + districts tables)
    """
    if _etl_state["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ETL pipeline is already running. Check /etl/status for progress.",
        )

    try:
        phase_list = [int(p.strip()) for p in phases.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid phases format: {phases}")

    _etl_state["status"] = "starting"
    background_tasks.add_task(_run_etl_background, phase_list)

    return {
        "message": "ETL pipeline started in background",
        "phases": phase_list,
        "triggered_by": current_user.email,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "monitor_at": "/api/v1/etl/status",
        "phase_descriptions": {
            1: "GIS District Centroids + Census 2011",
            2: "data.gov.in Open Government Datasets",
            3: "BhoomiRashi Highway Register Scraper",
            4: "Normalize + Deduplicate",
            5: "PostgreSQL Upsert",
        },
    }


@etl_router.get("/status")
async def get_etl_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current ETL pipeline status and database data summary.
    Shows how many records are loaded from each real data source.
    """
    db_summary = await get_real_data_summary(db)

    return {
        "pipeline": {
            "status": _etl_state["status"],
            "running": _etl_state["running"],
            "last_run_id": _etl_state["last_run_id"],
            "last_run_at": _etl_state["last_run_at"],
            "last_stats": _etl_state["last_stats"],
        },
        "database": db_summary,
        "credentials_status": await _check_credentials_status(),
        "data_files_status": _check_data_files_status(),
    }


@etl_router.get("/districts")
async def get_districts(
    state_code: Optional[str] = None,
    limit: int = Query(default=100, le=800),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List all loaded district centroids from the districts table.
    Used by GIS heatmap to place markers at real coordinates.
    """
    try:
        query = "SELECT district_code, district_name, state_code, state_name, centroid_lat, centroid_lng, total_population, area_sq_km, data_source FROM districts"
        params = {}
        if state_code:
            query += " WHERE state_code = :state_code"
            params["state_code"] = state_code.upper()
        query += " ORDER BY state_code, district_name LIMIT :limit"
        params["limit"] = limit

        result = await db.execute(text(query), params)
        rows = result.fetchall()

        districts = [
            {
                "district_code": r[0],
                "district_name": r[1],
                "state_code": r[2],
                "state_name": r[3],
                "centroid_lat": float(r[4]) if r[4] else None,
                "centroid_lng": float(r[5]) if r[5] else None,
                "total_population": r[6],
                "area_sq_km": float(r[7]) if r[7] else None,
                "data_source": r[8],
            }
            for r in rows
        ]

        return {
            "districts": districts,
            "count": len(districts),
            "state_filter": state_code,
        }
    except Exception as e:
        log.error(f"Error fetching districts: {e}")
        raise HTTPException(status_code=500, detail="Districts table not available. Run ETL Phase 1 first.")


@etl_router.get("/data-sources")
async def get_data_sources_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns count of project records by data source label.
    Useful for the Data Trust / Provenance panel.
    """
    summary = await get_real_data_summary(db)

    # Compute trust metrics
    sources = summary.get("project_sources", [])
    total = sum(s["count"] for s in sources)
    real = sum(s["count"] for s in sources if "SYNTHETIC" not in (s.get("source") or "").upper())
    with_coords = sum(s.get("with_coords", 0) for s in sources)
    with_area = sum(s.get("with_area", 0) for s in sources)

    completeness = round(with_area / max(1, total) * 100, 1)
    geo_coverage = round(with_coords / max(1, total) * 100, 1)
    real_data_pct = round(real / max(1, total) * 100, 1)
    trust_score = round((completeness * 0.4 + geo_coverage * 0.3 + real_data_pct * 0.3), 0)

    return {
        "total_projects": total,
        "real_data_count": real,
        "synthetic_count": total - real,
        "real_data_percentage": real_data_pct,
        "trust_metrics": {
            "trust_score": int(trust_score),
            "completeness_pct": completeness,
            "geo_coverage_pct": geo_coverage,
            "real_data_pct": real_data_pct,
        },
        "by_source": sources,
        "district_records": summary.get("district_records", 0),
        "last_updated": summary.get("summary_timestamp"),
    }


async def _check_credentials_status() -> Dict[str, Any]:
    """Check which API credentials are configured."""
    from app.config import get_settings
    settings = get_settings()
    return {
        "DATA_GOV_IN_API_KEY": "SET" if settings.DATAGOV_API_KEY else "MISSING — register at https://data.gov.in",
        "BHOOMIRASHI": "NO_KEY_NEEDED — public scraping",
        "ECOURTS": "NO_KEY_NEEDED — public search",
        "SURVEY_OF_INDIA": "NO_KEY_NEEDED — bundled files",
        "CENSUS_INDIA": "NO_KEY_NEEDED — bundled files",
    }


def _check_data_files_status() -> Dict[str, Any]:
    """Check which bundled data files are present."""
    import os
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    base = os.path.normpath(base)

    files = {
        "district_census_2011.csv": os.path.join(base, "census", "district_census_2011.csv"),
        "india_districts_centroids.csv": os.path.join(base, "gis", "india_districts_centroids.csv"),
        "india_districts.geojson": os.path.join(base, "gis", "india_districts.geojson"),
    }

    return {
        name: {
            "present": os.path.exists(path),
            "path": path,
            "size_mb": round(os.path.getsize(path) / 1_000_000, 2) if os.path.exists(path) else 0,
        }
        for name, path in files.items()
    }
