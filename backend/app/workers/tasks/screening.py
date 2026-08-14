"""
Celery Screening Task — Full ATSWorkflow Pipeline

Wires the modern ATSWorkflow (core/pipeline.py) into the Celery task.
Stores all breakdown fields to ScreeningResult, including XAI JSON,
matched/missing skills, and semantic score.

PDF byte storage strategy:
  - Upload route stores raw PDF bytes in Redis with 1h TTL keyed by task ID
  - Celery worker fetches bytes from Redis, runs ATSWorkflow, then cleans up
"""
import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

from celery.utils.log import get_task_logger
from sqlalchemy import select

from ..celery_app import celery_app, run_async
from ...db.database import AsyncSessionLocal
from ...models import models
from ...core.pipeline import ATSWorkflow
from ...core.logger import log
import redis

logger = get_task_logger(__name__)

# ─── Redis client for progress & PDF byte storage ─────────────────────────────
_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(_REDIS_URL)

_workflow = ATSWorkflow()


def update_task_progress(
    task_id: str,
    status: str,
    progress: int,
    step: str = "",
    error: Optional[str] = None,
) -> None:
    """Stores task state in Redis for SSE/polling tracking. TTL=1h."""
    data = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "current_step": step,
        "error": error,
        "timestamp": time.time(),
    }
    r.set(f"task_status:{task_id}", json.dumps(data), ex=3600)


def _fetch_pdf_bytes(task_id: str) -> Optional[bytes]:
    """Fetch raw PDF bytes from Redis. Returns None if expired or missing."""
    key = f"pdf_bytes:{task_id}"
    data = r.get(key)
    if data:
        r.delete(key)  # clean up after fetch
    return data


# ─── Main Screening Task ──────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.screening.screen_resume",
    bind=True,
    max_retries=3,
    rate_limit="10/m",
    acks_late=True,
)
def screen_resume(self, application_id: int):
    """
    Full ATSWorkflow pipeline for a single application.

    Steps:
      1. Fetch application, job, candidate from DB
      2. Retrieve PDF bytes from Redis (stored by upload route)
      3. Check Redis cache for duplicate JD-resume pair
      4. Run ATSWorkflow (parse → embed → score → bias → XAI → interview Qs)
      5. Persist full breakdown to ScreeningResult
      6. Update Application.score and status
    """
    task_id = self.request.id
    update_task_progress(task_id, "STARTED", 5, "Fetching application data")

    async def _run():
        async with AsyncSessionLocal() as db:
            # ── 1. Fetch entities ─────────────────────────────────────────────
            stmt = select(models.Application).where(models.Application.id == application_id)
            app = (await db.execute(stmt)).scalars().first()
            if not app:
                update_task_progress(task_id, "FAILED", 100, error="Application not found")
                return {"status": "error", "message": "Application not found"}

            stmt = select(models.JobPosting).where(models.JobPosting.id == app.job_id)
            job = (await db.execute(stmt)).scalars().first()
            if not job:
                update_task_progress(task_id, "FAILED", 100, error="Job not found")
                return {"status": "error", "message": "Job not found"}

            stmt = select(models.Candidate).where(models.Candidate.id == app.candidate_id)
            candidate = (await db.execute(stmt)).scalars().first()
            if not candidate:
                update_task_progress(task_id, "FAILED", 100, error="Candidate not found")
                return {"status": "error", "message": "Candidate not found"}

            update_task_progress(task_id, "PROCESSING", 15, "Checking cache")

            # ── 2. Retrieve PDF bytes from Redis ──────────────────────────────
            pdf_bytes = _fetch_pdf_bytes(task_id)
            # Fallback: re-encode raw_text if PDF bytes expired
            if pdf_bytes is None:
                logger.warning(f"PDF bytes not found in Redis for task {task_id}, using raw_text fallback")
                pdf_bytes = candidate.raw_text.encode("utf-8") if candidate.raw_text else b""
                filename = f"{candidate.name or 'resume'}.txt"
            else:
                filename = candidate.parsed_json.get("filename", f"{candidate.name or 'resume'}.pdf")

            # ── 3. Cache check (JD-resume pair deduplication) ─────────────────
            jd_text = job.description or ""
            resume_preview = (candidate.raw_text or "")[:1000]
            cache_raw = f"{jd_text[:500]}||{resume_preview}"
            cache_hash = hashlib.sha256(cache_raw.encode()).hexdigest()[:24]
            cache_key = f"scoring_result:{cache_hash}"

            cached = r.get(cache_key)
            if cached:
                logger.info(f"Cache HIT for application {application_id} (hash={cache_hash})")
                result = json.loads(cached)
                update_task_progress(task_id, "SUCCESS", 100, "Loaded from cache")
            else:
                update_task_progress(task_id, "PROCESSING", 30, "Parsing resume")

                # ── 4. Run full ATSWorkflow ──────────────────────────────────
                req_skills = job.required_skills
                if isinstance(req_skills, dict):
                    req_skills = list(req_skills.keys())
                elif not isinstance(req_skills, list):
                    req_skills = []

                update_task_progress(task_id, "PROCESSING", 45, "Generating embeddings")
                result = await _workflow.process(
                    file_content=pdf_bytes,
                    filename=filename,
                    jd_text=jd_text,
                    req_skills=req_skills,
                    min_exp=job.min_experience or 0,
                    org_id=app.org_id,
                )
                update_task_progress(task_id, "PROCESSING", 80, "Saving results")

                # Cache the result for 24h
                r.set(cache_key, json.dumps(result, default=str), ex=86400)

            # ── 5. Persist full breakdown to ScreeningResult ──────────────────
            breakdown = result.get("breakdown") or {}
            xai = breakdown.get("xai") or {}
            kw_detail = breakdown.get("keyword_detail") or {}

            # Update candidate parsed_json if pipeline re-parsed it
            if result.get("candidate") and result["candidate"].get("name"):
                parsed = result["candidate"]
                candidate.name = parsed.get("name") or candidate.name
                candidate.email = parsed.get("email") or candidate.email
                candidate.phone = parsed.get("phone") or candidate.phone
                candidate.raw_text = parsed.get("raw_text") or candidate.raw_text
                candidate.parsed_json = parsed

            screening = models.ScreeningResult(
                application_id=app.id,
                job_id=job.id,
                llm_model="gemini-1.5-flash",
                prompt_version="3.0",
                score=result.get("score") or 0.0,
                keyword_score=breakdown.get("keyword_score") or 0.0,
                semantic_score=breakdown.get("semantic_score"),
                skills_score=breakdown.get("keyword_score") or 0.0,
                experience_score=breakdown.get("experience_score") or 0.0,
                education_score=80.0,   # default — not separately computed
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
            db.add(screening)

            # Update Application score and status
            app.score = result.get("score") or 0.0
            app.status = "SCREENED"

            await db.commit()

            update_task_progress(task_id, "SUCCESS", 100, "Screening complete")
            logger.info(f"Screening complete: app={application_id} score={app.score:.1f}")

            return {
                "status": "success",
                "application_id": application_id,
                "score": app.score,
                "verdict": xai.get("verdict", "REVIEW"),
                "matched_skills": kw_detail.get("matched", []),
                "missing_skills": kw_detail.get("missing", []),
            }

    try:
        return run_async(_run())
    except Exception as exc:
        update_task_progress(task_id, "RETRYING", 50, error=str(exc))
        logger.error(f"Screening task failed (will retry): {exc}")
        # Exponential backoff: 60s, 120s, 240s
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


# ─── Batch Fan-out Task ───────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.screening.batch_screen_resumes")
def batch_screen_resumes(job_id: int):
    """
    Finds all unscreened applicants for a job and triggers individual screen_resume tasks.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            stmt = select(models.Application).where(
                models.Application.job_id == job_id,
                models.Application.status == "new",
            )
            apps = (await db.execute(stmt)).scalars().all()
            dispatched = 0
            for app in apps:
                screen_resume.delay(app.id)
                dispatched += 1
            return {"dispatched": dispatched, "job_id": job_id}

    return run_async(_run())
