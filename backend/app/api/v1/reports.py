"""
LADRIS — Reports API endpoints
"""
import io
import csv
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/projects.csv")
async def export_projects_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Project).where(Project.deleted_at.is_(None))
    result = await db.execute(query)
    projects = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Project ID", "Name", "Identifier", "State", "District", 
        "Agency", "Total Area (Ha)", "Risk Level", "Completion Status"
    ])
    
    # Data
    for p in projects:
        district_str = ", ".join(p.district_codes) if p.district_codes else ""
        writer.writerow([
            str(p.id),
            p.name,
            p.project_code,
            p.state_code,
            district_str,
            p.executing_agency or p.nodal_agency or "",
            p.total_area_ha,
            p.risk_level.value if hasattr(p.risk_level, "value") else str(p.risk_level or ""),
            "Completed" if (p.status and (p.status.value if hasattr(p.status, "value") else str(p.status)) == "COMPLETED") else "Active"
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=ladris_projects_report.csv"}
    )
