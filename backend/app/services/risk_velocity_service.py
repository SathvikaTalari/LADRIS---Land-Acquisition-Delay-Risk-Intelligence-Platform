"""
LADRIS — Risk Velocity Service
=====================================
Calculates Risk Velocity ("How quickly is this project's risk getting worse or better?")
for projects using timestamped observations from the `project_risk_snapshots` table.

CRITICAL RULES ENFORCED:
1. Signal Separation (Rule 3): Velocity is computed strictly independently per risk signal:
   - structural_anomaly
   - stage_risk
   - predictive_delay
   Different signals are NEVER mixed.

2. Policy Thresholds (Rule 6): 7-day Risk Change classification:
   - <= -10     : Improving (↓↓)
   - -10 to +5  : Stable (→)
   - +5 to +15  : Rising (↑)
   - > +15      : Rapidly Rising (↑↑)
   Labeled as "initial policy thresholds, not scientifically established thresholds".

3. Insufficient Observations (Rule 7): When < 2 observations exist for a signal,
   velocity_status is "NOT_AVAILABLE" with reason "Insufficient historical observations".
   Velocity is NEVER invented or imputed.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_models import ProjectRiskSnapshot
from app.models.project import Project

log = logging.getLogger(__name__)

POLICY_THRESHOLD_NOTE = (
    "Thresholds (<= -10: Improving, -10 to +5: Stable, +5 to +15: Rising, > +15: Rapidly Rising) "
    "are initial policy thresholds, not scientifically established thresholds."
)


def classify_7day_velocity(delta_7d: float) -> Dict[str, str]:
    """
    Classify 7-day risk change according to hackathon initial policy thresholds.

    Parameters
    ----------
    delta_7d : float (CurrentRisk - Risk7DaysAgo)

    Returns
    -------
    dict with: velocity_status, label, symbol, badge_color
    """
    if delta_7d <= -10.0:
        return {
            "velocity_status": "IMPROVING",
            "label": "Improving",
            "symbol": "↓↓",
            "badge_color": "emerald",
            "description": "Project risk has improved significantly over the past 7 days.",
        }
    elif delta_7d <= 5.0:
        return {
            "velocity_status": "STABLE",
            "label": "Stable",
            "symbol": "→",
            "badge_color": "blue",
            "description": "Project risk is relatively stable over the past 7 days.",
        }
    elif delta_7d <= 15.0:
        return {
            "velocity_status": "RISING",
            "label": "Rising",
            "symbol": "↑",
            "badge_color": "amber",
            "description": "Project risk condition is escalating over the past 7 days.",
        }
    else:
        return {
            "velocity_status": "RAPIDLY_RISING",
            "label": "Rapidly Rising",
            "symbol": "↑↑",
            "badge_color": "rose",
            "description": "Project condition is deteriorating very rapidly (Critical Early-Warning).",
        }


async def get_project_risk_velocity(
    project_id: UUID,
    risk_type: str = "structural_anomaly",
    db: AsyncSession = None,
) -> Dict[str, Any]:
    """
    Compute Risk Velocity for a project and specific risk signal.

    Returns
    -------
    dict containing velocity metrics, 7-day change, 30-day change, sparkline, and threshold label.
    """
    query = (
        select(ProjectRiskSnapshot)
        .where(
            ProjectRiskSnapshot.project_id == project_id,
            ProjectRiskSnapshot.risk_type == risk_type,
        )
        .order_by(ProjectRiskSnapshot.snapshot_date.asc())
    )

    result = await db.execute(query)
    snapshots = result.scalars().all()

    # Rule 7: Insufficient Historical Observations
    if len(snapshots) < 2:
        current_score = float(snapshots[0].risk_score) if len(snapshots) == 1 else None
        return {
            "project_id": str(project_id),
            "risk_type": risk_type,
            "current_score": current_score,
            "velocity_status": "NOT_AVAILABLE",
            "label": "Not Available",
            "symbol": "N/A",
            "badge_color": "slate",
            "reason": "Insufficient historical observations",
            "disclaimer": "At least 2 historical snapshots for this specific risk signal are required to compute velocity.",
            "policy_threshold_note": POLICY_THRESHOLD_NOTE,
            "observation_count": len(snapshots),
            "sparkline": [current_score] if current_score is not None else [],
            "change_7d": None,
            "change_30d": None,
            "daily_velocity_rate": None,
            "formatted_display": "Not Available",
        }

    # Extract historical points
    scores = [round(float(s.risk_score), 1) for s in snapshots]
    timestamps = [s.snapshot_date.isoformat() for s in snapshots]

    latest_snap = snapshots[-1]
    latest_score = float(latest_snap.risk_score)

    now = latest_snap.snapshot_date

    # Find 7-day previous snapshot (nearest snapshot around now - 7 days)
    target_7d = now - timedelta(days=7)
    target_30d = now - timedelta(days=30)

    snap_7d = min(snapshots[:-1], key=lambda s: abs((s.snapshot_date - target_7d).total_seconds()))
    snap_30d = min(snapshots, key=lambda s: abs((s.snapshot_date - target_30d).total_seconds()))

    score_7d = float(snap_7d.risk_score)
    score_30d = float(snap_30d.risk_score)

    # 7-day change and daily velocity formula
    change_7d = round(latest_score - score_7d, 1)
    days_7d = max(1, (now - snap_7d.snapshot_date).days)
    daily_rate_7d = round(change_7d / days_7d, 2) if days_7d > 0 else 0.0

    # 30-day change
    change_30d = round(latest_score - score_30d, 1)

    # Classification
    classification = classify_7day_velocity(change_7d)

    sign = "+" if change_7d >= 0 else ""
    formatted_display = f"{sign}{int(round(change_7d))} points / {days_7d} days"

    return {
        "project_id": str(project_id),
        "risk_type": risk_type,
        "current_score": round(latest_score, 1),
        "previous_score_7d": round(score_7d, 1),
        "previous_score_30d": round(score_30d, 1),
        "change_7d": change_7d,
        "change_30d": change_30d,
        "days_between_snapshots": days_7d,
        "daily_velocity_rate": daily_rate_7d,
        "velocity_status": classification["velocity_status"],
        "label": classification["label"],
        "symbol": classification["symbol"],
        "badge_color": classification["badge_color"],
        "description": classification["description"],
        "formatted_display": formatted_display,
        "sparkline": scores,
        "history": [
            {
                "snapshot_date": s.snapshot_date.isoformat(),
                "score": round(float(s.risk_score), 1),
                "risk_level": s.risk_level,
            }
            for s in snapshots
        ],
        "observation_count": len(snapshots),
        "policy_threshold_note": POLICY_THRESHOLD_NOTE,
    }


async def get_multi_signal_velocity(
    project_id: UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Compute velocity separately for all distinct risk signals (Rule 3).
    Does NOT mix signals.
    """
    structural = await get_project_risk_velocity(project_id, "structural_anomaly", db)
    stage = await get_project_risk_velocity(project_id, "stage_risk", db)
    delay = await get_project_risk_velocity(project_id, "predictive_delay", db)

    return {
        "project_id": str(project_id),
        "signals": {
            "structural_anomaly_velocity": structural,
            "stage_risk_velocity": stage,
            "predictive_delay_velocity": delay,
        },
        "primary_velocity": structural,  # Primary structural anomaly signal
    }


async def get_all_projects_velocity_summary(db: AsyncSession) -> Dict[str, Any]:
    """
    Summary of risk velocity across all active projects for Executive Dashboard.
    """
    res = await db.execute(select(Project).where(Project.deleted_at.is_(None)))
    projects = res.scalars().all()

    summary_list = []
    rapidly_rising_count = 0

    for proj in projects:
        vel = await get_project_risk_velocity(proj.id, "structural_anomaly", db)

        if vel.get("velocity_status") == "RAPIDLY_RISING":
            rapidly_rising_count += 1

        summary_list.append({
            "project_id": str(proj.id),
            "project_code": proj.project_code,
            "project_name": proj.name,
            "executing_agency": proj.executing_agency,
            "state_code": proj.state_code,
            "current_risk": vel.get("current_score"),
            "change_7d": vel.get("change_7d"),
            "velocity_status": vel.get("velocity_status"),
            "label": vel.get("label"),
            "symbol": vel.get("symbol"),
            "badge_color": vel.get("badge_color"),
            "sparkline": vel.get("sparkline", []),
        })

    return {
        "total_projects": len(projects),
        "rapidly_escalating_count": rapidly_rising_count,
        "projects_velocity": summary_list,
        "policy_threshold_note": POLICY_THRESHOLD_NOTE,
    }
