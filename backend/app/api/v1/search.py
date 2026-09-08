"""
LADRIS — Global Search API endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.schemas.misc import GlobalSearchResult

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/", response_model=List[GlobalSearchResult])
async def global_search(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not q or len(q) < 2:
        return []

    # Using basic ILIKE for search. Could be optimized with trigrams in a real prod env.
    search_term = f"%{q}%"
    
    query = select(Project).where(
        Project.deleted_at.is_(None)
    ).where(
        or_(
            Project.name.ilike(search_term),
            Project.project_code.ilike(search_term),
            Project.state_code.ilike(search_term),
            Project.executing_agency.ilike(search_term),
            Project.nodal_agency.ilike(search_term),
        )
    ).limit(20)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    search_results = []
    for p in projects:
        # Determine best match type for UI context
        match_type = "Project Name"
        agency_name = p.executing_agency or p.nodal_agency or "N/A"
        district_str = ", ".join(p.district_codes) if p.district_codes else "N/A"
        if q.lower() in (p.project_code or "").lower():
            match_type = "Identifier"
        elif q.lower() in (p.state_code or "").lower():
            match_type = "State"
        elif q.lower() in agency_name.lower():
            match_type = "Agency"
            
        search_results.append(
            GlobalSearchResult(
                project_id=p.id,
                project_name=p.name,
                project_identifier=p.project_code,
                state=p.state_code,
                district=district_str,
                agency=agency_name,
                match_type=match_type
            )
        )
        
    return search_results
