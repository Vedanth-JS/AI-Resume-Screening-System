import redis
import json
import os
from celery.utils.log import get_task_logger
from ..celery_app import celery_app
from .notifications import notify_recruiter_batch_complete

logger = get_task_logger(__name__)
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

@celery_app.task(name="app.workers.tasks.batch.finalize_batch")
def finalize_batch(results, batch_id: str, job_id: int):
    """
    Chord callback task triggered when all tasks in a batch complete.
    Aggregates stats and notifies the recruiter.
    """
    logger.info(f"Finalizing batch {batch_id} for job {job_id}")
    
    total = len(results)
    successful = sum(1 for r in results if r.get("status") != "error")
    failed = total - successful
    
    # Update Redis batch progress to 100%
    data = {
        "batch_id": batch_id,
        "status": "COMPLETED",
        "progress": 100,
        "total": total,
        "successful": successful,
        "failed": failed
    }
    r.set(f"batch_status:{batch_id}", json.dumps(data), ex=86400) # Keep for 24h
    
    # Notify Recruiter
    stats = {"total": total, "successful": successful, "failed": failed}
    notify_recruiter_batch_complete.delay(job_id, stats)
    
    return data
