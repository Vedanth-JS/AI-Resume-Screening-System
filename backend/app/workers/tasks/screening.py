import json
import time
import os
from celery.utils.log import get_task_logger
from ..celery_app import celery_app, run_async
from ...db.database import AsyncSessionLocal
from ...models import models
from ...agents.orchestrator import ScreeningOrchestrator
from sqlalchemy import select
import redis

logger = get_task_logger(__name__)
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

def update_task_progress(task_id, status, progress, step="", error=None):
    """Stores task state in Redis for SSE tracking."""
    data = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "current_step": step,
        "error": error,
        "timestamp": time.time()
    }
    r.set(f"task_status:{task_id}", json.dumps(data), ex=3600)

@celery_app.task(name="app.workers.tasks.screening.screen_resume", bind=True, rate_limit='10/m', max_retries=3)
def screen_resume(self, application_id: int):
    """
    Full agent pipeline for a single application.
    """
    task_id = self.request.id
    update_task_progress(task_id, "STARTED", 10, "Fetching application data")
    
    async def _run():
        async with AsyncSessionLocal() as db:
            # 1. Fetch Application & Job
            stmt = select(models.Application).where(models.Application.id == application_id)
            res = await db.execute(stmt)
            app = res.scalars().first()
            if not app:
                update_task_progress(task_id, "FAILED", 100, error="Application not found")
                return {"status": "error", "message": "App not found"}
            
            stmt = select(models.JobPosting).where(models.JobPosting.id == app.job_id)
            res = await db.execute(stmt)
            job = res.scalars().first()
            
            # 2. Fetch Candidate
            stmt = select(models.Candidate).where(models.Candidate.id == app.candidate_id)
            res = await db.execute(stmt)
            candidate = res.scalars().first()
            
            update_task_progress(task_id, "PROCESSING", 30, "Running AI agents")
            
            orchestrator = ScreeningOrchestrator(db)
            job_data = {
                "id": job.id,
                "description": job.description,
                "required_skills": job.required_skills,
                "min_experience": job.min_experience
            }
            
            # Re-reading content if needed or using raw_text
            # For simplicity, we assume we use candidate.raw_text or we'd need the original bytes
            # If the user wants the "full pipeline", we might need the original PDF bytes
            # But the orchestrator usually takes bytes or text. 
            # Let's assume text for this background task if bytes aren't passed.
            
            result = await orchestrator.run_pipeline(candidate.raw_text.encode(), job.id, job_data)
            
            update_task_progress(task_id, "SUCCESS", 100, "Screening complete")
            return result

    try:
        return run_async(_run())
    except Exception as exc:
        update_task_progress(task_id, "RETRYING", 50, error=str(exc))
        logger.error(f"Screening failed: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(name="app.workers.tasks.screening.batch_screen_resumes")
def batch_screen_resumes(job_id: int):
    """
    Finds all unscreened applicants for a job and triggers individual tasks.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            stmt = select(models.Application).where(
                models.Application.job_id == job_id,
                models.Application.status == "new"
            )
            apps = (await db.execute(stmt)).scalars().all()
            for app in apps:
                screen_resume.delay(app.id)
            return len(apps)

    return run_async(_run())
