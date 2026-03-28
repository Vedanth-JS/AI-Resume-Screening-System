from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    role: str = "recruiter"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class JobBase(BaseModel):
    title: str
    description: str
    required_skills: List[str]
    min_experience: int = 0
    required_education: str = "Not Specified"

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class CandidateBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class CandidateResponse(CandidateBase):
    id: int
    uploaded_at: datetime
    parsed_json: Optional[Dict[str, Any]] = None
    class Config:
        from_attributes = True

class ScreeningResultResponse(BaseModel):
    candidate_id: int
    job_id: int
    ats_score: float
    llm_score: Optional[float] = None
    final_score: float
    explanation: Optional[str] = None
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class BiasReportResponse(BaseModel):
    job_id: int
    report_json: Dict[str, Any]
    generated_at: datetime
    class Config:
        from_attributes = True
