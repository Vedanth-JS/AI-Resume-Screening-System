from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..db.database import get_db
from ..db import crud, models
from ..tasks.celery_tasks import process_resume_task, run_screening_logic
import os
from ..core.bias_detector import BiasDetector
import json

router = APIRouter()

@router.post("/job", response_model=dict)
def create_job(
    title: str = Form(...),
    description: str = Form(...),
    skills: str = Form(...), # JSON string
    min_exp: int = Form(...),
    edu: str = Form(...),
    db: Session = Depends(get_db)
):
    skills_list = json.loads(skills)
    job = crud.create_job_posting(db, title, description, skills_list, min_exp, edu)
    
    # Detect Bias in JD
    biases = BiasDetector.detect_bias(description)
    flags = BiasDetector.flag_requirements(description)
    
    return {
        "job_id": job.id,
        "biases": biases,
        "flags": flags
    }

@router.get("/jobs", response_model=List[dict])
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(models.JobPosting).all()
    return [{"id": j.id, "title": j.title} for j in jobs]

@router.post("/screen", response_model=dict)
async def screen_resumes(
    job_id: int = Form(...),
    resumes: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    job = crud.get_job_posting(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    task_ids = []
    for resume in resumes:
        content = await resume.read()
        # Mocking email extraction for now, usually part of NER
        email = f"candidate_{resume.filename}@example.com"
        
        # Dispatch to Celery or Fallback to Sync
        try:
            # Check if Redis is likely available
            if os.getenv("REDIS_URL"):
                task = process_resume_task.delay(job_id, resume.filename, content, email)
                task_ids.append(task.id)
            else:
                # Fallback to sync execution
                run_screening_logic(job_id, resume.filename, content, email)
                task_ids.append(f"sync_{resume.filename}")
        except Exception:
            # Fallback to sync on any connection error
            run_screening_logic(job_id, resume.filename, content, email)
            task_ids.append(f"sync_{resume.filename}")
        
    return {"message": "Screening completed" if not os.getenv("REDIS_URL") else "Screening started", "task_ids": task_ids}

@router.get("/results/{job_id}", response_model=List[dict])
def get_results(job_id: int, db: Session = Depends(get_db)):
    results = crud.get_screening_results(db, job_id)
    output = []
    for r in results:
        candidate = crud.get_candidate(db, r.candidate_id)
        output.append({
            "candidate_name": candidate.name,
            "total_score": r.total_score,
            "skills_score": r.skills_score,
            "experience_score": r.experience_score,
            "semantic_score": r.semantic_score,
            "matched_skills": r.matched_skills,
            "missing_skills": r.missing_skills,
            "status": r.status
        })
    return output

@router.get("/analytics/{job_id}", response_model=dict)
def get_analytics(job_id: int, db: Session = Depends(get_db)):
    results = crud.get_screening_results(db, job_id)
    if not results:
        return {"error": "No results found"}
        
    avg_score = sum(r.total_score for r in results) / len(results)
    status_counts = {"accept": 0, "review": 0, "reject": 0}
    for r in results:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        
    return {
        "count": len(results),
        "average_score": round(avg_score, 2),
        "funnel": status_counts
    }
