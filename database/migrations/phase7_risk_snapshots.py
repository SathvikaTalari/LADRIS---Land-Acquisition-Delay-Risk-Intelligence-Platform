"""
LandPulse AI — Database Migration: Phase 7 Risk Snapshots Table
================================================================
Creates the project_risk_snapshots table for temporal risk tracking.

IMPORTANT:
  - This table is populated by real API calls going forward
  - NO synthetic data will be inserted
  - Existing monitoring_log.jsonl is still the primary temporal source
  - This table enables persistent risk history beyond the log file

Run this migration:
  python database/migrations/phase7_risk_snapshots.py

Prerequisites:
  - PostgreSQL 16 database running (see docker-compose.yml)
  - DATABASE_URL set in environment (see .env)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

log = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
-- Phase 7: Project Risk Snapshots Table
-- Stores real timestamped risk assessments for temporal analysis
CREATE TABLE IF NOT EXISTS project_risk_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    snapshot_date   TIMESTAMPTZ NOT NULL DEFAULT now(),
    anomaly_score   NUMERIC(8, 6) NOT NULL,
    stage_fingerprint_risk NUMERIC(8, 6),
    risk_level      VARCHAR(20),
    data_completeness_pct NUMERIC(5, 2),
    model_version   VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Ensure we don't store duplicate snapshots for the same project
    -- within the same minute (prevents log replay duplicates)
    CONSTRAINT uq_project_snapshot_minute UNIQUE (project_id, date_trunc('minute', snapshot_date))
);

-- Index for fast temporal queries per project
CREATE INDEX IF NOT EXISTS idx_risk_snapshots_project_date
    ON project_risk_snapshots(project_id, snapshot_date DESC);

-- Index for risk-level based queries
CREATE INDEX IF NOT EXISTS idx_risk_snapshots_risk_level
    ON project_risk_snapshots(risk_level, snapshot_date DESC);

-- Comment documenting data authenticity
COMMENT ON TABLE project_risk_snapshots IS
    'Real timestamped risk assessment snapshots. '
    'Populated by LandPulse AI API calls only. '
    'No synthetic records. No backfilled fabricated data. '
    'Phase 7 — Government Decision Intelligence Platform.';
"""

# Index for projects table bottleneck queries
CREATE_PROJECT_INDEXES_SQL = """
-- Additional indexes for Phase 7 bottleneck group-by queries
CREATE INDEX IF NOT EXISTS idx_projects_state_risk
    ON projects(state_code, risk_level)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_projects_agency_state
    ON projects(executing_agency, state_code)
    WHERE deleted_at IS NULL;
"""


async def run_migration():
    """Execute the Phase 7 database migration."""
    from dotenv import load_dotenv
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        log.error("DATABASE_URL not set in environment. Check .env file.")
        sys.exit(1)

    # Convert to asyncpg URL format
    if database_url.startswith("postgresql://"):
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql+asyncpg://"):
        async_url = database_url
    else:
        log.error("Unsupported DATABASE_URL format: %s", database_url[:30])
        sys.exit(1)

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(async_url, echo=False)

    try:
        async with engine.begin() as conn:
            log.info("Running Phase 7 migration: creating project_risk_snapshots table...")
            await conn.execute(text(CREATE_TABLE_SQL))
            log.info("Creating additional indexes for bottleneck queries...")
            await conn.execute(text(CREATE_PROJECT_INDEXES_SQL))
            log.info("Migration completed successfully.")

        # Verify
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'project_risk_snapshots'"
            ))
            count = result.scalar()
            if count == 1:
                log.info("✅ project_risk_snapshots table verified.")
            else:
                log.error("❌ Table verification failed.")

    except Exception as e:
        log.error("Migration failed: %s", e)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_migration())
