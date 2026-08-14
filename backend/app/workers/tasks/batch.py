"""
Batch Resume Processing — Celery Group + Chord Pattern

Strategy:
  1. Bulk upload route stores each PDF in Redis (keyed by task_id, 1h TTL)
  2. This task creates a BatchJob DB record for progress tracking
  3. Uses Celery group (parallel fan-out) to dispatch one screen_resume per file
  4. A chord callback updates BatchJob.status → COMPLETED on completion
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

from celery import group, chord
from celery.utils.log import get_task_logger
from sqlalchemy import select

from ..celery_app import celery_app, run_async
from ...db.database import AsyncSessionLocal
from ...models import models
from ...models.models import BatchStatus
from .screening import screen_resume, update_task_progress

logger = get_task_logger(__name__)


# ─── Batch Orchestration ──────────────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.batch.process_batch", bind=True, max_retries=1)
def process_batch(self, batch_job_id: int, file_task_map: List[Dict[str, Any]]):
    """
    Orchestrates parallel screening of a batch of resumes.

    Args:
        batch_job_id: ID of BatchJob record to update
        file_task_map: List of {"task_id": str, "application_id": int, "filename": str}
    """
    async def _prepare():
        async with AsyncSessionLocal() as db:
            stmt = select(models.BatchJob).where(models.BatchJob.id == batch_job_id)
            batch = (await db.execute(stmt)).scalars().first()
            if not batch:
                return None
            batch.status = BatchStatus.PROCESSING
            batch.total_files = len(file_task_map)
            batch.completed_files = 0
            await db.commit()
            return True

    run_async(_prepare())

    # Dispatch parallel screening tasks
    task_signatures = [
        screen_resume.s(item["application_id"])
        for item in file_task_map
    ]

    # Chord: fan-out all screening tasks, then run callback on completion
    job = chord(
        group(task_signatures),
        batch_complete_callback.s(batch_job_id=batch_job_id),
    )
    job.delay()
    logger.info(f"Batch {batch_job_id}: dispatched {len(task_signatures)} screening tasks")

    return {"batch_job_id": batch_job_id, "dispatched": len(task_signatures)}


@celery_app.task(name="app.workers.tasks.batch.batch_complete_callback")
def batch_complete_callback(results: List[Any], batch_job_id: int):
    """
    Chord callback — runs after all screening tasks complete.
    Aggregates results and marks BatchJob as COMPLETED.
    """
    async def _finalize():
        async with AsyncSessionLocal() as db:
            stmt = select(models.BatchJob).where(models.BatchJob.id == batch_job_id)
            batch = (await db.execute(stmt)).scalars().first()
            if not batch:
                return

            successful = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
            failed = [r for r in results if not isinstance(r, dict) or r.get("status") != "success"]

            batch.status = BatchStatus.COMPLETED
            batch.completed_files = len(successful)
            batch.result_json = {
                "total": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "average_score": (
                    sum(r.get("score", 0) for r in successful) / len(successful)
                    if successful else 0
                ),
            }
            await db.commit()
            logger.info(
                f"Batch {batch_job_id} complete: {len(successful)}/{len(results)} succeeded"
            )

    run_async(_finalize())
    return {"batch_job_id": batch_job_id, "completed": len(results)}


@celery_app.task(name="app.workers.tasks.batch.finalize_batch")
def finalize_batch(results: List[Any], batch_id: str, job_id: int):
    """
    Chord callback for bulk uploads in api/bulk.py.
    Aggregates screening results and updates Redis with progress.
    """
    import redis
    import os

    successful = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
    failed = [r for r in results if not isinstance(r, dict) or r.get("status") != "success"]

    r_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

    status_data = {
        "batch_id": batch_id,
        "status": "COMPLETED",
        "progress": 100,
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
    }
    r_client.set(f"batch_status:{batch_id}", json.dumps(status_data), ex=86400)

    logger.info(f"Finalized batch {batch_id} for job {job_id}: {len(successful)} success, {len(failed)} failed")
    return {"batch_id": batch_id, "status": "completed"}


@celery_app.task(name="app.workers.tasks.batch.update_batch_progress")
def update_batch_progress(batch_job_id: int):
    """Poll-based progress updater: counts SCREENED applications for a batch job."""
    async def _count():
        async with AsyncSessionLocal() as db:
            stmt = select(models.BatchJob).where(models.BatchJob.id == batch_job_id)
            batch = (await db.execute(stmt)).scalars().first()
            if not batch:
                return {}

            # Count how many apps in this batch are SCREENED
            app_stmt = select(models.Application).where(
                models.Application.job_id == batch.job_id,
                models.Application.org_id == batch.org_id,
                models.Application.status == "SCREENED",
            )
            screened = (await db.execute(app_stmt)).scalars().all()
            batch.completed_files = len(screened)
            await db.commit()

            pct = int(100 * len(screened) / max(batch.total_files, 1))
            return {
                "batch_job_id": batch_job_id,
                "progress": pct,
                "completed": len(screened),
                "total": batch.total_files,
                "status": batch.status.value,
            }

    return run_async(_count())
