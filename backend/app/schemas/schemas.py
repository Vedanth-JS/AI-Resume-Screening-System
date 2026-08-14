"""
Pydantic v2 Response Models — full type coverage for every API endpoint.

All models use ConfigDict(from_attributes=True) for ORM compatibility.
Generic PaginatedResponse[T] works with any item type.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, EmailStr, ConfigDict, Field

T = TypeVar("T")


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    role: str = "recruiter"


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# ─── Pagination ───────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated wrapper for any list endpoint."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ─── Jobs ─────────────────────────────────────────────────────────────────────

class JobBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, examples=["Senior Python Engineer"])
    description: str = Field(..., min_length=50, examples=["We are looking for..."])
    required_skills: Any = Field(default_factory=list, description="List or dict of required skills")
    min_experience: int = Field(default=0, ge=0, le=30)
    required_education: str = Field(default="Not Specified")


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    id: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ─── Score Breakdown ──────────────────────────────────────────────────────────

class ScoreWeights(BaseModel):
    """Configured weights for each scoring component."""
    keyword: float
    semantic: float
    format: float
    section: float
    experience: float


class ScoreBreakdownResponse(BaseModel):
    """
    Complete 5-component ATS score breakdown.
    All scores are 0–100. overall_score is the weighted composite.
    """
    overall_score: float = Field(..., ge=0, le=100, description="Weighted composite score (0-100)")
    keyword_score: float = Field(default=0.0, description="Taxonomy + fuzzy skill match (0-100)")
    semantic_score: Optional[float] = Field(None, description="Embedding cosine similarity (0-100)")
    format_score: float = Field(default=0.0, description="Resume format quality (0-100)")
    section_score: Optional[float] = Field(None, description="Section completeness (0-100)")
    experience_score: float = Field(default=0.0, description="Years-of-experience match (0-100)")
    matched_skills: List[str] = Field(default_factory=list, description="JD skills found in resume")
    missing_skills: List[str] = Field(default_factory=list, description="Required JD skills absent from resume")
    red_flags: List[str] = Field(default_factory=list, description="LLM-identified concerns")
    weights: Optional[ScoreWeights] = None


class XAIReasoningResponse(BaseModel):
    """Explainable AI reasoning for a hiring decision."""
    verdict: str = Field(..., description="ACCEPT | REVIEW | REJECT")
    overall_score: float
    reasoning: Dict[str, str] = Field(
        ...,
        description="Per-dimension explanations: keyword, semantic, format, section, experience"
    )
    key_strengths: List[str] = Field(default_factory=list)
    key_gaps: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    hiring_recommendation: str
    source: str = Field(default="llm", description="llm | rule_based")


class HybridScoreResponse(BaseModel):
    """Complete AI analysis result returned by the upload endpoint."""
    score: float = Field(..., description="Composite ATS score (0-100)")
    verdict: str = Field(..., description="ACCEPT | REVIEW | REJECT")
    breakdown: Optional[ScoreBreakdownResponse] = None
    xai: Optional[XAIReasoningResponse] = None
    interview_questions: Optional[List[Dict[str, str]]] = None
    bias_report: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None


# ─── Candidates ──────────────────────────────────────────────────────────────

class CandidateBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None


class CandidateResponse(CandidateBase):
    id: int
    created_at: datetime
    parsed_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class CandidateWithScore(BaseModel):
    """Candidate enriched with latest screening result — for ranking table."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime
    final_score: Optional[float] = None
    keyword_score: Optional[float] = None
    semantic_score: Optional[float] = None
    format_score: Optional[float] = None
    section_score: Optional[float] = None
    experience_score: Optional[float] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    verdict: Optional[str] = None
    status: Optional[str] = "pending"
    job_title: Optional[str] = None
    job_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# ─── Screening Results ────────────────────────────────────────────────────────

class ScreeningResultResponse(BaseModel):
    """Full screening result for one candidate-job pair."""
    id: int
    application_id: int
    job_id: int
    score: float
    keyword_score: float
    semantic_score: Optional[float] = None
    skills_score: float
    experience_score: float
    format_score: float
    section_score: Optional[float] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    red_flags: Optional[List[str]] = None
    xai_json: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    bias_flags: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ─── Upload Responses ─────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """
    Response from POST /resume/upload.
    Synchronous upload — returns full analysis immediately.
    """
    success: bool
    message: str
    application_id: int
    candidate_id: Optional[int] = None
    analysis: Optional[HybridScoreResponse] = None


class BulkUploadResponse(BaseModel):
    """
    Response from POST /bulk-upload.
    Asynchronous — use batch_job_id to poll progress.
    """
    success: bool
    message: str
    batch_job_id: int
    files: List[str] = Field(description="Filenames that were queued")
    poll_url: str = Field(description="URL to poll batch progress")


# ─── Task & Batch Status ──────────────────────────────────────────────────────

class TaskStatusResponse(BaseModel):
    """Celery task progress state for SSE/polling."""
    task_id: str
    status: str = Field(description="PENDING | STARTED | PROCESSING | SUCCESS | FAILED | RETRYING")
    progress: int = Field(default=0, ge=0, le=100, description="Completion percentage (0-100)")
    current_step: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


class BatchStatusResponse(BaseModel):
    """BatchJob progress for bulk upload polling."""
    batch_job_id: int
    status: str
    total_files: int
    completed_files: int
    progress_pct: int
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ─── Other Responses ──────────────────────────────────────────────────────────

class NotificationCreate(BaseModel):
    user_id: int
    message: str


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    message: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BiasReportResponse(BaseModel):
    job_id: int
    report_json: Dict[str, Any]
    generated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: Optional[int] = Field(default=20, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None


class MetricsResponse(BaseModel):
    """Dashboard metrics summary."""
    count: int
    average_score: float
    accept: int = Field(description="Applications with score >= 70")
    review: int = Field(description="Applications with score 40-70")
    reject: int = Field(description="Applications with score < 40")
