from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db import crud
from ..models import models
from ..schemas import schemas
from ..core.pipeline import ATSWorkflow
from ..core.chatbot import CandidateChatbot
from ..core.bias_detector import BiasDetector
from ..api.auth import get_current_user, check_admin
from ..core.scorer import Scorer
from ..core.logger import log
from typing import List
from datetime import datetime
import zipfile, io, csv

from ..tasks.celery_tasks import process_resume_task, process_batch_task

router = APIRouter()
workflow = ATSWorkflow()

# ─────────────────────────────────────────
# JOB POSTINGS
# ─────────────────────────────────────────

@router.post("/jobs", response_model=schemas.JobResponse)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    new_job = crud.create_job_posting(db, job.title, job.description, job.required_skills, job.min_experience, job.required_education, current_user.id)
    crud.create_notification(db, current_user.id, f"New job posted: {new_job.title}")
    return new_job

@router.get("/jobs", response_model=List[schemas.JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    return db.query(models.JobPosting).all()

@router.get("/jobs/{job_id}", response_model=schemas.JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job_posting(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/jobs/refresh")
def refresh_jobs(admin: models.User = Depends(check_admin), db: Session = Depends(get_db)):
    from app.services.job_fetcher import fetch_jobs
    external_jobs = fetch_jobs()
    for job in external_jobs:
        crud.create_job_posting(
            db,
            title=job["title"],
            description=job["description"],
            skills=job["skills"],
            min_exp=job["min_exp"],
            edu=job["edu"],
            user_id=admin.id,
        )
        crud.create_notification(db, admin.id, f"Refreshed job: {job['title']}")
    return {"detail": f"Added {len(external_jobs)} jobs"}

# ─────────────────────────────────────────
# CANDIDATES
# ─────────────────────────────────────────

@router.get("/candidates", response_model=List[schemas.CandidateWithScore])
def get_candidates(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Return all candidates with their latest screening score and job title."""
    return crud.get_all_candidates(db)

@router.get("/score/{candidate_id}")
async def get_candidate_score(candidate_id: int, db: Session = Depends(get_db)):
    result = db.query(models.ScreeningResult).filter(models.ScreeningResult.candidate_id == candidate_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Score not found")
    return result

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

# ─────────────────────────────────────────
# RESUME UPLOAD
# ─────────────────────────────────────────

@router.get("/history/{job_id}")
async def get_screening_history(job_id: int, db: Session = Depends(get_db)):
    results = db.query(models.ScreeningResult).filter(models.ScreeningResult.job_id == job_id).all()
    history = []
    for r in results:
        cand = db.query(models.Candidate).filter(models.Candidate.id == r.candidate_id).first()
        history.append({
            "id": r.id,
            "candidate_id": r.candidate_id,
            "candidate_name": cand.name if cand else "Unknown",
            "job_id": r.job_id,
            "final_score": r.final_score,
            "created_at": r.created_at,
            "analysis": r.explanation
        })
    return history

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
    crud.create_screening_result(
        db, candidate.id, job.id, result["final_result"]["final_score"],
        0.0, result["final_result"]["final_score"], result["final_result"]["explanation"]
    )
    CandidateChatbot.add_candidate(candidate.id, candidate.raw_text, {"name": candidate.name, "email": candidate.email, "job_id": job.id})
    return {"message": "Success", "candidate_id": candidate.id, "analysis": result}

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

# ─────────────────────────────────────────
# AI / ANALYTICS
# ─────────────────────────────────────────

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
        return {"count": 0, "avg_score": 0, "average_score": 0, "accept": 0, "review": 0, "reject": 0}
    avg = sum(r.final_score for r in results) / len(results)
    accept = sum(1 for r in results if r.final_score >= 70)
    review = sum(1 for r in results if 40 <= r.final_score < 70)
    reject = sum(1 for r in results if r.final_score < 40)
    return {
        "count": len(results),
        "average_score": round(avg, 2),
        "avg_score": round(avg, 2),
        "accept": accept,
        "review": review,
        "reject": reject
    }


# ─────────────────────────────────────────
# TASK STATUS POLLING
# ─────────────────────────────────────────

@router.get("/tasks/{task_id}/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Poll status of a Celery task. Returns status, progress, and result when done."""
    record = db.query(models.TaskRecord).filter(
        models.TaskRecord.celery_task_id == task_id
    ).first()
    if not record:
        # Also check Celery backend directly
        from ..tasks.celery_tasks import celery_app
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status":  result.state.lower() if result.state else "unknown",
            "progress": 100 if result.state == "SUCCESS" else 0,
            "result":  result.result if result.ready() else None,
        }

    return {
        "task_id":     task_id,
        "status":      record.status,
        "progress":    record.progress,
        "result":      record.result_json,
        "error":       record.error,
        "created_at":  record.created_at.isoformat() if record.created_at else None,
        "completed_at":record.completed_at.isoformat() if record.completed_at else None,
    }


# ─────────────────────────────────────────
# BATCH UPLOAD (ZIP)
# ─────────────────────────────────────────

@router.post("/batch/upload")
async def batch_upload(
    file: UploadFile = File(...),
    job_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Accept a ZIP of resumes + a job_id. Returns batch_id for polling."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only ZIP files accepted.")
    job = crud.get_job_posting(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found.")

    content = await file.read()
    filenames, file_contents = [], []
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        for fname in z.namelist():
            if fname.lower().endswith((".pdf", ".txt")):
                with z.open(fname) as f:
                    filenames.append(fname)
                    file_contents.append(list(f.read()))   # bytes→list for JSON serialization

    if not filenames:
        raise HTTPException(400, "No PDF/TXT files found in ZIP.")

    batch = models.BatchJob(
        created_by=current_user.id,
        job_id=job_id,
        jd_text=job.description,
        status="pending",
        total_files=len(filenames),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    task = process_batch_task.delay(
        batch.id,
        job_id,
        filenames,
        file_contents,
        job.description,
        job.required_skills or [],
        job.min_experience,
    )

    log.info("batch_upload.queued", batch_id=batch.id, files=len(filenames))
    return {
        "batch_id":    batch.id,
        "task_id":     task.id,
        "total_files": len(filenames),
        "message":     f"Processing {len(filenames)} resumes. Poll /api/batch/{batch.id}/results.",
    }


@router.get("/batch/{batch_id}/results")
def get_batch_results(batch_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get results for a completed batch job."""
    batch = db.query(models.BatchJob).filter(models.BatchJob.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch job not found.")
    return {
        "batch_id":       batch.id,
        "status":         batch.status,
        "total_files":    batch.total_files,
        "completed_files":batch.completed_files,
        "progress_pct":   round((batch.completed_files / batch.total_files) * 100, 1) if batch.total_files else 0,
        "results":        batch.result_json or [],
        "created_at":     batch.created_at.isoformat() if batch.created_at else None,
        "completed_at":   batch.completed_at.isoformat() if batch.completed_at else None,
    }


@router.get("/batch/{batch_id}/export")
def export_batch_results(
    batch_id: int,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Export batch results as CSV."""
    batch = db.query(models.BatchJob).filter(models.BatchJob.id == batch_id).first()
    if not batch or not batch.result_json:
        raise HTTPException(404, "Batch results not available yet.")

    results = batch.result_json
    if format.lower() != "csv":
        raise HTTPException(400, "Only format=csv is supported.")

    output = io.StringIO()
    fieldnames = ["rank", "filename", "name", "email", "final_score", "verdict",
                  "keyword_score", "semantic_score"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for i, row in enumerate(results, 1):
        writer.writerow({
            "rank":           i,
            "filename":       row.get("filename", ""),
            "name":           row.get("name", ""),
            "email":          row.get("email", ""),
            "final_score":    row.get("final_score", 0),
            "verdict":        row.get("verdict", ""),
            "keyword_score":  row.get("keyword_score", 0),
            "semantic_score": row.get("semantic_score", 0),
        })
    output.seek(0)

    filename = f"batch_{batch_id}_results.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

