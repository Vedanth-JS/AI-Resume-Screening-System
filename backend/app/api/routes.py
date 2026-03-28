from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db import crud
from ..models import models
from ..schemas import schemas
from ..core.pipeline import ATSWorkflow
from ..core.chatbot import CandidateChatbot
from ..core.bias_detector import BiasDetector
from ..api.auth import get_current_user
from typing import List
import json

router = APIRouter()
workflow = ATSWorkflow()

@router.post("/jobs", response_model=schemas.JobResponse)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return crud.create_job_posting(db, job.title, job.description, job.required_skills, job.min_experience, job.required_education, current_user.id)

@router.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...), job_id: int = Form(...), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    content = await file.read()
    job = crud.get_job_posting(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    result = await workflow.process(content, file.filename, job.description, job.required_skills, job.min_experience)
    
    candidate = crud.create_candidate(
        db, name=result["candidate"]["name"], email=result["candidate"]["email"],
        phone=result["candidate"]["phone"], raw_text=result["candidate"]["raw_text"],
        parsed_json=result["candidate"]
    )
    
    # Create Screening Result
    crud.create_screening_result(
        db, candidate.id, job.id, result["final_result"]["final_score"], 
        0.0, result["final_result"]["final_score"], result["final_result"]["explanation"]
    )
    
    # Add to ChromaDB for RAG
    CandidateChatbot.add_candidate(candidate.id, candidate.raw_text, {"name": candidate.name, "email": candidate.email, "job_id": job.id})
    
    return {"message": "Success", "candidate_id": candidate.id, "analysis": result}

@router.get("/score/{candidate_id}")
async def get_candidate_score(candidate_id: int, db: Session = Depends(get_db)):
    result = db.query(models.ScreeningResult).filter(models.ScreeningResult.candidate_id == candidate_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Score not found")
    return result

@router.post("/llm/evaluate")
async def evaluate_candidate_llm(candidate_id: int, job_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    job = crud.get_job_posting(db, job_id)
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="Candidate or Job not found")
    
    from ..services.llm_service import LLMService
    evaluation = await LLMService.evaluate_candidate(job.description, candidate.raw_text)
    return {"evaluation": evaluation}

@router.post("/chat")
async def chat_candidates(query: str):
    results = CandidateChatbot.query_candidates(query)
    return {"results": results}

@router.get("/bias-report")
async def get_bias_report(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job_posting(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    report = BiasDetector.detect_bias(job.description)
    return report

@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    results = db.query(models.ScreeningResult).all()
    if not results:
        return {"count": 0, "avg_score": 0}
    avg = sum(r.final_score for r in results) / len(results)
    return {"count": len(results), "average_score": round(avg, 2)}

import zipfile
import io
from ..tasks.celery_tasks import process_resume_task

@router.get("/recommend-jobs/{candidate_id}")
async def recommend_jobs(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    jobs = db.query(models.JobPosting).all()
    recommendations = []
    
    for job in jobs:
        score = Scorer.get_similarity(candidate.raw_text, job.description)
        recommendations.append({
            "job_id": job.id,
            "title": job.title,
            "match_score": round(score * 100, 2)
        })
    
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations[:5]

@router.post("/bulk-upload")
async def bulk_upload_resumes(file: UploadFile = File(...), job_id: int = Form(...), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    job = crud.get_job_posting(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files allowed for bulk upload")
        
    content = await file.read()
    results = []
    
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        for filename in z.namelist():
            if filename.lower().endswith((".pdf", ".txt")):
                with z.open(filename) as f:
                    file_bytes = f.read()
                    process_resume_task.delay(
                        job_id, filename, file_bytes, 
                        job.description, job.required_skills, job.min_experience
                    )
                    results.append(filename)
    
    return {"message": f"Queued {len(results)} resumes for processing", "files": results}
