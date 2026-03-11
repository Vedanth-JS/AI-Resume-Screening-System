from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class RecommendationEnum(str, Enum):
    strong_fit = "Strong Fit"
    maybe = "Maybe"
    reject = "Reject"


# --- Job Schemas ---
class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str] = []
    experience_level: str = "Mid-level"


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    required_skills: List[str]
    experience_level: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Candidate Schemas ---
class CandidateOut(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    original_filename: Optional[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True


# --- Screening Schemas ---
class ScreenRequest(BaseModel):
    candidate_id: int
    job_id: int


class BatchScreenRequest(BaseModel):
    candidate_ids: List[int]
    job_id: int


class ScreeningResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    matched_skills: List[str]
    missing_skills: List[str]
    summary: str
    recommendation: RecommendationEnum


class ScreeningOut(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    ai_summary: Optional[str]
    recommendation: RecommendationEnum
    screened_at: datetime
    candidate: CandidateOut

    class Config:
        from_attributes = True


class ScreeningWithJob(ScreeningOut):
    job: JobOut

    class Config:
        from_attributes = True
