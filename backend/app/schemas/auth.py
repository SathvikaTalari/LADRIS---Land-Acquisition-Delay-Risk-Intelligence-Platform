"""
LADRIS — Pydantic Schemas: Auth
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.VIEWER
    state_code: Optional[str] = Field(None, max_length=3)
    district_code: Optional[str] = Field(None, max_length=10)
    agency_name: Optional[str] = Field(None, max_length=255)
    assigned_project_ids: Optional[str] = Field(None, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    state_code: Optional[str]
    district_code: Optional[str]
    agency_name: Optional[str] = None
    assigned_project_ids: Optional[str] = None
    last_login_at: Optional[datetime]
    created_at: datetime



class TokenPayload(BaseModel):
    sub: str          # user email
    user_id: str      # user UUID
    role: str
    exp: int          # expiry epoch
    iat: int          # issued-at epoch
    type: str = "access"  # "access" or "refresh"
