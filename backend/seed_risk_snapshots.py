"""
LADRIS — Temporal Risk Snapshots Database Seeder
======================================================
Seeds historical risk observations into the `project_risk_snapshots` table
for testing Risk Velocity metrics across 4 classification categories:
1. Rapidly Rising (+22 in 7 days)
2. Rising (+10 in 7 days)
3. Stable (+2 in 7 days)
4. Improving (-14 in 7 days)
5. Insufficient Data (0 or 1 snapshot)

Stores snapshots separately per risk signal type (Rule 3):
- structural_anomaly
- stage_risk
- predictive_delay (when applicable)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("seed_risk_snapshots")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS project_risk_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    snapshot_date           TIMESTAMPTZ NOT NULL DEFAULT now(),
    risk_type               VARCHAR(50) NOT NULL DEFAULT 'structural_anomaly',
    risk_score              NUMERIC(8, 4) NOT NULL DEFAULT 0.0,
    anomaly_score           NUMERIC(8, 6),
    stage_fingerprint_risk  NUMERIC(8, 6),
    risk_level              VARCHAR(20),
    data_completeness_pct   NUMERIC(5, 2),
    model_version           VARCHAR(50),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

ALTER_TABLE_SQL_1 = "ALTER TABLE project_risk_snapshots ADD COLUMN IF NOT EXISTS risk_type VARCHAR(50) NOT NULL DEFAULT 'structural_anomaly';"
ALTER_TABLE_SQL_2 = "ALTER TABLE project_risk_snapshots ADD COLUMN IF NOT EXISTS risk_score NUMERIC(8, 4) NOT NULL DEFAULT 0.0;"
CREATE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_risk_snapshots_project_type_date ON project_risk_snapshots(project_id, risk_type, snapshot_date DESC);"


async def seed_snapshots():
    from dotenv import load_dotenv
    load_dotenv()

    from sqlalchemy import select, text
    from app.database import AsyncSessionLocal, engine
    from app.models.project import Project, RiskLevel
    from app.models.ml_models import ProjectRiskSnapshot

    async with engine.begin() as conn:
        log.info("Ensuring project_risk_snapshots table and columns exist...")
        await conn.execute(text(CREATE_TABLE_SQL))
        await conn.execute(text(ALTER_TABLE_SQL_1))
        await conn.execute(text(ALTER_TABLE_SQL_2))
        await conn.execute(text(CREATE_INDEX_SQL))

    async with AsyncSessionLocal() as session:
        # Fetch existing projects
        res = await session.execute(select(Project).where(Project.deleted_at.is_(None)))
        projects = res.scalars().all()

        if not projects:
            log.warning("No projects found in database to seed snapshots for.")
            return

        log.info("Found %d projects in database.", len(projects))

        # Clear existing snapshots to allow idempotent seeding
        await session.execute(text("DELETE FROM project_risk_snapshots"))
        await session.commit()

        now = datetime.now(timezone.utc)

        seeded_count = 0

        # Pattern profiles for seeding realistic velocity
        profiles = [
            # 0: Rapidly Rising (+22 in 7 days)
            {
                "anomaly_series": [48, 52, 57, 57, 79],
                "stage_series": [45, 50, 52, 58, 80],
                "label": "Rapidly Rising",
            },
            # 1: Rising (+10 in 7 days)
            {
                "anomaly_series": [50, 55, 60, 62, 72],
                "stage_series": [48, 52, 58, 60, 70],
                "label": "Rising",
            },
            # 2: Stable (+2 in 7 days)
            {
                "anomaly_series": [80, 81, 82, 82, 84],
                "stage_series": [75, 76, 78, 78, 80],
                "label": "Stable",
            },
            # 3: Improving (-14 in 7 days)
            {
                "anomaly_series": [85, 80, 75, 72, 58],
                "stage_series": [82, 78, 72, 70, 56],
                "label": "Improving",
            },
            # 4: Insufficient Data (0 snapshots - leave empty)
            {
                "anomaly_series": [],
                "stage_series": [],
                "label": "Not Available",
            },
            # 5: Single Observation (1 snapshot)
            {
                "anomaly_series": [65],
                "stage_series": [60],
                "label": "Not Available",
            },
        ]

        intervals = [28, 21, 14, 7, 0]  # Days ago

        for idx, proj in enumerate(projects):
            # Select profile based on index modulo
            profile = profiles[idx % len(profiles)]

            anom_series = profile["anomaly_series"]
            stage_series = profile["stage_series"]

            # 1. Structural Anomaly Snapshots
            if anom_series:
                for point_idx, score in enumerate(anom_series):
                    days_ago = intervals[len(intervals) - len(anom_series) + point_idx]
                    snap_date = now - timedelta(days=days_ago)

                    r_level = "HIGH" if score >= 70 else ("MEDIUM" if score >= 45 else "LOW")
                    if score >= 80:
                        r_level = "CRITICAL"

                    snap = ProjectRiskSnapshot(
                        project_id=proj.id,
                        snapshot_date=snap_date,
                        risk_type="structural_anomaly",
                        risk_score=float(score),
                        anomaly_score=round(score / 100.0, 4),
                        risk_level=r_level,
                        data_completeness_pct=95.0,
                        model_version="v1.0-anomaly",
                    )
                    session.add(snap)
                    seeded_count += 1

            # 2. Stage Risk Snapshots (Signal separation)
            if stage_series:
                for point_idx, score in enumerate(stage_series):
                    days_ago = intervals[len(intervals) - len(stage_series) + point_idx]
                    snap_date = now - timedelta(days=days_ago)

                    snap = ProjectRiskSnapshot(
                        project_id=proj.id,
                        snapshot_date=snap_date,
                        risk_type="stage_risk",
                        risk_score=float(score),
                        stage_fingerprint_risk=round(score / 100.0, 4),
                        risk_level="HIGH" if score >= 70 else "MEDIUM",
                        data_completeness_pct=95.0,
                        model_version="v1.0-stage",
                    )
                    session.add(snap)
                    seeded_count += 1

        await session.commit()
        log.info("✅ Successfully seeded %d risk snapshots across %d projects.", seeded_count, len(projects))


if __name__ == "__main__":
    asyncio.run(seed_snapshots())
