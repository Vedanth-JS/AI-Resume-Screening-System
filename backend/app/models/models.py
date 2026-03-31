from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db.database import Base
import enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class TaskStatus(str, enum.Enum):
    pending   = "pending"
    running   = "running"
    completed = "completed"
    failed    = "failed"

class BatchStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    completed  = "completed"
    failed     = "failed"


# ─── Existing tables (unchanged) ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role          = Column(String, default="recruiter")   # admin | recruiter | candidate
    created_at    = Column(DateTime, default=datetime.utcnow)
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    batch_jobs    = relationship("BatchJob", back_populates="creator", cascade="all, delete-orphan")


class JobPosting(Base):
    __tablename__ = "jobs"
    id                = Column(Integer, primary_key=True, index=True)
    title             = Column(String, index=True)
    description       = Column(Text)
    required_skills   = Column(JSON)          # List[str]
    min_experience    = Column(Integer, default=0)
    required_education= Column(String, default="Not Specified")
    created_by        = Column(Integer, ForeignKey("users.id"))
    created_at        = Column(DateTime, default=datetime.utcnow)


class Candidate(Base):
    __tablename__ = "candidates"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, index=True)
    email       = Column(String, index=True)
    phone       = Column(String, nullable=True)
    raw_text    = Column(Text)
    parsed_json = Column(JSON)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class ScreeningResult(Base):
    __tablename__ = "scores"
    id                  = Column(Integer, primary_key=True, index=True)
    candidate_id        = Column(Integer, ForeignKey("candidates.id"))
    job_id              = Column(Integer, ForeignKey("jobs.id"))
    ats_score           = Column(Float)
    llm_score           = Column(Float, nullable=True)
    final_score         = Column(Float)
    # ─── New breakdown columns ───────────────────────────────────────────────
    keyword_score       = Column(Float, nullable=True)
    semantic_score      = Column(Float, nullable=True)
    format_score        = Column(Float, nullable=True)
    section_score       = Column(Float, nullable=True)
    interview_questions = Column(JSON, nullable=True)    # List[{question, rationale}]
    jd_profile          = Column(JSON, nullable=True)    # Structured JD analysis
    processing_time_ms  = Column(Integer, nullable=True)
    # ─────────────────────────────────────────────────────────────────────────
    explanation         = Column(Text, nullable=True)
    status              = Column(String, default="pending")   # accept | review | reject
    created_at          = Column(DateTime, default=datetime.utcnow)


class BiasReport(Base):
    __tablename__ = "bias_reports"
    id           = Column(Integer, primary_key=True, index=True)
    job_id       = Column(Integer, ForeignKey("jobs.id"))
    report_json  = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"))
    query     = Column(Text)
    response  = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    message    = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="notifications")


# ─── New tables ───────────────────────────────────────────────────────────────

class TaskRecord(Base):
    """Tracks every Celery task so the frontend can poll status."""
    __tablename__    = "tasks"
    id               = Column(Integer, primary_key=True, index=True)
    celery_task_id   = Column(String, unique=True, index=True)
    task_type        = Column(String)          # resume_screen | batch_process
    status           = Column(String, default=TaskStatus.pending)
    result_json      = Column(JSON, nullable=True)
    error            = Column(Text, nullable=True)
    progress         = Column(Integer, default=0)    # 0-100 percent
    created_at       = Column(DateTime, default=datetime.utcnow)
    completed_at     = Column(DateTime, nullable=True)


class AnalyticsEvent(Base):
    """Append-only event log for all significant system actions."""
    __tablename__  = "analytics_events"
    id             = Column(Integer, primary_key=True, index=True)
    event_type     = Column(String, index=True)     # resume_uploaded | score_computed | etc.
    payload_json   = Column(JSON, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)


class BatchJob(Base):
    """Tracks a bulk ZIP upload batch."""
    __tablename__  = "batch_jobs"
    id             = Column(Integer, primary_key=True, index=True)
    created_by     = Column(Integer, ForeignKey("users.id"))
    job_id         = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    jd_text        = Column(Text, nullable=True)
    status         = Column(String, default=BatchStatus.pending)
    total_files    = Column(Integer, default=0)
    completed_files= Column(Integer, default=0)
    result_json    = Column(JSON, nullable=True)      # List of ranked candidate results
    created_at     = Column(DateTime, default=datetime.utcnow)
    completed_at   = Column(DateTime, nullable=True)
    creator        = relationship("User", back_populates="batch_jobs")
