from sqlalchemy import String, Text, ForeignKey, DateTime, Float, JSON, Enum, Integer, Table, Column, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from datetime import datetime, timezone
from typing import List, Optional, Any
from ..db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import enum
import uuid
from sqlalchemy.types import TypeDecorator

# ─── Custom Types for SQLite Compatibility ────────────────────────────────────
class SafeJSONB(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

# ─── Enums ────────────────────────────────────────────────────────────────────

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    RECRUITER = "RECRUITER"
    VIEWER = "VIEWER"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class BatchStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# ─── Mixins ────────────────────────────────────────────────────────────────────

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

# ─── Association Tables ───────────────────────────────────────────────────────

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# ─── Models ───────────────────────────────────────────────────────────────────

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    plan_tier: Mapped[str] = mapped_column(String(20), default="free")
    
    users: Mapped[List["User"]] = relationship(back_populates="org")
    jobs: Mapped[List["JobPosting"]] = relationship(back_populates="org")
    candidates: Mapped[List["Candidate"]] = relationship(back_populates="org")

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), unique=True)
    permissions: Mapped[dict] = mapped_column(SafeJSONB, default=dict)

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    email_verified: Mapped[bool] = mapped_column(default=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    org: Mapped["Organization"] = relationship(back_populates="users")
    roles: Mapped[List["Role"]] = relationship(secondary=user_roles)
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(back_populates="user")
    mfa_devices: Mapped[List["MFADevice"]] = relationship(back_populates="user")
    sessions: Mapped[List["UserSession"]] = relationship(back_populates="user")
    departments: Mapped[List["Department"]] = relationship(secondary="department_members", back_populates="users")

class JobPosting(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "job_postings"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[dict] = mapped_column(SafeJSONB)
    min_experience: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    __table_args__ = (
        Index("ix_job_postings_skills_gin", "required_skills", postgresql_using="gin"),
    )
    
    org: Mapped["Organization"] = relationship(back_populates="jobs")
    results: Mapped[List["ScreeningResult"]] = relationship(back_populates="job")
    applications: Mapped[List["Application"]] = relationship(back_populates="job")

class Candidate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[dict] = mapped_column(SafeJSONB)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    
    __table_args__ = (
        Index("ix_candidates_skills_gin", "parsed_json", postgresql_using="gin"),
    )
    
    org: Mapped["Organization"] = relationship(back_populates="candidates")
    embeddings: Mapped[List["ResumeEmbedding"]] = relationship(back_populates="candidate")
    applications: Mapped[List["Application"]] = relationship(back_populates="candidate")

class Application(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="APPLIED")
    score: Mapped[Optional[float]] = mapped_column(nullable=True, index=True)
    
    __table_args__ = (
        Index("ix_applications_job_cand", "job_id", "candidate_id", unique=True),
        Index("ix_applications_score_desc", score.desc()),
    )
    
    org: Mapped["Organization"] = relationship()
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    job: Mapped["JobPosting"] = relationship(back_populates="applications")
    screening_results: Mapped[List["ScreeningResult"]] = relationship(back_populates="application")
    pipeline_stages: Mapped[List["PipelineStage"]] = relationship(back_populates="application", cascade="all, delete-orphan")

class ScreeningResult(Base, TimestampMixin):
    __tablename__ = "screening_results"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), index=True)
    llm_model: Mapped[str] = mapped_column(String(50), default="gemini-1.5-flash")
    prompt_version: Mapped[str] = mapped_column(String(20), default="1.0")
    
    # Granular Scoring (Total 100)
    score: Mapped[float] = mapped_column(index=True) # Total score
    keyword_score: Mapped[float] = mapped_column(default=0.0)
    skills_score: Mapped[float] = mapped_column(default=0.0)
    experience_score: Mapped[float] = mapped_column(default=0.0)
    education_score: Mapped[float] = mapped_column(default=0.0)
    format_score: Mapped[float] = mapped_column(default=0.0)
    certs_score: Mapped[float] = mapped_column(default=0.0)
    
    reasoning: Mapped[str] = mapped_column(Text)
    bias_flags: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    
    application: Mapped["Application"] = relationship(back_populates="screening_results")
    job: Mapped["JobPosting"] = relationship(back_populates="results")

class ResumeEmbedding(Base, TimestampMixin):
    __tablename__ = "resume_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    embedding: Mapped[Any] = mapped_column(Vector(768)) # Gemini text-embedding-004
    model_version: Mapped[str] = mapped_column(String(50))
    
    candidate: Mapped["Candidate"] = relationship(back_populates="embeddings")

class JobCandidateMatch(Base, TimestampMixin):
    __tablename__ = "job_candidate_matches"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    similarity_score: Mapped[float] = mapped_column(Float)
    
    job: Mapped["JobPosting"] = relationship()
    candidate: Mapped["Candidate"] = relationship()

    __table_args__ = (
        Index("ix_job_match_score", similarity_score.desc()),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[int] = mapped_column()
    
    # Audit trail details
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    input_hash: Mapped[Optional[str]] = mapped_column(String(64))
    output_json: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    bias_flags: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    
    diff: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(default=False)
    
    user: Mapped["User"] = relationship(back_populates="notifications")

class InterviewKit(Base, TimestampMixin):
    __tablename__ = "interview_kits"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    focus_areas: Mapped[dict] = mapped_column(JSON) # List[str]
    difficulty: Mapped[str] = mapped_column(String(20)) # JUNIOR|MID|SENIOR
    questions: Mapped[dict] = mapped_column(JSON) # List[QuestionDict]
    
    scorecards: Mapped[List["InterviewScorecard"]] = relationship(back_populates="kit")

class InterviewScorecard(Base, TimestampMixin):
    __tablename__ = "interview_scorecards"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kit_id: Mapped[int] = mapped_column(ForeignKey("interview_kits.id"), index=True)
    recruiter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    scores: Mapped[dict] = mapped_column(JSON) # {question_index: score}
    total_score: Mapped[float] = mapped_column()
    ai_recommendation: Mapped[str] = mapped_column(Text) # final hire/no-hire logic
    
    kit: Mapped["InterviewKit"] = relationship(back_populates="scorecards")
    recruiter: Mapped["User"] = relationship()
    
class BatchJob(Base, TimestampMixin):
    __tablename__ = "batch_jobs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), index=True)
    status: Mapped[BatchStatus] = mapped_column(Enum(BatchStatus), default=BatchStatus.PENDING)
    total_files: Mapped[int] = mapped_column(default=0)
    completed_files: Mapped[int] = mapped_column(default=0)
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    org: Mapped["Organization"] = relationship()
    job: Mapped["JobPosting"] = relationship()

class TaskRecord(Base, TimestampMixin):
    __tablename__ = "task_records"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(50)) # "screening", "bulk_upload", etc.
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    progress: Mapped[int] = mapped_column(default=0) # 0-100
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    org: Mapped["Organization"] = relationship()
