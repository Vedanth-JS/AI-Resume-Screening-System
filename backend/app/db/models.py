from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    required_skills = Column(JSON) # List of skills
    min_experience = Column(Integer)
    required_education = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    results = relationship("ScreeningResult", back_populates="job")

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    resume_path = Column(String)
    raw_text = Column(Text)
    extracted_skills = Column(JSON)
    experience_years = Column(Integer)
    education = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    results = relationship("ScreeningResult", back_populates="candidate")

class ScreeningResult(Base):
    __tablename__ = "screening_results"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"))
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    
    total_score = Column(Float)
    skills_score = Column(Float)
    experience_score = Column(Float)
    education_score = Column(Float)
    semantic_score = Column(Float)
    
    matched_skills = Column(JSON)
    missing_skills = Column(JSON)
    feedback = Column(Text)
    status = Column(String) # accept, review, reject
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    job = relationship("JobPosting", back_populates="results")
    candidate = relationship("Candidate", back_populates="results")
