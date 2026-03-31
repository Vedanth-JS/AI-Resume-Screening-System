from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import models
import json

def create_user(db: Session, email: str, password_hash: str, role: str = "recruiter"):
    user = models.User(email=email, password_hash=password_hash, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_job_posting(db: Session, title: str, description: str, skills: list, min_exp: int, edu: str, user_id: int):
    job = models.JobPosting(
        title=title, description=description, required_skills=skills,
        min_experience=min_exp, required_education=edu, created_by=user_id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def create_candidate(db: Session, name: str, email: str, phone: str, raw_text: str, parsed_json: dict):
    candidate = models.Candidate(
        name=name, email=email, phone=phone, raw_text=raw_text, parsed_json=parsed_json
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate

def create_screening_result(db: Session, candidate_id: int, job_id: int, ats_score: float, llm_score: float, final_score: float, explanation: str):
    result = models.ScreeningResult(
        candidate_id=candidate_id, job_id=job_id, ats_score=ats_score,
        llm_score=llm_score, final_score=final_score, explanation=explanation
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result

def get_job_posting(db: Session, job_id: int):
    return db.query(models.JobPosting).filter(models.JobPosting.id == job_id).first()

def get_all_candidates(db: Session):
    """Return all candidates joined with their latest screening result and job title."""
    candidates = db.query(models.Candidate).all()
    result = []
    for cand in candidates:
        # Get most recent screening result
        screening = (
            db.query(models.ScreeningResult)
            .filter(models.ScreeningResult.candidate_id == cand.id)
            .order_by(models.ScreeningResult.created_at.desc())
            .first()
        )
        job_title = None
        if screening:
            job = db.query(models.JobPosting).filter(models.JobPosting.id == screening.job_id).first()
            job_title = job.title if job else None

        result.append({
            "id": cand.id,
            "name": cand.name,
            "email": cand.email,
            "phone": cand.phone,
            "uploaded_at": cand.uploaded_at,
            "final_score": screening.final_score if screening else None,
            "status": screening.status if screening else "pending",
            "job_title": job_title,
            "job_id": screening.job_id if screening else None,
        })
    return result

# ─── Notification CRUD ───────────────────────────────────────────────────────

def create_notification(db: Session, user_id: int, message: str):
    notif = models.Notification(user_id=user_id, message=message)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

def get_user_notifications(db: Session, user_id: int):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )
