from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="recruiter") # admin, recruiter, interviewer

class JobPosting(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    required_skills = Column(JSON) # List[str]
    min_experience = Column(Integer, default=0)
    required_education = Column(String, default="Not Specified")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, index=True)
    phone = Column(String, nullable=True)
    raw_text = Column(Text)
    parsed_json = Column(JSON)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class ScreeningResult(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    ats_score = Column(Float)
    llm_score = Column(Float, nullable=True)
    final_score = Column(Float)
    explanation = Column(Text, nullable=True)
    status = Column(String, default="pending") # accept, review, reject
    created_at = Column(DateTime, default=datetime.utcnow)

class BiasReport(Base):
    __tablename__ = "bias_reports"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    report_json = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
