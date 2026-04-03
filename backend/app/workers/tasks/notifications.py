from celery.utils.log import get_task_logger
from ..celery_app import celery_app, run_async
from ...db.database import AsyncSessionLocal
from ...models import models
from sqlalchemy import select
from ...services.email_service import EmailService

logger = get_task_logger(__name__)

@celery_app.task(name="app.workers.tasks.notifications.send_status_email", bind=True, queue="notifications")
def send_status_email(self, application_id: int, status: str):
    """
    Sends application status update email to candidate.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            stmt = select(models.Application).where(models.Application.id == application_id)
            app = (await db.execute(stmt)).scalars().first()
            if not app: return False
            
            stmt = select(models.Candidate).where(models.Candidate.id == app.candidate_id)
            candidate = (await db.execute(stmt)).scalars().first()
            
            email_service = EmailService()
            await email_service.send_status_update(candidate.email, candidate.name, status)
            return True

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300) # Retry after 5m

@celery_app.task(name="app.workers.tasks.notifications.notify_recruiter_batch_complete", queue="notifications")
def notify_recruiter_batch_complete(job_id: int, stats: dict):
    """
    Notifies the job owner that a batch of screenings is finished.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            stmt = select(models.JobPosting).where(models.JobPosting.id == job_id)
            job = (await db.execute(stmt)).scalars().first()
            if not job: return False
            
            # Fetch recruiter/owner email from models.User 
            stmt = select(models.User).where(models.User.org_id == job.org_id) # Simplify for now
            user = (await db.execute(stmt)).scalars().first()
            
            email_service = EmailService()
            await email_service.send_batch_report(user.email, job.title, stats)
            return True

    return run_async(_run())
