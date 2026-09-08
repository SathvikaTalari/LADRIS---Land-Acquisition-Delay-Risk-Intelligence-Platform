"""
LADRIS — Pydantic Schemas: Project
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.project import AcquisitionAct, ProjectStatus, ProjectType, RiskLevel


class ProjectCreate(BaseModel):
    project_code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3)
    description: Optional[str] = None
    project_type: ProjectType
    acquisition_act: AcquisitionAct = AcquisitionAct.RFCTLARR_2013
    state_code: str = Field(..., max_length=3)
    district_codes: List[str] = Field(default_factory=list)
    tehsil_names: List[str] = Field(default_factory=list)
    nodal_agency: Optional[str] = None
    executing_agency: Optional[str] = None
    total_area_ha: Optional[float] = Field(None, gt=0)
    total_affected_families: Optional[int] = Field(None, ge=0)
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    estimated_compensation_inr: Optional[float] = Field(None, ge=0)
    notification_3a_date: Optional[date] = None
    notification_3d_date: Optional[date] = None
    delay_months: Optional[int] = Field(None, ge=0)
    delay_reason: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    project_type: Optional[ProjectType] = None
    acquisition_act: Optional[AcquisitionAct] = None
    nodal_agency: Optional[str] = None
    executing_agency: Optional[str] = None
    district_codes: Optional[List[str]] = None
    tehsil_names: Optional[List[str]] = None
    total_area_ha: Optional[float] = Field(None, gt=0)
    area_acquired_ha: Optional[float] = Field(None, ge=0)
    area_in_possession_ha: Optional[float] = Field(None, ge=0)
    total_affected_families: Optional[int] = Field(None, ge=0)
    families_compensated: Optional[int] = Field(None, ge=0)
    families_rehabilitated: Optional[int] = Field(None, ge=0)
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    estimated_compensation_inr: Optional[float] = Field(None, ge=0)
    disbursed_compensation_inr: Optional[float] = Field(None, ge=0)
    notification_3a_date: Optional[date] = None
    notification_3d_date: Optional[date] = None
    delay_months: Optional[int] = Field(None, ge=0)
    delay_reason: Optional[str] = None
    legal_case_count: Optional[int] = None
    legal_case_status: Optional[str] = None
    milestone_data_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lacrris_integration_status: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_code: str
    name: str
    description: Optional[str] = None
    project_type: ProjectType
    acquisition_act: AcquisitionAct
    status: ProjectStatus
    risk_level: RiskLevel
    state_code: str
    district_codes: List[str]
    tehsil_names: Optional[List[str]] = None
    nodal_agency: Optional[str] = None
    executing_agency: Optional[str] = None
    total_area_ha: Optional[float] = None
    area_acquired_ha: Optional[float] = None
    area_in_possession_ha: Optional[float] = None
    total_affected_families: Optional[int] = None
    families_compensated: Optional[int] = None
    families_rehabilitated: Optional[int] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    estimated_compensation_inr: Optional[float] = None
    disbursed_compensation_inr: Optional[float] = None
    notification_3a_date: Optional[date] = None
    notification_3d_date: Optional[date] = None
    delay_months: Optional[int] = None
    delay_reason: Optional[str] = None
    legal_case_count: Optional[int] = 0
    legal_case_status: Optional[str] = "NONE"
    milestone_data_status: Optional[str] = "SYNTHETIC_DEMO"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lacrris_integration_status: Optional[str] = "PLANNED"
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_code: str
    name: str
    project_type: ProjectType
    status: ProjectStatus
    risk_level: RiskLevel
    state_code: str
    district_codes: List[str] = Field(default_factory=list)
    nodal_agency: Optional[str] = None
    executing_agency: Optional[str] = None
    total_area_ha: Optional[float] = None
    total_affected_families: Optional[int] = None
    planned_end_date: Optional[date] = None
    delay_months: Optional[int] = None
    delay_reason: Optional[str] = None
    milestone_data_status: Optional[str] = "SYNTHETIC_DEMO"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime


