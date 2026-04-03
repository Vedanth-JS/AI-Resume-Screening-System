from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from ..db.database import get_db
from ..db.repositories.job_repo import JobRepository
from ..db.repositories.candidate_repo import CandidateRepository
from ..db.repositories.application_repo import ApplicationRepository
from ..models import models
from ..schemas import schemas, auth
from ..core.pipeline import ATSWorkflow
from ..embeddings.search import SemanticSearch
from ..agents.orchestrator import ScreeningOrchestrator
from ..api.auth import get_current_user_with_role, RoleEnum
from ..bias.anonymizer import CandidateAnonymizer
from ..scoring.ats_scorer import ATSScorer
from ..services.feedback_service import FeedbackService
from ..core.logger import log
from typing import List, Optional, Dict, Any
import zipfile, io, time, csv
from fastapi.responses import StreamingResponse

router = APIRouter()
workflow = ATSWorkflow()

# ─── Auth Dependency Short-cuts ─────────────────────────────────────────────
AdminOnly = get_current_user_with_role(RoleEnum.ADMIN)
RecruiterOnly = get_current_user_with_role(RoleEnum.RECRUITER)
ViewerOnly = get_current_user_with_role(RoleEnum.VIEWER)

# ─── Job Management ─────────────────────────────────────────────────────────

@router.post("/jobs", response_model=schemas.JobResponse)
async def create_job(job: schemas.JobCreate, request: Request, db: AsyncSession = Depends(get_db), current_user = Depends(RecruiterOnly)):
    repo = JobRepository(db)
    new_job = await repo.create(
        org_id=request.state.org_id,
        title=job.title,
        description=job.description,
        required_skills=job.required_skills,
        min_experience=job.min_experience,
        status="active"
    )
    return new_job

@router.get("/jobs", response_model=List[schemas.JobResponse])
async def get_jobs(request: Request, db: AsyncSession = Depends(get_db), current_user = Depends(ViewerOnly)):
    repo = JobRepository(db)
    return await repo.list_by_org(request.state.org_id)

@router.get("/jobs/{job_id}", response_model=schemas.JobResponse)
async def get_job(job_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user = Depends(ViewerOnly)):
    repo = JobRepository(db)
    job = await repo.get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# ─── Candidate & Screening ──────────────────────────────────────────────────

@router.post("/resume/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    job_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    # 1. Fetch Job
    job_repo = JobRepository(db)
    job = await job_repo.get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # 2. Run Pipeline
    content = await file.read()
    result = await workflow.process(
        content, file.filename, job.description, 
        job.required_skills, job.min_experience, request.state.org_id
    )
    
    # 3. Save Candidate
    cand_repo = CandidateRepository(db)
    candidate = await cand_repo.create(
        org_id=request.state.org_id,
        name=result["candidate"]["name"],
        email=result["candidate"]["email"],
        phone=result["candidate"]["phone"],
        raw_text=result["candidate"]["raw_text"],
        parsed_json=result["candidate"],
        status="new"
    )
    
    # 4. Save Application & Result
    app_repo = ApplicationRepository(db)
    application = await app_repo.create(
        org_id=request.state.org_id,
        candidate_id=candidate.id,
        job_id=job.id,
        score=result["score"],
        status="SCREENED"
    )
    
    # 5. Index for RAG
    rag = RAGService(db)
    await rag.index_candidate(candidate)
    
    return {"message": "Success", "application_id": application.id, "analysis": result}

@router.post("/applications/{application_id}/feedback")
async def get_candidate_feedback(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    """Generates personalized feedback using Gemini."""
    stmt = select(models.Application).where(models.Application.id == application_id)
    app = (await db.execute(stmt)).scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")
        
    candidate = await CandidateRepository(db).get(app.candidate_id)
    screening = await db.execute(select(models.ScreeningResult).where(models.ScreeningResult.application_id == app.id))
    result = screening.scalars().first()
    
    feedback = await FeedbackService.generate_candidate_feedback(
        candidate.raw_text, 
        {"overall_score": app.score, "reasoning": result.reasoning if result else ""}
    )
    return feedback

@router.post("/screen/anonymous")
async def screen_anonymous(
    candidate_id: int,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    """Runs a bias-masked screening to compare with standard scores."""
    candidate = await CandidateRepository(db).get(candidate_id)
    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
    
    anonymizer = CandidateAnonymizer()
    masked_data = anonymizer.mask_candidate_metadata({
        "email": candidate.email,
        "raw_text": candidate.raw_text
    })
    
    scorer = ATSScorer()
    res = scorer.score(masked_data, {"description": job.description, "required_skills": job.required_skills})
    
    return {
        "original_score": candidate.status, # Placeholder or fetch actual
        "anonymized_score": res["total_score"],
        "diff": 0, # Logic to compare
        "bias_flags": []
    }

@router.post("/jobs/{job_id}/match-candidates")
async def match_candidates_for_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    job = await JobRepository(db).get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    search_service = SemanticSearch(db)
    matches = await search_service.find_matches_for_job(
        job_id=job.id,
        job_description=job.description,
        org_id=request.state.org_id
    )
    return {"matches_found": len(matches), "candidates": matches}

# ─── Interview Assistant ────────────────────────────────────────────────────

@router.post("/candidates/{candidate_id}/interview-questions")
async def generate_interview_kit(
    candidate_id: int, 
    job_id: int, 
    focus_areas: List[str] = Form(...), 
    difficulty: str = Form("MID"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    # 1. Fetch data
    job = await JobRepository(db).get_by_id_org(job_id, request.state.org_id)
    candidate = await CandidateRepository(db).get(candidate_id) # Should check org_id too
    
    # 2. Call Gemini for Questions
    questions = await LLMService.generate_interview_questions(
        candidate_name=candidate.name,
        jd_text=job.description,
        resume_gaps=focus_areas # Or use focus_areas directly
    )
    
    # 3. Save kit
    kit = models.InterviewKit(
        job_id=job_id,
        candidate_id=candidate_id,
        focus_areas=focus_areas,
        difficulty=difficulty,
        questions=questions
    )
    db.add(kit)
    await db.commit()
    return kit

@router.post("/interviews/{kit_id}/scorecard")
async def submit_scorecard(
    kit_id: int,
    scores: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    # Logic to calculate total and get AI recommendation
    total = sum(scores.values()) / len(scores) if scores else 0
    rec = "Strong Hire" if total > 4 else "Hire" if total > 3 else "No Hire"
    
    scorecard = models.InterviewScorecard(
        kit_id=kit_id,
        recruiter_id=current_user.id,
        scores=scores,
        total_score=total,
        ai_recommendation=rec
    )
    db.add(scorecard)
    await db.commit()
    return scorecard

# ─── Comparison Mode ────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/compare")
async def compare_candidates(
    job_id: int, 
    candidate_ids: str, # "1,2,3"
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(ViewerOnly)
):
    ids = [int(i) for i in candidate_ids.split(",")]
    repo = CandidateRepository(db)
    candidates = []
    for cid in ids:
        c = await repo.get(cid)
        if c and c.org_id == request.state.org_id:
            candidates.append(c)
            
    # AI Summary
    summary = await LLMService.compare_candidates(
        jd="...", # Fetch job
        resume1=candidates[0].raw_text if len(candidates) > 0 else "",
        resume2=candidates[1].raw_text if len(candidates) > 1 else ""
    )
    
    return {"candidates": candidates, "ai_comparison": summary}

@router.post("/bulk-upload")
async def bulk_upload_resumes(file: UploadFile = File(...), job_id: int = Form(...), db: AsyncSession = Depends(get_db), current_user = Depends(RecruiterOnly)):
    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
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
async def evaluate_candidate_llm(candidate_id: int, job_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user = Depends(RecruiterOnly)):
    candidate = await CandidateRepository(db).get_by_id_org(candidate_id, current_user.org_id)
    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="Candidate or Job not found")
    from ..services.llm_service import LLMService
    evaluation = await LLMService.evaluate_candidate(job.description, candidate.raw_text)
    return {"evaluation": evaluation}

@router.post("/chat")
async def chat_candidates(query: str, request: Request, db: AsyncSession = Depends(get_db), current_user = Depends(ViewerOnly)):
    rag = RAGService(db)
    results = await rag.search_candidates(query, current_user.org_id)
    return {"results": results}

@router.get("/bias-report")
async def get_bias_report(job_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(ViewerOnly)):
    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    report = BiasDetector.detect_bias(job.description)
    return report

@router.get("/metrics")
async def get_metrics(request: Request, db: AsyncSession = Depends(get_db), current_user = Depends(ViewerOnly)):
    org_id = current_user.org_id
    stmt = select(models.Application).where(models.Application.org_id == org_id)
    res = await db.execute(stmt)
    results = res.scalars().all()
    
    if not results:
        return {"count": 0, "average_score": 0, "accept": 0, "review": 0, "reject": 0}
    
    scores = [r.score for r in results if r.score is not None]
    avg = sum(scores) / len(scores) if scores else 0
    accept = sum(1 for s in scores if s >= 70)
    review = sum(1 for s in scores if 40 <= s < 70)
    reject = sum(1 for s in scores if s < 40)
    
    return {
        "count": len(results),
        "average_score": round(avg, 2),
        "accept": accept,
        "review": review,
        "reject": reject
    }


# ─────────────────────────────────────────
# TASK STATUS POLLING
# ─────────────────────────────────────────

@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db), current_user = Depends(ViewerOnly)):
    """Poll status of a Celery task."""
    stmt = select(models.TaskRecord).where(
        models.TaskRecord.celery_task_id == task_id,
        models.TaskRecord.org_id == current_user.org_id
    )
    res = await db.execute(stmt)
    record = res.scalars().first()
    
    if not record:
        return {"status": "unknown"}

    return {
        "task_id": task_id,
        "status": record.status,
        "progress": record.progress,
        "result": record.result_json,
        "error": record.error,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
    }


# ─────────────────────────────────────────
# BATCH UPLOAD (ZIP)
# ─────────────────────────────────────────

@router.post("/batch/upload")
async def batch_upload(
    file: UploadFile = File(...),
    job_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    """Accept a ZIP of resumes + a job_id. Returns batch_id for polling."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only ZIP files accepted.")
    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
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
async def get_batch_results(batch_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(ViewerOnly)):
    """Get results for a completed batch job."""
    stmt = select(models.BatchJob).where(models.BatchJob.id == batch_id, models.BatchJob.org_id == current_user.org_id)
    batch = (await db.execute(stmt)).scalars().first()
    if not batch:
        raise HTTPException(404, "Batch job not found.")
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "total_files": batch.total_files,
        "completed_files": batch.completed_files,
        "progress_pct": round((batch.completed_files / batch.total_files) * 100, 1) if batch.total_files else 0,
        "results": batch.result_json or [],
    }


@router.get("/batch/{batch_id}/export")
async def export_batch_results(
    batch_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly),
):
    """Export batch results as CSV."""
    stmt = select(models.BatchJob).where(models.BatchJob.id == batch_id, models.BatchJob.org_id == current_user.org_id)
    batch = (await db.execute(stmt)).scalars().first()
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

