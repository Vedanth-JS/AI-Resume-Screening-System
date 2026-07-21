"""
ATS Core Routes — Jobs, Candidates, Screening, Interviews, Analytics, Chat.
All endpoints are async, properly validated, and org-scoped.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db.database import get_db
from ..db.repositories.job_repo import JobRepository
from ..db.repositories.candidate_repo import CandidateRepository
from ..db.repositories.application_repo import ApplicationRepository
from ..models import models
from ..schemas import schemas
from ..core.pipeline import ATSWorkflow
from ..embeddings.search import SemanticSearch
from ..core.auth_dependencies import ViewerOnly, RecruiterOnly, AdminOnly, get_current_user
from ..services.feedback_service import FeedbackService
from ..services.rag_service import RAGService
from ..services.llm_service import LLMService
from ..core.bias_detector import BiasDetector
from ..workers.tasks.screening import screen_resume
from ..core.logger import log
from typing import List, Optional
import zipfile
import io
import csv

router = APIRouter()
workflow = ATSWorkflow()


# ═══════════════════════════════════════════════════════════════════════════════
# JOBS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/jobs", response_model=schemas.JobResponse)
async def create_job(
    job: schemas.JobCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    repo = JobRepository(db)
    new_job = await repo.create(
        org_id=request.state.org_id,
        title=job.title,
        description=job.description,
        required_skills=job.required_skills,
        min_experience=job.min_experience,
        status="active",
    )
    return new_job


@router.get("/jobs", response_model=List[schemas.JobResponse])
async def list_jobs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    repo = JobRepository(db)
    return await repo.list_by_org(request.state.org_id)


@router.get("/jobs/{job_id}", response_model=schemas.JobResponse)
async def get_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    repo = JobRepository(db)
    job = await repo.get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ═══════════════════════════════════════════════════════════════════════════════
# CANDIDATES & SCREENING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/resume/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    job_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    # Validate environment configuration
    if not settings.GOOGLE_API_KEY:
        log.error("upload_resume.missing_api_key")
        raise HTTPException(
            500, 
            "Server configuration error: AI processing service not available. Please contact administrator."
        )

    job_repo = JobRepository(db)
    job = await job_repo.get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Validate file size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File size exceeds 10MB limit")

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")

    try:
        result = await workflow.process(
            content,
            file.filename,
            job.description,
            job.required_skills,
            job.min_experience,
            request.state.org_id,
        )

        # Check if parsing failed
        if result.get("error"):
            raise HTTPException(422, f"Failed to process resume: {result['error']}")

        if not result.get("candidate") or not result["candidate"].get("raw_text"):
            raise HTTPException(
                422, 
                "Failed to extract text from PDF. The file may be corrupt, scanned without OCR, or password-protected."
            )

        cand_repo = CandidateRepository(db)
        candidate = await cand_repo.create(
            org_id=request.state.org_id,
            name=result["candidate"]["name"],
            email=result["candidate"]["email"],
            phone=result["candidate"]["phone"],
            raw_text=result["candidate"]["raw_text"],
            parsed_json=result["candidate"],
            status="new",
        )

        app_repo = ApplicationRepository(db)
        application = await app_repo.create(
            org_id=request.state.org_id,
            candidate_id=candidate.id,
            job_id=job.id,
            score=result["score"],
            status="SCREENED",
        )

        rag = RAGService(db)
        await rag.index_candidate(candidate)

        return {
            "success": True,
            "message": "Resume processed successfully",
            "application_id": application.id,
            "analysis": result
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error("upload_resume.error", filename=file.filename, error=str(e), exc_info=True)
        raise HTTPException(
            500,
            f"Failed to process resume: {str(e)}. Please try again or contact support if the issue persists."
        )


@router.get("/candidates", response_model=List[schemas.CandidateResponse])
async def list_candidates(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    repo = CandidateRepository(db)
    return await repo.list_by_org(request.state.org_id)


@router.get("/candidates/{candidate_id}", response_model=schemas.CandidateResponse)
async def get_candidate(
    candidate_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    repo = CandidateRepository(db)
    candidate = await repo.get(candidate_id, org_id=request.state.org_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    return candidate


@router.post("/applications/{application_id}/feedback")
async def get_candidate_feedback(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    stmt = select(models.Application).where(models.Application.id == application_id)
    app = (await db.execute(stmt)).scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")

    candidate = await CandidateRepository(db).get(app.candidate_id)
    screening_stmt = select(models.ScreeningResult).where(
        models.ScreeningResult.application_id == app.id
    )
    screening = (await db.execute(screening_stmt)).scalars().first()

    feedback = await FeedbackService.generate_candidate_feedback(
        candidate.raw_text,
        {
            "overall_score": app.score,
            "reasoning": screening.reasoning if screening else "",
        },
    )
    return feedback


@router.post("/jobs/{job_id}/match-candidates")
async def match_candidates_for_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    job = await JobRepository(db).get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(404, "Job not found")

    search_service = SemanticSearch(db)
    matches = await search_service.find_matches_for_job(
        job_id=job.id,
        job_description=job.description,
        org_id=request.state.org_id,
    )
    return {"matches_found": len(matches), "candidates": matches}


# ═══════════════════════════════════════════════════════════════════════════════
# BULK UPLOAD (ZIP)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/bulk-upload")
async def bulk_upload_resumes(
    file: UploadFile = File(...),
    job_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files allowed")

    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
    if not job:
        raise HTTPException(404, "Job not found")

    from ..core.pdf_extractor import PDFExtractor
    from ..workers.tasks.screening import screen_resume

    content = await file.read()
    results = []
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        for filename in z.namelist():
            if not filename.lower().endswith((".pdf", ".txt")):
                continue
            with z.open(filename) as f:
                file_bytes = f.read()
                try:
                    if filename.lower().endswith(".pdf"):
                        text = await PDFExtractor.extract_text(file_bytes)
                    else:
                        text = file_bytes.decode("utf-8", errors="ignore")
                except Exception as e:
                    log.error("bulk_upload.extract_failed", filename=filename, error=str(e))
                    continue

                cand_repo = CandidateRepository(db)
                candidate = await cand_repo.create(
                    org_id=current_user.org_id,
                    name="Unknown",
                    email="unknown@example.com",
                    phone="N/A",
                    raw_text=text,
                    parsed_json={"filename": filename},
                    status="new",
                )

                app_repo = ApplicationRepository(db)
                application = await app_repo.create(
                    org_id=current_user.org_id,
                    candidate_id=candidate.id,
                    job_id=job.id,
                    score=0,
                    status="new",
                )

                screen_resume.delay(application.id)
                results.append(filename)

    return {"message": f"Queued {len(results)} resumes", "files": results}


# ═══════════════════════════════════════════════════════════════════════════════
# AI / ANALYTICS / CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/llm/evaluate")
async def evaluate_candidate_llm(
    candidate_id: int,
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    candidate = await CandidateRepository(db).get(candidate_id, org_id=current_user.org_id)
    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
    if not candidate or not job:
        raise HTTPException(404, "Candidate or Job not found")
    evaluation = await LLMService.evaluate_candidate(job.description, candidate.raw_text)
    return {"evaluation": evaluation}


@router.post("/chat")
async def chat_candidates(
    query: str = Query(..., min_length=1, max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    # Validate environment configuration
    if not settings.GOOGLE_API_KEY:
        log.error("chat_candidates.missing_api_key")
        raise HTTPException(
            500,
            "Server configuration error: AI search service not available. Please contact administrator."
        )

    if not query or not query.strip():
        raise HTTPException(400, "Query cannot be empty")

    try:
        rag = RAGService(db)
        results = await rag.search_candidates(query, current_user.org_id)
        
        return {
            "success": True,
            "results": results,
            "query": query,
            "count": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error("chat_candidates.error", query=query, error=str(e), exc_info=True)
        raise HTTPException(
            500,
            f"Failed to search candidates: {str(e)}. Please try again or contact support if the issue persists."
        )


@router.get("/bias-report")
async def get_bias_report(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    job = await JobRepository(db).get_by_id_org(job_id, current_user.org_id)
    if not job:
        raise HTTPException(404, "Job not found")
    report = BiasDetector.detect_bias(job.description)
    return report


@router.get("/metrics")
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
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
        "reject": reject,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TASK STATUS POLLING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    stmt = select(models.TaskRecord).where(
        models.TaskRecord.celery_task_id == task_id,
        models.TaskRecord.org_id == current_user.org_id,
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


# ═══════════════════════════════════════════════════════════════════════════════
# INTERVIEW KITS (non-duplicate routes only — /interviews paths kept in interviews.py)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/interviews/{kit_id}/scorecard")
async def submit_scorecard(
    kit_id: int,
    scores: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    total = sum(scores.values()) / len(scores) if scores else 0
    rec = "Strong Hire" if total > 4 else "Hire" if total > 3 else "No Hire"

    scorecard = models.InterviewScorecard(
        kit_id=kit_id,
        recruiter_id=current_user.id,
        scores=scores,
        total_score=total,
        ai_recommendation=rec,
    )
    db.add(scorecard)
    await db.commit()
    return scorecard
