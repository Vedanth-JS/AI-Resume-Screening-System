from sqlalchemy.orm import Session
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
