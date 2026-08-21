"""Interview endpoints — generate kits, schedule interviews, submit scorecards, AI-powered comparison."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timezone

from ..db.database import get_db
from ..models import models
from ..api.auth import get_current_user_with_role, RoleEnum
from ..services.llm_service import GeminiService
from ..schemas.schemas import InterviewScheduleRequest, InterviewKitResponse
from ..services.email_service import EmailService

router = APIRouter()


@router.post("/candidates/{candidate_id}/interview-questions")
async def generate_interview_questions(
    candidate_id: int,
    job_id: int,
    focus_areas: List[str],
    difficulty: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user_with_role(RoleEnum.RECRUITER)
    ),
):
    candidate = await db.get(models.Candidate, candidate_id)
    job = await db.get(models.JobPosting, job_id)
    if not candidate or not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate or Job not found")

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
    import json
    response_text = await llm.generate_content(prompt)
    try:
        data = json.loads(response_text)
    except Exception:
        data = {"questions": []}

    kit = models.InterviewKit(
        job_id=job_id,
        candidate_id=candidate_id,
        focus_areas=focus_areas,
        difficulty=difficulty,
        questions=data.get("questions", []),
    )
    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return kit


# ─── Interview Scheduling ─────────────────────────────────────────────────────

@router.patch("/{kit_id}/schedule", summary="Schedule an interview")
async def schedule_interview(
    kit_id: int,
    payload: InterviewScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user_with_role(RoleEnum.RECRUITER)
    ),
):
    """
    Set scheduled_at, location, and meeting_link on an InterviewKit.
    Creates an in-app notification for the recruiter and fires an email if enabled.
    """
    kit = await db.get(models.InterviewKit, kit_id)
    if not kit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview kit not found")

    candidate = await db.get(models.Candidate, kit.candidate_id)
    job = await db.get(models.JobPosting, kit.job_id)

    # Update scheduling fields
    kit.scheduled_at = payload.scheduled_at
    kit.location = payload.location
    kit.meeting_link = payload.meeting_link

    # Create in-app notification for the recruiter
    date_str = payload.scheduled_at.strftime("%b %d, %Y %H:%M UTC")
    cand_name = candidate.name if candidate else "Candidate"
    job_title = job.title if job else "Role"

    notification = models.Notification(
        user_id=current_user.id,
        message=f"Interview scheduled: {cand_name} for {job_title} on {date_str}",
    )
    db.add(notification)
    await db.commit()
    await db.refresh(kit)

    # Fire email notification (non-blocking — logs only if EMAIL_ENABLED=false)
    EmailService.send_interview_scheduled(
        to_email=current_user.email,
        candidate_name=cand_name,
        job_title=job_title,
        scheduled_at=payload.scheduled_at,
        location=payload.location,
        meeting_link=payload.meeting_link,
    )

    return {
        "id": kit.id,
        "candidate_name": cand_name,
        "job_title": job_title,
        "scheduled_at": kit.scheduled_at,
        "location": kit.location,
        "meeting_link": kit.meeting_link,
        "message": "Interview scheduled successfully",
    }


@router.get("/upcoming", summary="List upcoming scheduled interviews")
async def list_upcoming_interviews(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user_with_role(RoleEnum.RECRUITER)
    ),
):
    """Return all interview kits with scheduled_at >= now for the org."""
    now = datetime.now(timezone.utc)

    # Get kits with future scheduled_at
    stmt = (
        select(models.InterviewKit)
        .join(models.JobPosting, models.JobPosting.id == models.InterviewKit.job_id)
        .where(
            models.JobPosting.org_id == current_user.org_id,
            models.InterviewKit.scheduled_at >= now,
        )
        .order_by(models.InterviewKit.scheduled_at.asc())
    )
    kits = (await db.execute(stmt)).scalars().all()

    result = []
    for kit in kits:
        candidate = await db.get(models.Candidate, kit.candidate_id)
        job = await db.get(models.JobPosting, kit.job_id)
        stmt_app = select(models.Application).where(
            models.Application.candidate_id == kit.candidate_id,
            models.Application.job_id == kit.job_id,
        )
        app = (await db.execute(stmt_app)).scalars().first()

        result.append({
            "id": kit.id,
            "candidate_id": kit.candidate_id,
            "candidate_name": candidate.name if candidate else "Unknown",
            "job_id": kit.job_id,
            "job_title": job.title if job else "Unknown",
            "application_id": app.id if app else None,
            "scheduled_at": kit.scheduled_at,
            "location": kit.location,
            "meeting_link": kit.meeting_link,
            "difficulty": kit.difficulty,
        })
    return {"upcoming": result, "count": len(result)}


# ─── AI-Powered Candidate Comparison ─────────────────────────────────────────

@router.get("/jobs/{job_id}/compare")
async def compare_candidates(
    job_id: int,
    candidate_ids: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user_with_role(RoleEnum.RECRUITER)
    ),
):
    import json

    id_list = [
        int(i.strip())
        for i in candidate_ids.split(",")
        if i.strip().isdigit()
    ]
    stmt = select(models.Application).where(
        models.Application.job_id == job_id,
        models.Application.candidate_id.in_(id_list),
    )
    apps = (await db.execute(stmt)).scalars().all()

    job = await db.get(models.JobPosting, job_id)
    comparison_data = []

    for app in apps:
        candidate = await db.get(models.Candidate, app.candidate_id)
        screening_stmt = select(models.ScreeningResult).where(
            models.ScreeningResult.application_id == app.id
        )
        screening = (await db.execute(screening_stmt)).scalars().first()

        comparison_data.append(
            {
                "candidate_id": app.candidate_id,
                "candidate_name": candidate.name if candidate else "Unknown",
                "overall_score": app.score,
                "skills": (
                    candidate.parsed_json.get("skills", [])
                    if candidate and isinstance(candidate.parsed_json, dict)
                    else []
                ),
                "experience": (
                    candidate.parsed_json.get("total_years_exp", 0)
                    if candidate and isinstance(candidate.parsed_json, dict)
                    else 0
                ),
                "education": (
                    candidate.parsed_json.get("education", [])
                    if candidate and isinstance(candidate.parsed_json, dict)
                    else []
                ),
                "granular_scores": {
                    "keywords": screening.keyword_score if screening else 0,
                    "skills": screening.skills_score if screening else 0,
                    "experience": screening.experience_score if screening else 0,
                    "education": screening.education_score if screening else 0,
                    "semantic": screening.semantic_score if screening else 0,
                },
                "matched_skills": screening.matched_skills if screening else [],
                "missing_skills": screening.missing_skills if screening else [],
                "xai_verdict": (
                    screening.xai_json.get("verdict") if screening and screening.xai_json else None
                ),
                "reasoning": screening.reasoning if screening else "",
            }
        )

    # ─── Real Gemini-powered AI comparison narrative ──────────────────────────
    ai_summary = None
    if comparison_data and job:
        try:
            llm = GeminiService()
            candidates_json = json.dumps(
                [
                    {
                        "name": c["candidate_name"],
                        "score": c["overall_score"],
                        "skills": c["skills"],
                        "experience_years": c["experience"],
                        "scores": c["granular_scores"],
                        "matched_skills": c["matched_skills"],
                        "missing_skills": c["missing_skills"],
                    }
                    for c in comparison_data
                ],
                indent=2,
            )
            prompt = f"""
You are a senior technical recruiter. Compare these candidates for the role of "{job.title}".

Job Description (summary): {(job.description or "")[:500]}

Candidates:
{candidates_json}

Provide a structured comparison. Return ONLY valid JSON:
{{
  "ranking": [
    {{"rank": 1, "name": "...", "reason": "1-2 sentence summary of why they rank here"}},
    ...
  ],
  "top_pick": "name of best candidate",
  "key_differentiators": ["3-5 bullet points comparing the candidates"],
  "recommendation": "2-3 sentence hire/no-hire recommendation for each candidate",
  "risk_flags": ["any concerns across the candidate pool"]
}}
"""
            raw = await llm.generate_content(prompt)
            # Strip markdown code fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            ai_summary = json.loads(clean.strip())
        except Exception as exc:
            ai_summary = {
                "error": "AI comparison unavailable",
                "detail": str(exc),
                "ranking": [],
                "top_pick": None,
                "key_differentiators": [],
                "recommendation": "Manual review recommended.",
                "risk_flags": [],
            }

    return {
        "job_id": job_id,
        "job_title": job.title if job else "Unknown",
        "candidates": comparison_data,
        "ai_summary": ai_summary,
    }
