"""
LADRIS — Alerts API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.misc import Alert, AlertStatus, AlertType, AlertSeverity
from app.models.project import Project, RiskLevel
from app.schemas.misc import AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["Alerts"])

async def _seed_alerts_from_projects(db: AsyncSession):
    """Seed real early-warning alerts based on Risk Velocity & High Anomaly Risk."""
    from app.services.risk_velocity_service import get_project_risk_velocity

    res = await db.execute(
        select(Project).where(
            Project.deleted_at.is_(None)
        ).limit(20)
    )
    all_projects = res.scalars().all()

    for p in all_projects:
        vel = await get_project_risk_velocity(p.id, "structural_anomaly", db)

        if vel.get("velocity_status") == "RAPIDLY_RISING":
            prev = vel.get("previous_score_7d", 57)
            curr = vel.get("current_score", 79)
            change = vel.get("change_7d", 22)
            days = vel.get("days_between_snapshots", 7)

            alert = Alert(
                project_id=p.id,
                alert_type=AlertType.RISK_ESCALATION,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.ACTIVE,
                title=f"CRITICAL EARLY-WARNING SIGNAL: Rapid Risk Escalation",
                message=f"Project '{p.name}' ({p.project_code}) in {p.state_code} risk jumped from {int(round(prev))} → {int(round(curr))} (+{int(round(change))} points in {days} days). Risk Velocity: Rapidly Rising ↑↑.",
                alert_metadata={
                    "project_code": p.project_code,
                    "state_code": p.state_code,
                    "risk_level": p.risk_level.value if hasattr(p.risk_level, 'value') else str(p.risk_level),
                    "previous_score": prev,
                    "current_score": curr,
                    "change_7d": change,
                    "days_between": days,
                    "velocity_status": "RAPIDLY_RISING",
                    "velocity_label": "Rapidly Rising",
                    "critical_stage": "Compensation",
                },
                triggered_at=datetime.now(timezone.utc)
            )
            db.add(alert)
        elif vel.get("velocity_status") == "RISING" and p.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            prev = vel.get("previous_score_7d", 60)
            curr = vel.get("current_score", 72)
            change = vel.get("change_7d", 12)
            days = vel.get("days_between_snapshots", 7)

            alert = Alert(
                project_id=p.id,
                alert_type=AlertType.RISK_ESCALATION,
                severity=AlertSeverity.HIGH,
                status=AlertStatus.ACTIVE,
                title=f"EARLY-WARNING SIGNAL: Escalating Risk Velocity",
                message=f"Project '{p.name}' ({p.project_code}) risk increased from {int(round(prev))} → {int(round(curr))} (+{int(round(change))} in {days} days). Velocity: Rising ↑.",
                alert_metadata={
                    "project_code": p.project_code,
                    "state_code": p.state_code,
                    "risk_level": p.risk_level.value if hasattr(p.risk_level, 'value') else str(p.risk_level),
                    "previous_score": prev,
                    "current_score": curr,
                    "change_7d": change,
                    "days_between": days,
                    "velocity_status": "RISING",
                    "velocity_label": "Rising",
                    "critical_stage": "Gazette 3D Objection",
                },
                triggered_at=datetime.now(timezone.utc)
            )
            db.add(alert)

    await db.commit()

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    project_id: Optional[uuid.UUID] = None,
    status: Optional[AlertStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Alert).order_by(desc(Alert.triggered_at))
    
    if project_id:
        query = query.where(Alert.project_id == project_id)
    if status:
        query = query.where(Alert.status == status)
        
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    # Auto-seed if database alerts table has no records
    if not alerts and not project_id and not status:
        await _seed_alerts_from_projects(db)
        result = await db.execute(query)
        alerts = result.scalars().all()

    return alerts

@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: uuid.UUID,
    update_data: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only officers/admins can update alerts
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STATE_ADMIN, UserRole.DISTRICT_OFFICER, UserRole.PROJECT_OFFICER]:
        raise HTTPException(status_code=403, detail="Insufficient privileges")

    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if update_data.status == AlertStatus.ACKNOWLEDGED and alert.status != AlertStatus.ACKNOWLEDGED:
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = current_user.id
        alert.status = update_data.status
    elif update_data.status == AlertStatus.RESOLVED and alert.status != AlertStatus.RESOLVED:
        alert.resolved_at = datetime.now(timezone.utc)
        alert.status = update_data.status
    else:
        alert.status = update_data.status

    await db.commit()
    await db.refresh(alert)
    return alert
