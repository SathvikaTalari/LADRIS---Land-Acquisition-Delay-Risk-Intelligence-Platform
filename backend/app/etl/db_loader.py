"""
LADRIS — Database Upserter
=================================
Takes normalized project dicts and upserts them into the PostgreSQL projects table.
Also manages the districts table for GIS centroids and Census data.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def upsert_projects(
    db: AsyncSession,
    projects: List[Dict[str, Any]],
    batch_size: int = 50,
) -> Dict[str, int]:
    """
    Upsert normalized project dicts into the projects table.
    Uses ON CONFLICT (project_code) DO UPDATE to handle re-runs.
    Returns counts of inserted and updated records.
    """
    inserted = 0
    updated = 0
    errors = 0

    for i in range(0, len(projects), batch_size):
        batch = projects[i:i + batch_size]
        for p in batch:
            try:
                await _upsert_single_project(db, p)
                inserted += 1
            except Exception as e:
                logger.debug(f"Upsert error for {p.get('project_code')}: {e}")
                errors += 1

        await db.commit()
        logger.info(f"Upserted batch {i//batch_size + 1} ({min(i+batch_size, len(projects))}/{len(projects)})")

    logger.info(f"Project upsert complete: {inserted} ok, {errors} errors")
    return {"inserted": inserted, "updated": updated, "errors": errors}


async def _upsert_single_project(db: AsyncSession, p: Dict[str, Any]):
    """Upsert a single project record."""
    project_id = p.get("id") or str(uuid.uuid4())

    # Convert dates to strings for SQL
    def fmt_date(d):
        if d is None:
            return None
        if hasattr(d, "isoformat"):
            return d.isoformat()
        return str(d)

    def fmt_float(v):
        try:
            if v is None:
                return None
            f = float(v)
            return f if f > 0 else None
        except (TypeError, ValueError):
            return None

    def fmt_int(v):
        try:
            if v is None:
                return 0
            return int(v)
        except (TypeError, ValueError):
            return 0

    stmt = text("""
        INSERT INTO projects (
            id, project_code, name, description,
            project_type, acquisition_act, status, risk_level,
            nodal_agency, executing_agency,
            state_code, district_codes,
            total_area_ha, area_acquired_ha, area_in_possession_ha,
            total_affected_families, families_compensated, families_rehabilitated,
            planned_start_date, planned_end_date,
            estimated_compensation_inr, disbursed_compensation_inr,
            notification_3a_date, notification_3d_date,
            delay_months, legal_case_count, legal_case_status,
            milestone_data_status, latitude, longitude,
            lacrris_integration_status,
            created_at, updated_at
        ) VALUES (
            :id, :project_code, :name, :description,
            :project_type, :acquisition_act, :status, :risk_level,
            :nodal_agency, :executing_agency,
            :state_code, :district_codes,
            :total_area_ha, :area_acquired_ha, :area_in_possession_ha,
            :total_affected_families, :families_compensated, :families_rehabilitated,
            :planned_start_date, :planned_end_date,
            :estimated_compensation_inr, :disbursed_compensation_inr,
            :notification_3a_date, :notification_3d_date,
            :delay_months, :legal_case_count, :legal_case_status,
            :milestone_data_status, :latitude, :longitude,
            :lacrris_integration_status,
            NOW(), NOW()
        )
        ON CONFLICT (project_code) DO UPDATE SET
            name = EXCLUDED.name,
            status = EXCLUDED.status,
            risk_level = EXCLUDED.risk_level,
            total_area_ha = COALESCE(EXCLUDED.total_area_ha, projects.total_area_ha),
            area_acquired_ha = COALESCE(EXCLUDED.area_acquired_ha, projects.area_acquired_ha),
            area_in_possession_ha = COALESCE(EXCLUDED.area_in_possession_ha, projects.area_in_possession_ha),
            delay_months = GREATEST(EXCLUDED.delay_months, projects.delay_months),
            legal_case_count = COALESCE(EXCLUDED.legal_case_count, projects.legal_case_count),
            notification_3a_date = COALESCE(EXCLUDED.notification_3a_date, projects.notification_3a_date),
            notification_3d_date = COALESCE(EXCLUDED.notification_3d_date, projects.notification_3d_date),
            milestone_data_status = EXCLUDED.milestone_data_status,
            latitude = COALESCE(EXCLUDED.latitude, projects.latitude),
            longitude = COALESCE(EXCLUDED.longitude, projects.longitude),
            lacrris_integration_status = EXCLUDED.lacrris_integration_status,
            updated_at = NOW()
    """)

    district_codes = p.get("district_codes") or []

    await db.execute(stmt, {
        "id": project_id,
        "project_code": p["project_code"],
        "name": p["name"][:500],
        "description": (p.get("description") or "")[:1000],
        "project_type": p.get("project_type", "HIGHWAY"),
        "acquisition_act": p.get("acquisition_act", "NH_ACT_1956"),
        "status": p.get("status", "ACTIVE"),
        "risk_level": p.get("risk_level", "UNKNOWN"),
        "nodal_agency": p.get("nodal_agency", "MoRTH"),
        "executing_agency": p.get("executing_agency", "NHAI"),
        "state_code": p["state_code"],
        "district_codes": district_codes,
        "total_area_ha": fmt_float(p.get("total_area_ha")),
        "area_acquired_ha": fmt_float(p.get("area_acquired_ha")),
        "area_in_possession_ha": fmt_float(p.get("area_in_possession_ha")),
        "total_affected_families": fmt_int(p.get("total_affected_families")),
        "families_compensated": fmt_int(p.get("families_compensated")),
        "families_rehabilitated": fmt_int(p.get("families_rehabilitated")),
        "planned_start_date": fmt_date(p.get("planned_start_date")),
        "planned_end_date": fmt_date(p.get("planned_end_date")),
        "estimated_compensation_inr": fmt_float(p.get("estimated_compensation_inr")),
        "disbursed_compensation_inr": fmt_float(p.get("disbursed_compensation_inr")),
        "notification_3a_date": fmt_date(p.get("notification_3a_date")),
        "notification_3d_date": fmt_date(p.get("notification_3d_date")),
        "delay_months": fmt_int(p.get("delay_months")),
        "legal_case_count": fmt_int(p.get("legal_case_count")),
        "legal_case_status": p.get("legal_case_status", "NONE"),
        "milestone_data_status": p.get("milestone_data_status", "REAL_DERIVED"),
        "latitude": fmt_float(p.get("latitude")),
        "longitude": fmt_float(p.get("longitude")),
        "lacrris_integration_status": p.get("lacrris_integration_status", "INTEGRATED"),
    })


async def upsert_districts(
    db: AsyncSession,
    districts: List[Dict[str, Any]],
) -> int:
    """
    Upsert district centroid + census data into the districts table.
    Creates the table if it doesn't exist.
    """
    # Ensure districts table exists
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS districts (
            id              SERIAL PRIMARY KEY,
            district_code   VARCHAR(20),
            district_name   VARCHAR(200) NOT NULL,
            state_code      VARCHAR(3) NOT NULL,
            state_name      VARCHAR(200),
            centroid_lat    NUMERIC(9,6),
            centroid_lng    NUMERIC(9,6),
            total_population BIGINT DEFAULT 0,
            rural_population BIGINT DEFAULT 0,
            urban_population BIGINT DEFAULT 0,
            total_households BIGINT DEFAULT 0,
            area_sq_km      NUMERIC(12,2),
            boundary_geojson TEXT,
            data_source     VARCHAR(100),
            created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(district_name, state_code)
        )
    """))
    await db.commit()

    count = 0
    for d in districts:
        try:
            await db.execute(text("""
                INSERT INTO districts (
                    district_code, district_name, state_code, state_name,
                    centroid_lat, centroid_lng,
                    total_population, rural_population, urban_population,
                    total_households, area_sq_km, boundary_geojson, data_source,
                    updated_at
                ) VALUES (
                    :district_code, :district_name, :state_code, :state_name,
                    :centroid_lat, :centroid_lng,
                    :total_population, :rural_population, :urban_population,
                    :total_households, :area_sq_km, :boundary_geojson, :data_source,
                    NOW()
                )
                ON CONFLICT (district_name, state_code) DO UPDATE SET
                    centroid_lat = COALESCE(EXCLUDED.centroid_lat, districts.centroid_lat),
                    centroid_lng = COALESCE(EXCLUDED.centroid_lng, districts.centroid_lng),
                    total_population = COALESCE(EXCLUDED.total_population, districts.total_population),
                    area_sq_km = COALESCE(EXCLUDED.area_sq_km, districts.area_sq_km),
                    boundary_geojson = COALESCE(EXCLUDED.boundary_geojson, districts.boundary_geojson),
                    data_source = EXCLUDED.data_source,
                    updated_at = NOW()
            """), {
                "district_code": d.get("district_code", ""),
                "district_name": d.get("district_name", "")[:200],
                "state_code": d.get("state_code", "XX"),
                "state_name": d.get("state_name", ""),
                "centroid_lat": d.get("centroid_lat"),
                "centroid_lng": d.get("centroid_lng"),
                "total_population": d.get("total_population", 0),
                "rural_population": d.get("rural_population", 0),
                "urban_population": d.get("urban_population", 0),
                "total_households": d.get("total_households", 0),
                "area_sq_km": d.get("area_sq_km"),
                "boundary_geojson": d.get("boundary_geojson"),
                "data_source": d.get("source", "UNKNOWN"),
            })
            count += 1
        except Exception as e:
            logger.debug(f"District upsert error: {e}")
            continue

    await db.commit()
    logger.info(f"Districts upserted: {count}/{len(districts)}")
    return count


async def get_real_data_summary(db: AsyncSession) -> Dict[str, Any]:
    """Get a summary of what real data is loaded in the database."""
    try:
        result = await db.execute(text("""
            SELECT
                milestone_data_status,
                COUNT(*) as count,
                COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_coords,
                COUNT(CASE WHEN total_area_ha IS NOT NULL THEN 1 END) as with_area,
                COUNT(CASE WHEN notification_3a_date IS NOT NULL THEN 1 END) as with_3a_date
            FROM projects
            WHERE deleted_at IS NULL
            GROUP BY milestone_data_status
            ORDER BY count DESC
        """))
        rows = result.fetchall()

        district_count = 0
        try:
            dr = await db.execute(text("SELECT COUNT(*) FROM districts"))
            district_count = dr.scalar() or 0
        except Exception:
            pass

        return {
            "project_sources": [
                {
                    "source": row[0],
                    "count": row[1],
                    "with_coords": row[2],
                    "with_area": row[3],
                    "with_3a_date": row[4],
                }
                for row in rows
            ],
            "district_records": district_count,
            "summary_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Summary query error: {e}")
        return {}
