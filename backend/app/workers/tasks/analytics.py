from celery.utils.log import get_task_logger
from ..celery_app import celery_app, run_async
from ...db.database import AsyncSessionLocal
from ...models import models
from sqlalchemy import select, func
from ...api.analytics import job_analytics

logger = get_task_logger(__name__)

@celery_app.task(name="app.workers.tasks.analytics.compute_job_analytics_scheduled", queue="analytics")
def compute_job_analytics_scheduled():
    """
    Periodic task to refresh analytics for all active jobs.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            stmt = select(models.JobPosting).where(models.JobPosting.status == "active")
            jobs = (await db.execute(stmt)).scalars().all()
            for job in jobs:
                # This could populate a cache or summary table
                logger.info(f"Computing analytics for job {job.id}")
                # await refresh_job_cache(job.id, db)
            return len(jobs)

    return run_async(_run())

@celery_app.task(name="app.workers.tasks.analytics.generate_weekly_report", queue="analytics")
def generate_weekly_report(org_id: int = None):
    """
    Periodic task (Mondays 9 AM) to email weekly recruitment summary to organizations.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            # logic to aggregate weekly metrics (new candidates, screenings, hires)
            # send_weekly_email(...)
            logger.info(f"Generating weekly report for org {org_id}")
            return True

    return run_async(_run())
