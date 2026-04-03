from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import json

from ..db.database import get_db
from ..models import models
from ..api.auth import get_current_user_with_role, RoleEnum
from ..services.llm_service import GeminiService

router = APIRouter()
RecruiterOnly = get_current_user_with_role(RoleEnum.RECRUITER)

@router.post("/candidates/{candidate_id}/interview-questions")
async def generate_interview_questions(
    candidate_id: int,
    job_id: int,
    focus_areas: List[str],
    difficulty: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly)
):
    """
    Generate tailored interview questions using Gemini based on resume and JD.
    """
    # 1. Fetch Candidate and Job
    candidate = await db.get(models.Candidate, candidate_id)
    job = await db.get(models.JobPosting, job_id)
    
    if not candidate or not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate or Job not found")

    # 2. Call LLM Service
    llm = GeminiService()
    prompt = f"""
    You are an expert technical recruiter. Generate a professional interview kit for:
    Candidate: {candidate.name}
    Job: {job.title}
    Job Description: {job.description}
    Focus Areas: {", ".join(focus_areas)}
    Difficulty: {difficulty}

    Generate 5 technical questions, 3 behavioral, and 2 situational questions.
    Return JSON format:
    {{
        "questions": [
            {{
                "type": "TECHNICAL|BEHAVIORAL|SITUATIONAL",
                "question": "text",
                "expected_answer_points": ["point1", "point2"],
                "follow_ups": ["q1", "q2"],
                "difficulty": "{difficulty}"
            }}
        ]
    }}
    """
    response_text = await llm.generate_content(prompt)
    try:
        data = json.loads(response_text)
    except:
        # Fallback if LLM output isn't clean JSON
        data = {"questions": []}

    # 3. Save to InterviewKit
    kit = models.InterviewKit(
        job_id=job_id,
        candidate_id=candidate_id,
        focus_areas={"areas": focus_areas},
        difficulty=difficulty,
        questions=data["questions"]
    )
    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    
    return kit

@router.get("/jobs/{job_id}/compare")
async def compare_candidates(
    job_id: int,
    candidate_ids: str, # Comma separated
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly)
):
    """
    Side-by-side comparison of candidates for a specific job.
    """
    id_list = [int(i.strip()) for i in candidate_ids.split(",") if i.strip().isdigit()]
    
    stmt = select(models.Application).where(
        models.Application.job_id == job_id,
        models.Application.candidate_id.in_(id_list)
    )
    apps = (await db.execute(stmt)).scalars().all()
    
    comparison_data = []
    for app in apps:
        candidate = await db.get(models.Candidate, app.candidate_id)
        # Fetch screening results for charts
        stmt_s = select(models.ScreeningResult).where(models.ScreeningResult.application_id == app.id)
        screening = (await db.execute(stmt_s)).scalars().first()
        
        comparison_data.append({
            "candidate_name": candidate.name,
            "overall_score": app.score,
            "skills": candidate.parsed_json.get("skills", []),
            "experience": candidate.parsed_json.get("total_years_exp", 0),
            "granular_scores": {
                "keywords": screening.keyword_score if screening else 0,
                "skills": screening.skills_score if screening else 0,
                "experience": screening.experience_score if screening else 0,
                "education": screening.education_score if screening else 0,
            }
        })
    
    return {
        "job_id": job_id,
        "candidates": comparison_data,
        "ai_summary": "Summary logic using Gemini can be added here."
    }
