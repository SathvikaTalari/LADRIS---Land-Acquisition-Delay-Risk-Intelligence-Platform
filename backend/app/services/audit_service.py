"""
LADRIS — Audit Service: Record audit log entries
"""
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.misc import AuditLog
from app.models.user import UserRole


async def record_audit_log(
    db: AsyncSession,
    action: str,
    user_id: Optional[UUID] = None,
    user_email: Optional[str] = None,
    user_role: Optional[UserRole] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    request_body: Optional[Dict[str, Any]] = None,
    response_status: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """
    Insert an audit log entry asynchronously.
    This function does NOT commit — the caller's session commit handles it.
    """
    log_entry = AuditLog(
        user_id=user_id,
        user_email=user_email,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_method=request_method,
        request_path=request_path,
        request_body=request_body,
        response_status=response_status,
        duration_ms=duration_ms,
    )
    db.add(log_entry)
