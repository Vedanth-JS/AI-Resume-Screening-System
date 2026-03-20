from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
import datetime
from typing import List, Optional

class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[List[str]] = mapped_column(JSON) # List of skills
    min_experience: Mapped[int] = mapped_column()
    required_education: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    results: Mapped[List["ScreeningResult"]] = relationship("ScreeningResult", back_populates="job")

class Candidate(Base):
    __tablename__ = "candidates"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    resume_path: Mapped[str] = mapped_column(String)
    raw_text: Mapped[str] = mapped_column(Text)
    extracted_skills: Mapped[List[str]] = mapped_column(JSON)
    experience_years: Mapped[int] = mapped_column()
    education: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    results: Mapped[List["ScreeningResult"]] = relationship("ScreeningResult", back_populates="candidate")

class ScreeningResult(Base):
    __tablename__ = "screening_results"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    
    total_score: Mapped[float] = mapped_column(Float)
    skills_score: Mapped[float] = mapped_column(Float)
    experience_score: Mapped[float] = mapped_column(Float)
    education_score: Mapped[float] = mapped_column(Float)
    semantic_score: Mapped[float] = mapped_column(Float)
    
    matched_skills: Mapped[List[str]] = mapped_column(JSON)
    missing_skills: Mapped[List[str]] = mapped_column(JSON)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String) # accept, review, reject
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    job: Mapped["JobPosting"] = relationship("JobPosting", back_populates="results")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="results")
