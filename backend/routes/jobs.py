from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Job
from schemas import JobCreate, JobOut

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobOut)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    db_job = Job(
        title=job.title,
        description=job.description,
        required_skills=job.required_skills,
        experience_level=job.experience_level,
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
