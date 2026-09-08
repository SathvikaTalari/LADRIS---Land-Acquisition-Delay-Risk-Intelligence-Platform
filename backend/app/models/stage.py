"""
LADRIS — SQLAlchemy ORM Models: Project Stage
"""
import enum
import uuid

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.project import RiskLevel


class StageName(str, enum.Enum):
    PRELIMINARY_NOTIFICATION = "PRELIMINARY_NOTIFICATION"
    SOCIAL_IMPACT_ASSESSMENT = "SOCIAL_IMPACT_ASSESSMENT"
    EXPERT_GROUP_REVIEW = "EXPERT_GROUP_REVIEW"
    SECTION_19_DECLARATION = "SECTION_19_DECLARATION"
    SECTION_21_OBJECTIONS = "SECTION_21_OBJECTIONS"
    AWARD_PREPARATION = "AWARD_PREPARATION"
    AWARD_ANNOUNCEMENT = "AWARD_ANNOUNCEMENT"
    COMPENSATION_DISBURSEMENT = "COMPENSATION_DISBURSEMENT"
    REHABILITATION_RESETTLEMENT = "REHABILITATION_RESETTLEMENT"
    POSSESSION = "POSSESSION"
    MUTATION = "MUTATION"
    PROJECT_HANDOVER = "PROJECT_HANDOVER"


class StageStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"
    BLOCKED = "BLOCKED"


class ProjectStage(Base):
    __tablename__ = "project_stages"
    __table_args__ = (
        UniqueConstraint("project_id", "stage_name", name="uq_stage_project_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_name = Column(
        Enum(StageName, name="stage_name"), nullable=False
    )
    stage_order = Column(SmallInteger, nullable=False)
    status = Column(
        Enum(StageStatus, name="stage_status"),
        nullable=False,
        default=StageStatus.PENDING,
    )

    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    stage_risk_level = Column(
        Enum(RiskLevel, name="risk_level"),
        default=RiskLevel.UNKNOWN,
    )
    delay_probability = Column(Numeric(5, 4), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project = relationship("Project", back_populates="stages")
