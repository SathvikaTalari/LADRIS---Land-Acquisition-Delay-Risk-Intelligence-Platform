"""
LandPulse AI — Phase 4 Database Migration
==========================================
Creates:
  - intervention_recommendations table
  - intervention_scenarios table

Run with: python database/migrations/phase4_intervention_tables.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

async def create_tables():
    from app.database import engine, Base
    from app.models.ml_models import InterventionRecommendation, InterventionScenario

    async with engine.begin() as conn:
        # Create only the new Phase 4 tables (don't drop existing)
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    InterventionRecommendation.__table__,
                    InterventionScenario.__table__,
                ],
            )
        )
    print("✅ Phase 4 tables created: intervention_recommendations, intervention_scenarios")


if __name__ == "__main__":
    asyncio.run(create_tables())
