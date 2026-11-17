"""
Pydantic v2 schemas for the Advanced ATS Resume Screening and Scoring Engine.
Supports 8-criteria weighted evaluation, skill gap analysis, recruiter recommendations,
and full candidate extraction schemas.
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SemanticMatch(BaseModel):
    jd_term: str = Field(..., description="Term required by the JD or inferred role benchmark")
    resume_term: str = Field(..., description="Matching or semantically equivalent term found in resume")


class KeywordAnalysis(BaseModel):
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords confirmed present in candidate profile")
    missing_critical_keywords: List[str] = Field(default_factory=list, description="Critical must-have keywords missing from candidate profile")
    semantic_matches: List[SemanticMatch] = Field(default_factory=list, description="Pairs of semantic/synonym matches detected")


class SkillItem(BaseModel):
    skill: str = Field(..., description="Skill name")
    reason: str = Field(..., description="Detailed explanation of why this skill was classified")


class SkillGapAnalysis(BaseModel):
    matching_skills: List[SkillItem] = Field(default_factory=list, description="Skills meeting role requirements")
    missing_mandatory_skills: List[SkillItem] = Field(default_factory=list, description="Critical required skills missing")
    missing_preferred_skills: List[SkillItem] = Field(default_factory=list, description="Nice-to-have skills missing")
    partially_matching_skills: List[SkillItem] = Field(default_factory=list, description="Partially overlapping or adjacent skills")
    additional_skills: List[str] = Field(default_factory=list, description="Candidate skills not specified in requirements")
    relevant_technologies: List[str] = Field(default_factory=list, description="Adjacent or complementary tools observed")


class RecruiterRecommendation(BaseModel):
    verdict: Literal["Shortlist", "Consider for Interview", "Needs Further Review", "Not Recommended"] = Field(
        ..., description="Actionable screening recommendation"
    )
    reasoning: str = Field(..., description="Detailed objective reasoning supporting the recommendation")
    score_explanation: str = Field(..., description="Transparent breakdown of how the final score was derived")


class ATSCriteriaWeights(BaseModel):
    technical_skills: float = Field(default=30.0, ge=0, le=100)
    jd_relevance: float = Field(default=20.0, ge=0, le=100)
    relevant_experience: float = Field(default=15.0, ge=0, le=100)
    project_relevance: float = Field(default=10.0, ge=0, le=100)
    education_match: float = Field(default=10.0, ge=0, le=100)
    certifications: float = Field(default=5.0, ge=0, le=100)
    keywords_match: float = Field(default=5.0, ge=0, le=100)
    resume_quality: float = Field(default=5.0, ge=0, le=100)


class ATSScoreBreakdown(BaseModel):
    # 8 Default Weighted Criteria (each 0 to 100 scaled or weighted contribution)
    technical_skills_score: float = Field(default=0.0, ge=0, le=100, description="Technical Skills Match (30% weight)")
    jd_relevance_score: float = Field(default=0.0, ge=0, le=100, description="Job Description Relevance (20% weight)")
    relevant_experience_score: float = Field(default=0.0, ge=0, le=100, description="Relevant Experience (15% weight)")
    project_relevance_score: float = Field(default=0.0, ge=0, le=100, description="Project Relevance (10% weight)")
    education_match_score: float = Field(default=0.0, ge=0, le=100, description="Education Match (10% weight)")
    certifications_score: float = Field(default=0.0, ge=0, le=100, description="Certifications Match (5% weight)")
    keywords_match_score: float = Field(default=0.0, ge=0, le=100, description="Keywords Match (5% weight)")
    resume_quality_score: float = Field(default=0.0, ge=0, le=100, description="Resume Quality & Formatting (5% weight)")

    # Backward-compatible 4-component integer fields
    hard_skills_score: Optional[int] = Field(default=None, ge=0, le=40)
    experience_score: Optional[int] = Field(default=None, ge=0, le=25)
    impact_metrics_score: Optional[int] = Field(default=None, ge=0, le=20)
    formatting_and_education_score: Optional[int] = Field(default=None, ge=0, le=15)


class ActionableImprovement(BaseModel):
    section: str = Field(..., description="Resume section needing improvement")
    issue: str = Field(..., description="Specific defect, gap, or sub-optimal pattern detected")
    suggested_fix: str = Field(..., description="Concrete, actionable rewrite or addition")


class ParsedCandidateProfile(BaseModel):
    name: str = Field(default="Candidate", description="Full extracted name")
    email: Optional[str] = Field(default=None, description="Contact email")
    phone: Optional[str] = Field(default=None, description="Contact phone")
    education: Optional[str] = Field(default=None, description="Highest degree detected")
    college: Optional[str] = Field(default=None, description="College or University")
    graduation_year: Optional[str] = Field(default=None, description="Graduation year")
    technical_skills: List[str] = Field(default_factory=list, description="All technical skills identified")
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    tools_and_technologies: List[str] = Field(default_factory=list)
    work_experience_years: float = Field(default=0.0, description="Calculated years of experience")
    experience_entries: List[Dict[str, Any]] = Field(default_factory=list)
    internship_experience: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    raw_text: str = Field(default="", description="Cleaned raw resume text")


class CandidateScreeningResult(BaseModel):
    id: str = Field(..., description="Unique candidate or file id")
    rank: int = Field(default=1, description="Rank ordered by highest ATS score")
    candidate: ParsedCandidateProfile
    overall_ats_score: Optional[int] = Field(default=None, description="ATS Compatibility Score (0-100), None on extraction error")
    match_tier: Optional[str] = Field(
        default=None,
        description="Excellent Match (90-100) | Strong Match (80-89) | Good Match (70-79) | Moderate Match (60-69) | Low Match (40-59) | Poor Match (0-39)"
    )
    recommendation: Optional[RecruiterRecommendation] = None
    breakdown: Optional[ATSScoreBreakdown] = None
    skill_gap_analysis: Optional[SkillGapAnalysis] = None
    keyword_analysis: Optional[KeywordAnalysis] = None
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    actionable_improvements: List[ActionableImprovement] = Field(default_factory=list)
    status: Literal["COMPLETED", "ERROR"] = Field(default="COMPLETED")
    extraction_error: Optional[str] = Field(default=None, description="Details if resume extraction failed")
    file_name: str = Field(..., description="Uploaded file name")
    file_size: int = Field(default=0, description="File size in bytes")


class CustomJDConfig(BaseModel):
    title: str = Field(default="", description="Custom Job Title")
    description: str = Field(default="", description="Full Job Description text")
    required_skills: List[str] = Field(default_factory=list, description="Must-have technical skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills")
    min_experience: float = Field(default=0.0, description="Minimum experience in years")
    educational_qualifications: str = Field(default="", description="Required education")
    mandatory_requirements: List[str] = Field(default_factory=list, description="Mandatory specific requirements")


class ATSScoreResponse(BaseModel):
    overall_ats_score: int = Field(..., ge=0, le=100, description="Total ATS score (0-100)")
    match_tier: str = Field(..., description="Candidate match tier classification")
    input_mode_used: Literal["job_description", "inferred_role"] = Field(
        ..., description="Whether scoring ran against explicit JD or dynamically inferred role"
    )
    breakdown: ATSScoreBreakdown
    keyword_analysis: KeywordAnalysis
    skill_gap_analysis: Optional[SkillGapAnalysis] = None
    recommendation: Optional[RecruiterRecommendation] = None
    strengths: List[str] = Field(default_factory=list)
    critical_gaps: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    actionable_improvements: List[ActionableImprovement] = Field(default_factory=list)


class ATSScoreRequest(BaseModel):
    resume_text: Optional[str] = Field(default=None, description="Plain text extracted from candidate resume")
    job_description: Optional[str] = Field(default=None, description="Full text job description with requirements")
    job_role: Optional[str] = Field(default=None, description="Target job title / role")
    custom_jd: Optional[CustomJDConfig] = Field(default=None, description="Detailed custom JD specifications")
    weights: Optional[ATSCriteriaWeights] = Field(default=None, description="Optional custom evaluation weights")
    parsed_resume: Optional[Dict[str, Any]] = Field(default=None, description="Optional pre-parsed resume object")


class BulkScreenRequest(BaseModel):
    job_role: Optional[str] = None
    custom_jd: Optional[CustomJDConfig] = None
    weights: Optional[ATSCriteriaWeights] = None


class BulkScreenResponse(BaseModel):
    job_role_used: str
    input_mode_used: str
    total_processed: int
    successful_count: int
    error_count: int
    average_score: float
    candidates: List[CandidateScreeningResult]
