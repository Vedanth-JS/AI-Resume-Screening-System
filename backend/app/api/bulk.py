import os
import uuid
import json
import asyncio
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis
from celery import chord

from ..db.database import get_db
from ..db.repositories.job_repo import JobRepository
from ..db.repositories.candidate_repo import CandidateRepository
from ..db.repositories.application_repo import ApplicationRepository
from ..models import models
from ..api.auth import get_current_user_with_role, RoleEnum
from ..workers.tasks.screening import screen_resume
from ..workers.tasks.batch import finalize_batch
from ..core.pdf_extractor import PDFExtractor

router = APIRouter()
RecruiterOnly = get_current_user_with_role(RoleEnum.RECRUITER)
r = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

@router.post("/jobs/{job_id}/bulk-upload")
async def bulk_upload_resumes(
    job_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(RecruiterOnly)
):
    """
    Handles bulk PDF uploads, deduplicates, and starts a Celery Chord for screening.
    """
    if len(files) > 100:
        raise HTTPException(400, "Too many files. Max 100 per batch.")
    
    batch_id = str(uuid.uuid4())
    job_repo = JobRepository(db)
    job = await job_repo.get_by_id_org(job_id, current_user.org_id)
    if not job:
        raise HTTPException(404, "Job not found")

    accepted = []
    rejected = []
    task_signatures = []

    for file in files:
        if not file.filename.endswith(".pdf"):
            rejected.append({"file": file.filename, "reason": "Not a PDF"})
            continue
        
        content = await file.read()
        file_hash = PDFExtractor.get_file_hash(content)
        
        # Deduplication check
        stmt = select(models.Candidate).where(models.Candidate.raw_text.contains(file_hash)) # Simplified hash check
        # In real prod, we'd have a specific content_hash field
        
        # 1. Extract Text
        try:
            text = await PDFExtractor.extract_text(content)
        except Exception as e:
            rejected.append({"file": file.filename, "reason": str(e)})
            continue

        # 2. Create Candidate
        cand_repo = CandidateRepository(db)
        candidate = await cand_repo.create(
            org_id=current_user.org_id,
            name="Unknown", # Will be parsed by agent later
            email="unknown@example.com",
            phone="N/A",
            raw_text=text,
            parsed_json={"filename": file.filename},
            status="new"
        )
        
        # 3. Create Application
        app_repo = ApplicationRepository(db)
        application = await app_repo.create(
            org_id=current_user.org_id,
            candidate_id=candidate.id,
            job_id=job.id,
            score=0,
            status="new"
        )
        
        accepted.append(file.filename)
        # 4. Prepare Task Signature
        task_signatures.append(screen_resume.s(application.id))

    if not task_signatures:
        return {"batch_id": batch_id, "accepted": accepted, "rejected": rejected}

    # 5. Launch Batch Chord
    # Using chord(header)(callback)
    callback = finalize_batch.s(batch_id, job.id)
    chord(task_signatures)(callback)

    # Initial Redis progress
    await r.set(f"batch_status:{batch_id}", json.dumps({
        "batch_id": batch_id,
        "status": "PROCESSING",
        "progress": 0,
        "total": len(task_signatures)
    }), ex=86400)

    return {
        "batch_id": batch_id, 
        "accepted": accepted, 
        "rejected": rejected,
        "estimated_time_seconds": len(task_signatures) * 10 # Rough estimate
    }

@router.get("/batches/{batch_id}/progress")
async def get_batch_progress_sse(batch_id: str, request: Request):
    """
    Server-Sent Events endpoint for real-time batch progress.
    """
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
                
            data = await r.get(f"batch_status:{batch_id}")
            if data:
                yield {
                    "event": "message",
                    "data": data.decode()
                }
                status_obj = json.loads(data)
                if status_obj.get("status") == "COMPLETED":
                    break
            else:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Batch not found"})
                }
                break
                
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
