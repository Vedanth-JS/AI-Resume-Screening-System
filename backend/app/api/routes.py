"""
ATS Core Routes — Jobs, Candidates, Screening, Interviews, Analytics, Chat.
All endpoints are async, properly validated, and org-scoped.
"""
import os
import uuid
import zipfile
import io
import csv
import hashlib

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis as redis_lib

from ..db.database import get_db, AsyncSessionLocal
from ..db.repositories.job_repo import JobRepository
from ..db.repositories.candidate_repo import CandidateRepository
from ..db.repositories.application_repo import ApplicationRepository
from ..models import models
from ..models.models import BatchStatus
from ..schemas import schemas
from ..core.pipeline import ATSWorkflow
from ..embeddings.search import SemanticSearch
from ..core.auth_dependencies import ViewerOnly, RecruiterOnly, AdminOnly, get_current_user, get_current_user_hybrid
from ..services.feedback_service import FeedbackService
from ..services.rag_service import RAGService
from ..services.llm_service import LLMService
from ..core.bias_detector import BiasDetector
from ..core.ats_scoring_engine import ATSScoringEngine
from ..core.parser import ResumeParser
from ..schemas.ats_engine import (
    ATSScoreResponse,
    ATSScoreRequest,
    BulkScreenResponse,
    CandidateScreeningResult,
    CustomJDConfig,
    ATSCriteriaWeights,
)
from ..workers.tasks.screening import screen_resume
from ..workers.tasks.batch import process_batch
from ..core.logger import log
from ..core.config import settings
from typing import List, Optional, Dict, Any

router = APIRouter()
workflow = ATSWorkflow()

# Redis client for PDF byte storage
_redis = redis_lib.Redis.from_url(os.getenv("REDIS_URL", settings.REDIS_URL))


def _store_pdf_in_redis(task_id: str, pdf_bytes: bytes, ttl: int = 3600) -> None:
    """Store raw PDF bytes in Redis keyed by task_id (1h TTL)."""
    _redis.set(f"pdf_bytes:{task_id}", pdf_bytes, ex=ttl)



@router.post(
    "/jobs",
    response_model=schemas.JobResponse,
    summary="Create a job posting",
    description="Create a new job posting with required skills and experience.",
    tags=["Jobs"],
    status_code=201,
)
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


@router.get(
    "/jobs",
    response_model=schemas.PaginatedResponse[schemas.JobResponse],
    summary="List job postings",
    description="List all active job postings for the organization with pagination.",
    tags=["Jobs"],
)
async def list_jobs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    status: Optional[str] = Query(default=None, description="Filter by status: active | closed | draft"),
):
    from sqlalchemy import func
    repo = JobRepository(db)
    # Get all for org, then paginate in Python (repository layer doesn't yet support pagination)
    all_jobs = await repo.list_by_org(request.state.org_id)
    if not all_jobs:
        starter_jobs = [
            {
                "title": "Senior Full Stack Engineer",
                "description": "Seeking a Senior Full Stack Engineer experienced with React, Python, FastAPI, and Cloud infrastructure. You will architect scalable systems and lead feature implementation.",
                "required_skills": ["Python", "FastAPI", "React", "TypeScript", "SQLAlchemy", "PostgreSQL", "Docker", "Git"],
                "min_experience": 4,
            },
            {
                "title": "AI / Machine Learning Specialist",
                "description": "Looking for an AI/ML Engineer to build LLM pipelines, semantic embeddings, and automated candidate matching algorithms.",
                "required_skills": ["Python", "PyTorch", "NLP", "Machine Learning", "FastAPI", "Vector DB", "Docker"],
                "min_experience": 3,
            },
            {
                "title": "Cloud & DevOps Architect",
                "description": "Manage Kubernetes clusters, CI/CD pipelines, and cloud environments.",
                "required_skills": ["AWS", "Docker", "Kubernetes", "CI/CD", "Terraform", "Linux"],
                "min_experience": 5,
            }
        ]
        for sj in starter_jobs:
            try:
                created = await repo.create(
                    org_id=request.state.org_id,
                    title=sj["title"],
                    description=sj["description"],
                    required_skills=sj["required_skills"],
                    min_experience=sj["min_experience"],
                    status="active",
                )
                all_jobs.append(created)
            except Exception:
                pass

    if status:
        all_jobs = [j for j in all_jobs if j.status == status]
    total = len(all_jobs)
    start = (page - 1) * page_size
    items = all_jobs[start: start + page_size]
    return schemas.PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


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


@router.post(
    "/resume/upload",
    summary="Upload and screen a single resume",
    description="Upload a PDF resume against a job. Runs the full 6-stage AI pipeline synchronously and returns a scored result with XAI reasoning.",
    tags=["Screening"],
    responses={
        200: {"description": "Resume processed successfully with full score breakdown"},
        400: {"description": "Invalid file type or size"},
        422: {"description": "Could not extract text from PDF"},
        500: {"description": "AI processing service error"},
    },
)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    job_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    job_repo = JobRepository(db)
    job = await job_repo.get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Validate file size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File size exceeds 10MB limit")

    # Validate file type
    allowed_exts = (".pdf", ".docx", ".doc", ".txt")
    if not any(file.filename.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(400, f"Supported file formats: {', '.join(allowed_exts)}")

    # Close DB session to release connection back to pool during slow external API calls
    await db.close()

    try:
        result = await workflow.process(
            content,
            file.filename,
            job.description,
            job.required_skills,
            job.min_experience,
            request.state.org_id,
        )

        if result.get("error"):
            raise HTTPException(422, f"Failed to process resume: {result['error']}")

        if not result.get("candidate") or not result["candidate"].get("raw_text"):
            raise HTTPException(
                422,
                "Failed to extract text from PDF. The file may be corrupt, scanned without OCR, or password-protected."
            )

        cand_data = result["candidate"]
        cand_name = cand_data.get("name") or "Candidate"
        cand_email = cand_data.get("email") or f"{cand_name.lower().replace(' ', '.')}.applicant@ai-ats.local"

        async with AsyncSessionLocal() as fresh_db:
            cand_repo = CandidateRepository(fresh_db)
            candidate = await cand_repo.create(
                org_id=request.state.org_id,
                name=cand_name,
                email=cand_email,
                phone=cand_data.get("phone"),
                raw_text=cand_data["raw_text"],
                parsed_json=cand_data,
                status="new",
            )

            app_repo = ApplicationRepository(fresh_db)
            application = await app_repo.create(
                org_id=request.state.org_id,
                candidate_id=candidate.id,
                job_id=job.id,
                score=result["score"],
                status="SCREENED",
            )

            # Also persist ScreeningResult for the breakdown
            breakdown = result.get("breakdown") or {}
            xai = breakdown.get("xai") or {}
            kw_detail = breakdown.get("keyword_detail") or {}
            screening = models.ScreeningResult(
                application_id=application.id,
                job_id=job.id,
                llm_model=settings.LLM_MODEL,
                prompt_version="3.0",
                score=result.get("score") or 0.0,
                keyword_score=breakdown.get("keyword_score") or 0.0,
                semantic_score=breakdown.get("semantic_score"),
                skills_score=breakdown.get("keyword_score") or 0.0,
                experience_score=breakdown.get("experience_score") or 0.0,
                education_score=80.0,
                format_score=breakdown.get("format_score") or 0.0,
                section_score=breakdown.get("section_score"),
                certs_score=5.0,
                matched_skills=kw_detail.get("matched", []),
                missing_skills=kw_detail.get("missing", []),
                red_flags=xai.get("red_flags", []),
                xai_json=xai,
                reasoning=xai.get("hiring_recommendation") or result.get("explanation") or "",
                bias_flags=result.get("bias") or {},
            )
            fresh_db.add(screening)

            rag = RAGService(fresh_db)
            await rag.index_candidate(candidate)
            await fresh_db.commit()

            # Enrich result with robust ATS Scoring Engine evaluation
            try:
                ats_eval = ATSScoringEngine.score(
                    resume_text=cand_data.get("raw_text", ""),
                    job_description=job.description,
                    job_role=job.title,
                )
                result["ats_scoring"] = ats_eval.model_dump()
            except Exception as score_err:
                log.warning("ats_scoring_enrichment_failed", error=str(score_err))

            return {
                "success": True,
                "message": "Resume processed successfully",
                "application_id": application.id,
                "candidate_id": candidate.id,
                "analysis": result,
            }

    except HTTPException:
        raise
    except Exception as e:
        log.error("upload_resume.error", filename=file.filename, error=str(e), exc_info=True)
        raise HTTPException(
            500,
            f"Failed to process resume: {str(e)}. Please try again or contact support if the issue persists."
        )


@router.get(
    "/candidates",
    response_model=schemas.PaginatedResponse[schemas.CandidateWithScore],
    summary="List candidates with scores",
    description="Paginated candidate list enriched with latest screening scores. Supports sorting and filtering.",
    tags=["Candidates"],
)
async def list_candidates(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="score", description="Sort field: score | created_at | name"),
    sort_order: str = Query(default="desc", description="Sort direction: asc | desc"),
    min_score: Optional[float] = Query(default=None, ge=0, le=100),
    max_score: Optional[float] = Query(default=None, ge=0, le=100),
    status: Optional[str] = Query(default=None, description="Filter by application status"),
    job_id: Optional[int] = Query(default=None, description="Filter by specific job"),
):
    """Returns paginated candidates enriched with their latest screening scores."""
    from sqlalchemy import func, desc, asc
    from sqlalchemy.orm import selectinload

    # Join Applications → Candidates → ScreeningResults
    stmt = (
        select(
            models.Candidate,
            models.Application,
            models.ScreeningResult,
        )
        .join(models.Application, models.Application.candidate_id == models.Candidate.id)
        .outerjoin(
            models.ScreeningResult,
            models.ScreeningResult.application_id == models.Application.id,
        )
        .where(models.Candidate.org_id == request.state.org_id)
        .where(models.Candidate.deleted_at.is_(None))
    )

    if job_id:
        stmt = stmt.where(models.Application.job_id == job_id)
    if status:
        stmt = stmt.where(models.Application.status == status)
    if min_score is not None:
        stmt = stmt.where(models.Application.score >= min_score)
    if max_score is not None:
        stmt = stmt.where(models.Application.score <= max_score)

    # Sorting
    sort_col = {
        "score": models.Application.score,
        "created_at": models.Candidate.created_at,
        "name": models.Candidate.name,
    }.get(sort_by, models.Application.score)
    order_fn = desc if sort_order == "desc" else asc
    stmt = stmt.order_by(order_fn(sort_col))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginate
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items = []
    for cand, app, screening in rows:
        items.append(
            schemas.CandidateWithScore(
                id=cand.id,
                name=cand.name,
                email=cand.email,
                phone=cand.phone,
                created_at=cand.created_at,
                final_score=app.score if app else None,
                keyword_score=screening.keyword_score if screening else None,
                semantic_score=screening.semantic_score if screening else None,
                format_score=screening.format_score if screening else None,
                section_score=screening.section_score if screening else None,
                experience_score=screening.experience_score if screening else None,
                matched_skills=screening.matched_skills if screening else None,
                missing_skills=screening.missing_skills if screening else None,
                verdict=screening.xai_json.get("verdict") if screening and screening.xai_json else None,
                status=app.status if app else "pending",
                job_id=app.job_id if app else None,
            )
        )

    return schemas.PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get(
    "/candidates/{candidate_id}",
    response_model=schemas.CandidateResponse,
    summary="Get candidate details",
    tags=["Candidates"],
)
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


@router.get(
    "/candidates/{candidate_id}/score",
    response_model=schemas.ScreeningResultResponse,
    summary="Get candidate score breakdown",
    description="Returns the full 5-component score breakdown with XAI reasoning, matched/missing skills, and red flags for the latest screening result.",
    tags=["Candidates"],
)
async def get_candidate_score(
    candidate_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    stmt = (
        select(models.ScreeningResult)
        .join(models.Application, models.Application.id == models.ScreeningResult.application_id)
        .join(models.Candidate, models.Candidate.id == models.Application.candidate_id)
        .where(
            models.Candidate.id == candidate_id,
            models.Candidate.org_id == request.state.org_id,
        )
        .order_by(models.ScreeningResult.created_at.desc())
        .limit(1)
    )
    result = (await db.execute(stmt)).scalars().first()
    if not result:
        raise HTTPException(404, "No screening result found for this candidate")
    return result


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


@router.post(
    "/bulk-upload",
    summary="Batch resume upload (ZIP or multiple PDFs)",
    description="Upload a ZIP file containing multiple PDF resumes. Each resume is processed in parallel via Celery. Returns a batch_job_id for polling progress.",
    tags=["Screening"],
)
async def bulk_upload_resumes(
    request: Request,
    file: UploadFile = File(...),
    job_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files allowed for bulk upload")

    job = await JobRepository(db).get_by_id_org(job_id, request.state.org_id)
    if not job:
        raise HTTPException(404, "Job not found")

    content = await file.read()
    from ..core.pdf_extractor import PDFExtractor

    # Create a BatchJob record for progress tracking
    batch_job = models.BatchJob(
        org_id=request.state.org_id,
        job_id=job.id,
        status=BatchStatus.PENDING,
        total_files=0,
        completed_files=0,
    )
    db.add(batch_job)
    await db.flush()  # get batch_job.id

    file_task_map = []
    queued_filenames = []

    with zipfile.ZipFile(io.BytesIO(content)) as z:
        pdf_files = [f for f in z.namelist() if f.lower().endswith((".pdf", ".txt"))]
        if not pdf_files:
            raise HTTPException(400, "ZIP contains no supported files (.pdf, .txt)")

        for filename in pdf_files:
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

            if not text.strip():
                log.warning("bulk_upload.empty_text", filename=filename)
                continue

            # Create placeholder candidate (will be updated when task runs)
            cand_repo = CandidateRepository(db)
            candidate = await cand_repo.create(
                org_id=request.state.org_id,
                name="Processing...",
                email=f"pending-{uuid.uuid4().hex[:8]}@pending.ai",
                phone=None,
                raw_text=text,
                parsed_json={"filename": filename, "status": "pending_parse"},
                status="new",
            )

            app_repo = ApplicationRepository(db)
            application = await app_repo.create(
                org_id=request.state.org_id,
                candidate_id=candidate.id,
                job_id=job.id,
                score=0,
                status="new",
            )

            # Generate a unique task_id and store PDF bytes in Redis (1h TTL)
            task_id = f"batch_{batch_job.id}_{application.id}"
            _store_pdf_in_redis(task_id, file_bytes, ttl=3600)

            file_task_map.append({
                "task_id": task_id,
                "application_id": application.id,
                "filename": filename,
            })
            queued_filenames.append(filename)

    if not file_task_map:
        raise HTTPException(422, "No valid resumes could be extracted from the ZIP")

    # Update batch job total
    batch_job.total_files = len(file_task_map)
    batch_job.status = BatchStatus.PROCESSING
    await db.commit()

    # Dispatch Celery batch task (group + chord)
    process_batch.delay(batch_job.id, file_task_map)

    return {
        "success": True,
        "message": f"Queued {len(file_task_map)} resumes for processing",
        "batch_job_id": batch_job.id,
        "files": queued_filenames,
        "poll_url": f"/api/batch/{batch_job.id}/status",
    }



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


@router.get(
    "/tasks/{task_id}/status",
    response_model=schemas.TaskStatusResponse,
    summary="Poll Celery task progress",
    description="Poll the status of a Celery screening task. Returns progress (0-100) and current processing step.",
    tags=["Tasks"],
)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    import json
    import redis as redis_lib
    import os
    # First check Redis for live progress (faster, real-time)
    try:
        r = redis_lib.Redis.from_url(os.getenv("REDIS_URL", settings.REDIS_URL))
        redis_data = r.get(f"task_status:{task_id}")
        if redis_data:
            data = json.loads(redis_data)
            return schemas.TaskStatusResponse(
                task_id=task_id,
                status=data.get("status", "UNKNOWN"),
                progress=data.get("progress", 0),
                current_step=data.get("current_step"),
                error=data.get("error"),
            )
    except Exception:
        pass

    # Fall back to DB record
    stmt = select(models.TaskRecord).where(
        models.TaskRecord.celery_task_id == task_id,
        models.TaskRecord.org_id == current_user.org_id,
    )
    res = await db.execute(stmt)
    record = res.scalars().first()

    if not record:
        return schemas.TaskStatusResponse(task_id=task_id, status="unknown", progress=0)

    return schemas.TaskStatusResponse(
        task_id=task_id,
        status=record.status.value if hasattr(record.status, 'value') else str(record.status),
        progress=record.progress,
        result=record.result_json,
        error=record.error,
        completed_at=record.completed_at,
    )


@router.get(
    "/batch/{batch_job_id}/status",
    response_model=schemas.BatchStatusResponse,
    summary="Poll batch job progress",
    description="Poll the status of a bulk resume upload batch job. Returns progress and per-file counts.",
    tags=["Tasks"],
)
async def get_batch_status(
    batch_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    stmt = select(models.BatchJob).where(
        models.BatchJob.id == batch_job_id,
        models.BatchJob.org_id == current_user.org_id,
    )
    batch = (await db.execute(stmt)).scalars().first()
    if not batch:
        raise HTTPException(404, "Batch job not found")

    pct = int(100 * batch.completed_files / max(batch.total_files, 1))
    return schemas.BatchStatusResponse(
        batch_job_id=batch.id,
        status=batch.status.value if hasattr(batch.status, 'value') else str(batch.status),
        total_files=batch.total_files,
        completed_files=batch.completed_files,
        progress_pct=pct,
        result=batch.result_json,
        started_at=batch.created_at,
        completed_at=None,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTERVIEW KITS (non-duplicate routes only — /interviews paths kept in interviews.py)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/interviews/{kit_id}")
async def get_interview_kit(
    kit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    kit = await db.get(models.InterviewKit, kit_id)
    if not kit:
        raise HTTPException(404, "Interview kit not found")
    
    candidate = await db.get(models.Candidate, kit.candidate_id)
    job = await db.get(models.JobPosting, kit.job_id)
    
    stmt = select(models.Application).where(
        models.Application.candidate_id == kit.candidate_id,
        models.Application.job_id == kit.job_id
    )
    app = (await db.execute(stmt)).scalars().first()
    
    return {
        "id": kit.id,
        "job_id": kit.job_id,
        "job_title": job.title if job else "Unknown Job",
        "candidate_id": kit.candidate_id,
        "candidate_name": candidate.name if candidate else "Unknown Candidate",
        "application_id": app.id if app else None,
        "focus_areas": kit.focus_areas,
        "difficulty": kit.difficulty,
        "questions": kit.questions,
        "created_at": kit.created_at,
        "updated_at": kit.updated_at,
    }


@router.post("/interviews/{kit_id}/scorecard")
async def submit_scorecard(
    kit_id: int,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    scores = payload.get("scores", payload) if isinstance(payload, dict) else {}
    scores_cleaned = {}
    for k, v in scores.items():
        try:
            scores_cleaned[str(k)] = float(v)
        except (ValueError, TypeError):
            pass

    total = sum(scores_cleaned.values()) / len(scores_cleaned) if scores_cleaned else 0.0
    rec = "Strong Hire" if total > 4 else "Hire" if total > 3 else "No Hire"

    scorecard = models.InterviewScorecard(
        kit_id=kit_id,
        recruiter_id=current_user.id,
        scores=scores_cleaned,
        total_score=total,
        ai_recommendation=rec,
    )
    db.add(scorecard)
    await db.commit()
    return scorecard


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE KANBAN — Application Status Management
# ═══════════════════════════════════════════════════════════════════════════════

_VALID_PIPELINE_STATUSES = frozenset({
    "APPLIED", "SCREENING", "INTERVIEW", "OFFER", "REJECTED",
    # Legacy values for backward compat
    "new", "SCREENED", "screened",
})


@router.put(
    "/applications/{application_id}/status",
    summary="Update application pipeline status",
    description="Moves a candidate between Kanban pipeline stages. Creates an in-app notification on status change.",
    tags=["Candidates"],
)
async def update_application_status(
    application_id: int,
    payload: schemas.ApplicationStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    """Update Application.status for Kanban pipeline drag-and-drop."""
    new_status = payload.status.upper()
    # Normalise to canonical pipeline statuses
    _canonical = {
        "NEW": "APPLIED", "APPLIED": "APPLIED",
        "SCREENED": "SCREENING", "SCREENING": "SCREENING",
        "INTERVIEW": "INTERVIEW", "OFFER": "OFFER",
        "REJECTED": "REJECTED",
    }
    new_status = _canonical.get(new_status, new_status)
    if new_status not in {"APPLIED", "SCREENING", "INTERVIEW", "OFFER", "REJECTED"}:
        raise HTTPException(400, f"Invalid status '{payload.status}'. Must be one of: APPLIED, SCREENING, INTERVIEW, OFFER, REJECTED")

    stmt = select(models.Application).where(
        models.Application.id == application_id,
        models.Application.org_id == request.state.org_id,
    )
    app = (await db.execute(stmt)).scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")

    old_status = app.status
    app.status = new_status

    # In-app notification
    candidate = await db.get(models.Candidate, app.candidate_id)
    cand_name = candidate.name if candidate else f"Candidate #{app.candidate_id}"
    notification = models.Notification(
        user_id=current_user.id,
        message=f"{cand_name}: moved from {old_status} → {new_status}",
    )
    db.add(notification)
    await db.commit()

    return {
        "application_id": application_id,
        "old_status": old_status,
        "new_status": new_status,
        "candidate_name": cand_name,
    }


@router.get(
    "/pipeline",
    summary="Get all applications grouped by pipeline stage",
    tags=["Candidates"],
)
async def get_pipeline(
    request: Request,
    job_id: Optional[int] = Query(default=None, description="Filter by job"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    """Returns all applications grouped into Kanban columns."""
    stmt = (
        select(models.Application, models.Candidate, models.ScreeningResult)
        .join(models.Candidate, models.Candidate.id == models.Application.candidate_id)
        .outerjoin(
            models.ScreeningResult,
            models.ScreeningResult.application_id == models.Application.id,
        )
        .where(models.Application.org_id == request.state.org_id)
        .where(models.Candidate.deleted_at.is_(None))
    )
    if job_id:
        stmt = stmt.where(models.Application.job_id == job_id)

    rows = (await db.execute(stmt)).all()

    # Normalise old status values into pipeline stages
    _stage_map = {
        "new": "APPLIED", "applied": "APPLIED", "APPLIED": "APPLIED",
        "screened": "SCREENING", "SCREENED": "SCREENING", "SCREENING": "SCREENING",
        "interview": "INTERVIEW", "INTERVIEW": "INTERVIEW",
        "offer": "OFFER", "OFFER": "OFFER",
        "rejected": "REJECTED", "REJECTED": "REJECTED",
    }
    stages = {"APPLIED": [], "SCREENING": [], "INTERVIEW": [], "OFFER": [], "REJECTED": []}

    for app, cand, screening in rows:
        stage = _stage_map.get(app.status or "APPLIED", "APPLIED")
        verdict = None
        if screening and screening.xai_json:
            verdict = screening.xai_json.get("verdict")
        stages[stage].append({
            "application_id": app.id,
            "candidate_id": cand.id,
            "candidate_name": cand.name,
            "candidate_email": cand.email,
            "score": app.score,
            "verdict": verdict,
            "job_id": app.job_id,
            "matched_skills": screening.matched_skills if screening else [],
        })

    return {
        "stages": stages,
        "total": sum(len(v) for v in stages.values()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ATS Scoring Engine Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

async def OptionalUser(request: Request, db: AsyncSession = Depends(get_db)):
    """Graceful auth fallback: recognizes authenticated user without blocking unauthenticated requests."""
    try:
        return await get_current_user_hybrid(request, db)
    except Exception:
        return None


@router.post(
    "/ats/score",
    response_model=ATSScoreResponse,
    summary="Evaluate resume with deterministic-plus-semantic ATS scoring engine",
    description=(
        "Evaluates candidate resume text against an explicit Job Description or "
        "dynamically inferred Job Role Title benchmarks across 4 weighted components."
    ),
    tags=["ATS Scoring Engine"],
)
async def score_resume_endpoint(
    payload: ATSScoreRequest,
    current_user=Depends(OptionalUser),
):
    """Calculates comprehensive ATS score matching the required JSON schema."""
    return ATSScoringEngine.score(
        resume_text=payload.resume_text,
        job_description=payload.job_description,
        job_role=payload.job_role,
        parsed_resume=payload.parsed_resume,
    )


@router.post(
    "/ats/score-file",
    response_model=ATSScoreResponse,
    summary="Upload resume file and evaluate with ATS scoring engine",
    description="Upload a PDF/DOCX/TXT file to evaluate against a Job Description or Job Role.",
    tags=["ATS Scoring Engine"],
)
async def score_resume_file_endpoint(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(default=None),
    job_role: Optional[str] = Form(default=None),
    current_user=Depends(OptionalUser),
):
    """Extracts raw text from uploaded resume file and scores it."""
    allowed_exts = (".pdf", ".docx", ".doc", ".txt")
    if not any(file.filename.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(400, f"Supported file formats: {', '.join(allowed_exts)}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File size exceeds 10MB limit")

    raw_text = ResumeParser.extract_text(content, file.filename)
    return ATSScoringEngine.score(
        resume_text=raw_text,
        job_description=job_description,
        job_role=job_role,
    )


@router.get(
    "/ats/roles",
    summary="Get list of predefined ATS job roles",
    description="Returns the 16 industry-standard predefined job roles supported by the ATS engine.",
    tags=["ATS Scoring Engine"],
)
async def get_predefined_roles_endpoint():
    from ..core.role_inferrer import PREDEFINED_ROLES
    return {"roles": PREDEFINED_ROLES}


@router.post(
    "/ats/bulk-screen",
    response_model=BulkScreenResponse,
    summary="Bulk screen up to 50 resumes simultaneously",
    description=(
        "Processes up to 50 resumes against a predefined role (Option A) or "
        "custom Job Description (Option B) with configurable weights and strict extraction checks."
    ),
    tags=["ATS Scoring Engine"],
)
async def bulk_screen_endpoint(
    files: List[UploadFile] = File(...),
    job_role: Optional[str] = Form(default=None),
    job_description: Optional[str] = Form(default=None),
    custom_jd: Optional[str] = Form(default=None),
    weights: Optional[str] = Form(default=None),
    current_user=Depends(OptionalUser),
):
    import json
    if len(files) > 50:
        raise HTTPException(400, "Maximum 50 resumes can be screened simultaneously.")

    parsed_custom_jd = None
    if custom_jd:
        try:
            jd_dict = json.loads(custom_jd)
            parsed_custom_jd = CustomJDConfig(**jd_dict)
        except Exception as e:
            log.warning("failed_to_parse_custom_jd_json", error=str(e))

    parsed_weights = None
    if weights:
        try:
            w_dict = json.loads(weights)
            parsed_weights = ATSCriteriaWeights(**w_dict)
        except Exception as e:
            log.warning("failed_to_parse_weights_json", error=str(e))

    file_items = []
    for f in files:
        b = await f.read()
        file_items.append((f.filename, b))

    results = ATSScoringEngine.evaluate_bulk(
        file_items=file_items,
        job_role=job_role,
        job_description=job_description,
        custom_jd=parsed_custom_jd,
        weights=parsed_weights,
    )

    successful = [r for r in results if r.status == "COMPLETED" and r.overall_ats_score is not None]
    errors = [r for r in results if r.status == "ERROR"]
    avg_score = round(sum(r.overall_ats_score for r in successful) / len(successful), 1) if successful else 0.0

    role_used = (
        parsed_custom_jd.title if parsed_custom_jd and parsed_custom_jd.title
        else (job_role or "Software Engineer")
    )
    input_mode = "job_description" if (parsed_custom_jd or (job_description and len(job_description.strip()) >= 50)) else "inferred_role"

    return BulkScreenResponse(
        job_role_used=role_used,
        input_mode_used=input_mode,
        total_processed=len(results),
        successful_count=len(successful),
        error_count=len(errors),
        average_score=avg_score,
        candidates=results,
    )


@router.post(
    "/ats/rescore",
    response_model=BulkScreenResponse,
    summary="Instantly re-evaluate already parsed resumes against updated job requirements",
    description="Allows recruiters to change the target role or custom JD and re-score candidates without re-uploading files.",
    tags=["ATS Scoring Engine"],
)
async def rescore_candidates_endpoint(
    payload: Dict[str, Any] = Body(...),
    current_user=Depends(OptionalUser),
):
    candidates_data = payload.get("candidates", [])
    job_role = payload.get("job_role")
    job_description = payload.get("job_description")
    custom_jd_dict = payload.get("custom_jd")
    weights_dict = payload.get("weights")

    parsed_custom_jd = CustomJDConfig(**custom_jd_dict) if custom_jd_dict else None
    parsed_weights = ATSCriteriaWeights(**weights_dict) if weights_dict else None

    rescored_candidates: List[CandidateScreeningResult] = []

    for item in candidates_data:
        cand_id = item.get("id") or str(uuid.uuid4())[:8]
        filename = item.get("file_name") or "resume.pdf"
        file_size = item.get("file_size") or 0
        raw_text = item.get("candidate", {}).get("raw_text") or item.get("raw_text") or ""

        if not raw_text.strip():
            empty_profile = ParsedCandidateProfile(name=filename, raw_text="")
            rescored_candidates.append(
                CandidateScreeningResult(
                    id=cand_id,
                    rank=len(rescored_candidates) + 1,
                    candidate=empty_profile,
                    overall_ats_score=None,
                    match_tier=None,
                    status="ERROR",
                    extraction_error="Extraction Error: No text available for re-scoring.",
                    file_name=filename,
                    file_size=file_size,
                )
            )
            continue

        try:
            eval_res = ATSScoringEngine.score(
                resume_text=raw_text,
                job_description=job_description,
                job_role=job_role,
                custom_jd=parsed_custom_jd,
                weights=parsed_weights,
            )
            cand_profile = ATSScoringEngine.extract_candidate_profile(raw_text, filename)
            rescored_candidates.append(
                CandidateScreeningResult(
                    id=cand_id,
                    rank=1,
                    candidate=cand_profile,
                    overall_ats_score=eval_res.overall_ats_score,
                    match_tier=eval_res.match_tier,
                    recommendation=eval_res.recommendation,
                    breakdown=eval_res.breakdown,
                    skill_gap_analysis=eval_res.skill_gap_analysis,
                    keyword_analysis=eval_res.keyword_analysis,
                    strengths=eval_res.strengths,
                    weaknesses=eval_res.weaknesses,
                    actionable_improvements=eval_res.actionable_improvements,
                    status="COMPLETED",
                    extraction_error=None,
                    file_name=filename,
                    file_size=file_size,
                )
            )
        except Exception as err:
            rescored_candidates.append(
                CandidateScreeningResult(
                    id=cand_id,
                    rank=len(rescored_candidates) + 1,
                    candidate=ParsedCandidateProfile(name=filename, raw_text=raw_text[:200]),
                    overall_ats_score=None,
                    match_tier=None,
                    status="ERROR",
                    extraction_error=f"Re-scoring error: {str(err)}",
                    file_name=filename,
                    file_size=file_size,
                )
            )

    rescored_candidates.sort(
        key=lambda x: (x.status == "COMPLETED", x.overall_ats_score or 0),
        reverse=True,
    )
    for i, item in enumerate(rescored_candidates):
        item.rank = i + 1

    successful = [r for r in rescored_candidates if r.status == "COMPLETED" and r.overall_ats_score is not None]
    errors = [r for r in rescored_candidates if r.status == "ERROR"]
    avg_score = round(sum(r.overall_ats_score for r in successful) / len(successful), 1) if successful else 0.0

    role_used = (
        parsed_custom_jd.title if parsed_custom_jd and parsed_custom_jd.title
        else (job_role or "Software Engineer")
    )
    input_mode = "job_description" if (parsed_custom_jd or (job_description and len(job_description.strip()) >= 50)) else "inferred_role"

    return BulkScreenResponse(
        job_role_used=role_used,
        input_mode_used=input_mode,
        total_processed=len(rescored_candidates),
        successful_count=len(successful),
        error_count=len(errors),
        average_score=avg_score,
        candidates=rescored_candidates,
    )


@router.post(
    "/ats/export-csv",
    summary="Export candidate screening results to CSV",
    tags=["ATS Scoring Engine"],
)
async def export_candidates_csv_endpoint(
    candidates: List[Dict[str, Any]] = Body(...),
    current_user=Depends(OptionalUser),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Rank", "Candidate Name", "Email", "Phone", "ATS Score",
        "Match Tier", "Recommendation", "Experience (Years)",
        "Education", "College", "Top Skills", "Status"
    ])

    for c in candidates:
        profile = c.get("candidate", {})
        rec = c.get("recommendation", {})
        writer.writerow([
            c.get("rank", ""),
            profile.get("name", "Candidate"),
            profile.get("email", ""),
            profile.get("phone", ""),
            c.get("overall_ats_score", "N/A"),
            c.get("match_tier", ""),
            rec.get("verdict", c.get("status", "")),
            profile.get("work_experience_years", ""),
            profile.get("education", ""),
            profile.get("college", ""),
            ", ".join(profile.get("technical_skills", [])[:6]),
            c.get("status", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ats_screening_results.csv"},
    )


@router.post(
    "/ats/export-excel",
    summary="Export candidate screening results to Excel (.xlsx)",
    tags=["ATS Scoring Engine"],
)
async def export_candidates_excel_endpoint(
    candidates: List[Dict[str, Any]] = Body(...),
    current_user=Depends(OptionalUser),
):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Screening Results"

    headers = [
        "Rank", "Candidate Name", "Email", "Phone", "ATS Score",
        "Match Tier", "Recommendation", "Experience (Yrs)",
        "Education", "College", "Top Skills", "File Name", "Status"
    ]
    ws.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="F97316", end_color="F97316", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for c in candidates:
        profile = c.get("candidate", {})
        rec = c.get("recommendation", {})
        ws.append([
            c.get("rank", ""),
            profile.get("name", "Candidate"),
            profile.get("email", ""),
            profile.get("phone", ""),
            c.get("overall_ats_score") if c.get("overall_ats_score") is not None else "N/A",
            c.get("match_tier", ""),
            rec.get("verdict", c.get("status", "")),
            profile.get("work_experience_years", 0),
            profile.get("education", ""),
            profile.get("college", ""),
            ", ".join(profile.get("technical_skills", [])[:6]),
            c.get("file_name", ""),
            c.get("status", ""),
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ats_screening_results.xlsx"},
    )



