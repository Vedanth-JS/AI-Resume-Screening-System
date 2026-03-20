from sqlalchemy.orm import Session
from sqlalchemy import select
from . import models
from typing import List

def create_job_posting(db: Session, title: str, description: str, skills: List[str], min_exp: int, edu: str):
    db_job = models.JobPosting(
        title=title,
        description=description,
        required_skills=skills,
        min_experience=min_exp,
        required_education=edu
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job_posting(db: Session, job_id: int):
    return db.get(models.JobPosting, job_id)

def create_candidate(db: Session, name: str, email: str, path: str, text: str, skills: List[str], exp: int, edu: str):
    db_candidate = models.Candidate(
        name=name,
        email=email,
        resume_path=path,
        raw_text=text,
        extracted_skills=skills,
        experience_years=exp,
        education=edu
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

def get_candidate(db: Session, candidate_id: int):
    return db.get(models.Candidate, candidate_id)

def create_screening_result(db: Session, job_id: int, candidate_id: int, scores: dict, matched: list, missing: list, status: str):
    db_result = models.ScreeningResult(
        job_id=job_id,
        candidate_id=candidate_id,
        total_score=scores["total_score"],
        skills_score=scores["skills_score"],
        experience_score=scores["experience_score"],
        education_score=scores["education_score"],
        semantic_score=scores["semantic_score"],
        matched_skills=matched,
        missing_skills=missing,
        status=status
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_screening_results(db: Session, job_id: int):
    stmt = select(models.ScreeningResult).where(models.ScreeningResult.job_id == job_id).order_by(models.ScreeningResult.total_score.desc())
    return db.scalars(stmt).all()
