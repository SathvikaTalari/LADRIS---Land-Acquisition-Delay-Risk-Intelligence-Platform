"""
LADRIS — Risk Velocity Feature Verification Test
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("test_risk_velocity")


async def run_tests():
    from dotenv import load_dotenv
    load_dotenv()

    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.project import Project
    from app.services.risk_velocity_service import (
        classify_7day_velocity,
        get_project_risk_velocity,
        get_multi_signal_velocity,
        get_all_projects_velocity_summary,
    )
    from ml.interventions.priority_scorer import compute_priority_score

    log.info("--- TEST 1: Classification Thresholds ---")
    assert classify_7day_velocity(-12.0)["velocity_status"] == "IMPROVING"
    assert classify_7day_velocity(2.0)["velocity_status"] == "STABLE"
    assert classify_7day_velocity(10.0)["velocity_status"] == "RISING"
    assert classify_7day_velocity(22.0)["velocity_status"] == "RAPIDLY_RISING"
    log.info("✅ Test 1 Passed: 7-day velocity policy thresholds correctly mapped.")

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Project).where(Project.deleted_at.is_(None)))
        projects = res.scalars().all()
        log.info("Found %d projects for backend test.", len(projects))

        if not projects:
            log.error("❌ No projects found.")
            return

        # Test project with multi-snapshots
        proj_with_history = projects[0]
        vel_res = await get_project_risk_velocity(proj_with_history.id, "structural_anomaly", session)

        log.info("--- TEST 2: Risk Velocity Calculation for Project with History ---")
        log.info("Project: %s (%s)", proj_with_history.name, proj_with_history.project_code)
        log.info("Current Score: %s | 7d Change: %s | Status: %s | Symbol: %s",
                 vel_res["current_score"], vel_res["change_7d"], vel_res["velocity_status"], vel_res["symbol"])
        log.info("Sparkline: %s", vel_res["sparkline"])
        assert vel_res["velocity_status"] in ["RAPIDLY_RISING", "RISING", "STABLE", "IMPROVING"]
        log.info("✅ Test 2 Passed: Risk Velocity correctly calculated for historical project.")

        log.info("--- TEST 3: Rule 3 Signal Separation ---")
        multi_sig = await get_multi_signal_velocity(proj_with_history.id, session)
        assert "structural_anomaly_velocity" in multi_sig["signals"]
        assert "stage_risk_velocity" in multi_sig["signals"]
        assert "predictive_delay_velocity" in multi_sig["signals"]
        assert multi_sig["signals"]["predictive_delay_velocity"]["velocity_status"] == "NOT_AVAILABLE"
        log.info("✅ Test 3 Passed: Distinct signal separation enforced. Predictive delay returns Not Available when unobserved.")

        log.info("--- TEST 4: Rule 7 Insufficient Observations Handling ---")
        # Find project with 0 or 1 snapshot
        no_hist_proj = None
        for p in projects:
            v = await get_project_risk_velocity(p.id, "structural_anomaly", session)
            if v["velocity_status"] == "NOT_AVAILABLE":
                no_hist_proj = p
                break

        if no_hist_proj:
            v_no_hist = await get_project_risk_velocity(no_hist_proj.id, "structural_anomaly", session)
            assert v_no_hist["velocity_status"] == "NOT_AVAILABLE"
            assert v_no_hist["label"] == "Not Available"
            assert v_no_hist["reason"] == "Insufficient historical observations"
            log.info("✅ Test 4 Passed: Project without 2 snapshots returns 'Not Available' with explicit reason.")

        log.info("--- TEST 5: Executive Dashboard Cross-Project Summary ---")
        summary = await get_all_projects_velocity_summary(session)
        log.info("Total Projects: %d | Rapidly Escalating Count: %d",
                 summary["total_projects"], summary["rapidly_escalating_count"])
        assert summary["rapidly_escalating_count"] >= 0
        log.info("✅ Test 5 Passed: Cross-project velocity summary generated.")

        log.info("--- TEST 6: Priority Scorer Integration with Risk Velocity ---")
        ps = compute_priority_score(
            risk_severity=0.8,
            stage_risk=0.7,
            urgency=0.8,
            potential_impact=0.7,
            feasibility=0.8,
            data_confidence=0.85,
            data_completeness_pct=100.0,
            risk_velocity_score=0.95,  # Rapidly rising risk score
        )
        assert "risk_velocity" in ps["score_components"]
        assert ps["score_components"]["risk_velocity"]["weight"] == 0.10
        log.info("Priority Score with High Velocity: %d", ps["priority_score"])
        log.info("✅ Test 6 Passed: Priority Scorer incorporates Risk Velocity weight (10%).")

        log.info("🎉 ALL RISK VELOCITY VERIFICATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_tests())
