from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class RecommendationEnum(str, enum.Enum):
    strong_fit = "Strong Fit"
    maybe = "Maybe"
    reject = "Reject"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, default=[])
    experience_level = Column(String(50), nullable=False, default="Mid-level")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    screenings = relationship("Screening", back_populates="job", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255))
    resume_text = Column(Text, nullable=False)
    file_path = Column(String(500))
    original_filename = Column(String(255))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    screenings = relationship("Screening", back_populates="candidate", cascade="all, delete-orphan")


class Screening(Base):
    __tablename__ = "screenings"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    matched_skills = Column(JSON, default=[])
    missing_skills = Column(JSON, default=[])
    ai_summary = Column(Text)
    recommendation = Column(SAEnum(RecommendationEnum), nullable=False)
    screened_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate", back_populates="screenings")
    job = relationship("Job", back_populates="screenings")

    __table_args__ = (
        Index("ix_screenings_job_score", "job_id", "score"),
    )
