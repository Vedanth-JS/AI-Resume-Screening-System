"""
Structured Resume Schema — Canonical representation after parsing + enrichment.
All dates are ISO 8601 strings. All durations are in months.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class EducationEntry(BaseModel):
    school: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[float] = None
    description: str = ""


class ExperienceEntry(BaseModel):
    company: str = ""
    title: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    duration_months: float = 0.0
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    title: str = ""
    description: str = ""
    url: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class CertificationEntry(BaseModel):
    name: str = ""
    issuer: str = ""
    date_obtained: Optional[str] = None
    expiration_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class LanguageEntry(BaseModel):
    language: str = ""
    proficiency: str = ""  # native | fluent | advanced | intermediate | basic


class SocialProfile(BaseModel):
    github: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None
    stackoverflow: Optional[str] = None


class GitHubContribution(BaseModel):
    total_commits: int = 0
    total_prs: int = 0
    total_repos: int = 0
    languages_used: List[str] = Field(default_factory=list)
    top_repos: List[str] = Field(default_factory=list)


class ResumeDocument(BaseModel):
    """Canonical resume representation after parsing + enrichment."""

    # Identity
    name: str = "Unknown"
    email: str = ""
    phone: str = ""
    location: str = ""
    social: SocialProfile = Field(default_factory=SocialProfile)

    # Parsed sections
    skills: List[str] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    languages: List[LanguageEntry] = Field(default_factory=list)

    # Computed
    total_years_experience: float = 0.0
    highest_education: str = ""
    skills_by_category: Dict[str, List[str]] = Field(default_factory=dict)

    # Metadata
    raw_text: str = ""
    parsed_text: str = ""
    source_format: str = ""          # pdf | docx | image | txt
    source_language: str = "en"
    ocr_applied: bool = False
    parsing_confidence: float = 0.0
    file_hash: str = ""
    extracted_date: Optional[datetime] = None

    # Enrichment
    github_profile: Optional[GitHubContribution] = None
    linkedin_enriched: bool = False

    # Quality / Integrity
    quality_score: float = 0.0       # 0–100
    completeness_score: float = 0.0  # 0–100
    is_duplicate: bool = False
    duplicate_of_id: Optional[int] = None
    fraud_flags: List[str] = Field(default_factory=list)
    fraud_risk_score: float = 0.0    # 0–1
