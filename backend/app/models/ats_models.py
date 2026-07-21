"""
Extended ATS Models — Departments, Pipeline Stages, Notes, Activities, Offers, Templates.
Integrates with existing models (Organization, User, JobPosting, Candidate, Application).
"""
from sqlalchemy import (
    String, Text, ForeignKey, DateTime, Float, JSON, Integer, Boolean, Table, Column, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from typing import List, Optional, Any
from ..db.database import Base
from .models import TimestampMixin, SafeJSONB
import enum
import uuid


# ─── Enums ────────────────────────────────────────────────────────────────────

class PipelineStageEnum(str, enum.Enum):
    APPLIED = "APPLIED"
    SCREENED = "SCREENED"
    PHONE_SCREEN = "PHONE_SCREEN"
    TECHNICAL_INTERVIEW = "TECHNICAL_INTERVIEW"
    ONSITE_INTERVIEW = "ONSITE_INTERVIEW"
    ASSESSMENT = "ASSESSMENT"
    REFERENCE_CHECK = "REFERENCE_CHECK"
    OFFER_EXTENDED = "OFFER_EXTENDED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    HIRED = "HIRED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    ON_HOLD = "ON_HOLD"

class InterviewType(str, enum.Enum):
    PHONE = "PHONE"
    VIDEO = "VIDEO"
    ONSITE = "ONSITE"
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    PANEL = "PANEL"
    CASE_STUDY = "CASE_STUDY"

class OfferStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    COUNTERED = "COUNTERED"

class CommunicationType(str, enum.Enum):
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"
    SMS = "SMS"
    PUSH = "PUSH"


# ─── Models ────────────────────────────────────────────────────────────────────


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    head_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    org: Mapped["Organization"] = relationship()
    head: Mapped[Optional["User"]] = relationship(foreign_keys=[head_user_id])
    users: Mapped[List["User"]] = relationship(secondary="department_members", back_populates="departments")


# Association table for department members
department_members = Table(
    "department_members",
    Base.metadata,
    Column("department_id", ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class PipelineStage(Base, TimestampMixin):
    """Represents a candidate's progression through hiring stages."""
    __tablename__ = "pipeline_stages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    stage: Mapped[PipelineStageEnum] = mapped_column(SAEnum(PipelineStageEnum), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")  # active | completed | skipped
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("ix_pipeline_application_stage", "application_id", "stage", unique=True),
    )

    application: Mapped["Application"] = relationship(back_populates="pipeline_stages")
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to])


class CandidateNote(Base, TimestampMixin):
    """Notes/comments on candidates."""
    __tablename__ = "candidate_notes"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    is_private: Mapped[bool] = mapped_column(default=False)
    tags: Mapped[dict] = mapped_column(SafeJSONB, default=dict)

    author: Mapped["User"] = relationship()


class ActivityLog(Base, TimestampMixin):
    """Audit trail of all actions on candidates, jobs, applications."""
    __tablename__ = "activity_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))  # candidate, application, interview, offer
    entity_id: Mapped[int] = mapped_column()
    details: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    meta_info: Mapped[dict] = mapped_column("metadata", SafeJSONB, default=dict)

    __table_args__ = (
        Index("ix_activity_entity", "entity_type", "entity_id"),
        Index("ix_activity_org_time", "org_id", "created_at"),
    )


class Interview(Base, TimestampMixin):
    """Scheduled interviews — extends InterviewKit for actual scheduling."""
    __tablename__ = "interviews"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    interview_type: Mapped[InterviewType] = mapped_column(SAEnum(InterviewType))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(default=60)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL or physical address
    interviewers: Mapped[dict] = mapped_column(SafeJSONB, default=list)  # [{user_id, name}]
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled | completed | cancelled | no_show
    feedback: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    kit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("interview_kits.id"), nullable=True)
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_interviews_app_time", "application_id", "scheduled_at"),
    )

    application: Mapped["Application"] = relationship()
    kit: Mapped[Optional["InterviewKit"]] = relationship()


class OfferLetter(Base, TimestampMixin):
    """Offer letters sent to candidates."""
    __tablename__ = "offer_letters"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    status: Mapped[OfferStatus] = mapped_column(SAEnum(OfferStatus), default=OfferStatus.DRAFT)
    title: Mapped[str] = mapped_column(String(200))
    salary: Mapped[Optional[float]] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    content_html: Mapped[str] = mapped_column(Text)
    signed_by_candidate: Mapped[bool] = mapped_column(default=False)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    token: Mapped[str] = mapped_column(String(64), default=lambda: uuid.uuid4().hex, unique=True)

    application: Mapped["Application"] = relationship()


class EmailTemplate(Base, TimestampMixin):
    """Reusable email templates for different communication stages."""
    __tablename__ = "email_templates"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    body_html: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(50))  # screening_result | interview_invite | offer | rejection | general
    variables: Mapped[dict] = mapped_column(SafeJSONB, default=dict)  # {var_name: description}
    is_active: Mapped[bool] = mapped_column(default=True)

    org: Mapped["Organization"] = relationship()


class TalentPool(Base, TimestampMixin):
    """Pools of candidates grouped for future roles."""
    __tablename__ = "talent_pools"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criteria: Mapped[dict] = mapped_column(SafeJSONB, default=dict)  # filter criteria
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    candidates: Mapped[List["Candidate"]] = relationship(secondary="talent_pool_candidates")
    owner: Mapped["User"] = relationship()


talent_pool_candidates = Table(
    "talent_pool_candidates",
    Base.metadata,
    Column("talent_pool_id", ForeignKey("talent_pools.id", ondelete="CASCADE"), primary_key=True),
    Column("candidate_id", ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True),
    Column("added_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("added_by", ForeignKey("users.id")),
)


class RejectionReason(Base, TimestampMixin):
    """Canned rejection reasons for compliance reporting."""
    __tablename__ = "rejection_reasons"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))  # skills | experience | culture | compensation | other
    is_active: Mapped[bool] = mapped_column(default=True)


class BulkOperation(Base, TimestampMixin):
    """Track bulk operations on candidates/applications."""
    __tablename__ = "bulk_operations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    initiated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    operation_type: Mapped[str] = mapped_column(String(50))  # stage_change | reject | email | tag | archive
    target_count: Mapped[int] = mapped_column(default=0)
    completed_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | running | completed | failed
    result_summary: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
