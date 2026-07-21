"""
Celery notification tasks — email + in-app notifications.
"""
from celery.utils.log import get_task_logger
from ..celery_app import celery_app, run_async
from ...db.database import AsyncSessionLocal
from ...models import models
from sqlalchemy import select
from ...services.email_service import EmailService
from ...core.logger import log

logger = get_task_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.notifications.send_screening_result_email",
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=300,
)
def send_screening_result_email(self, application_id: int, score: float, verdict: str):
    """Send screening result email to candidate."""

    async def _run():
        async with AsyncSessionLocal() as db:
            app_stmt = (
                select(models.Application)
                .where(models.Application.id == application_id)
            )
            app = (await db.execute(app_stmt)).scalars().first()
            if not app:
                log.warning("send_email.app_not_found", application_id=application_id)
                return False

            cand_stmt = (
                select(models.Candidate)
                .where(models.Candidate.id == app.candidate_id)
            )
            candidate = (await db.execute(cand_stmt)).scalars().first()
            if not candidate:
                log.warning("send_email.candidate_not_found", candidate_id=app.candidate_id)
                return False

            job_stmt = (
                select(models.JobPosting)
                .where(models.JobPosting.id == app.job_id)
            )
            job = (await db.execute(job_stmt)).scalars().first()
            job_title = job.title if job else "the position"

            return EmailService.send_screening_result(
                to_email=candidate.email,
                candidate_name=candidate.name or "Candidate",
                job_title=job_title,
                score=score,
                verdict=verdict,
            )

    try:
        return run_async(_run())
    except Exception as exc:
        logger.error(f"Email task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.tasks.notifications.notify_recruiter_batch_complete",
    queue="notifications",
)
def notify_recruiter_batch_complete(job_id: int, stats: dict):
    """Notify job owner that a batch screening is finished."""

    async def _run():
        async with AsyncSessionLocal() as db:
            job_stmt = (
                select(models.JobPosting)
                .where(models.JobPosting.id == job_id)
            )
            job = (await db.execute(job_stmt)).scalars().first()
            if not job:
                return False

            user_stmt = (
                select(models.User)
                .where(models.User.org_id == job.org_id)
            )
            user = (await db.execute(user_stmt)).scalars().first()
            if not user or not user.email:
                return False

            return EmailService.send_screening_result(
                to_email=user.email,
                candidate_name="Recruiter",
                job_title=job.title,
                score=100.0,
                verdict="review",
                suggestions=[
                    f"Total resumes processed: {stats.get('total', 0)}",
                    f"Successful: {stats.get('successful', 0)}",
                    f"Failed: {stats.get('failed', 0)}",
                ],
            )

    return run_async(_run())


@celery_app.task(
    name="app.workers.tasks.notifications.create_in_app_notification",
    queue="notifications",
)
def create_in_app_notification(user_id: int, message: str):
    """Create an in-app notification record."""

    async def _run():
        async with AsyncSessionLocal() as db:
            notif = models.Notification(user_id=user_id, message=message)
            db.add(notif)
            await db.commit()
            return True

    return run_async(_run())
