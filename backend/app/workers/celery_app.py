import os
from celery import Celery
from celery.schedules import crontab
from ..core.config import settings

# ─── Celery Configuration ─────────────────────────────────────────────────────

# Broker: Redis (DB 0 for tasks)
# Backend: Redis (DB 1 for results)
# These can be customized in .env
broker_url = os.getenv("CELERY_BROKER_URL", settings.REDIS_URL)
backend_url = os.getenv("CELERY_RESULT_BACKEND", settings.REDIS_URL.replace("/0", "/1"))

celery_app = Celery(
    "ats_workers",
    broker=broker_url,
    backend=backend_url,
    include=[
        "app.workers.tasks.screening",
        "app.workers.tasks.notifications",
        "app.workers.tasks.analytics",
        "app.workers.tasks.batch"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    
    # ─── Multi-Queue Setup ────────────────────────────────────────────────────
    task_routes={
        "app.workers.tasks.screening.*": {"queue": "screening"},
        "app.workers.tasks.notifications.*": {"queue": "notifications"},
        "app.workers.tasks.analytics.*": {"queue": "analytics"},
    },
    
    # ─── Beat Scheduler Configuration ─────────────────────────────────────────
    beat_schedule={
        "hourly-job-analytics": {
            "task": "app.workers.tasks.analytics.compute_job_analytics_scheduled",
            "schedule": 3600.0, # Every 1 hour
        },
        "weekly-org-report": {
            "task": "app.workers.tasks.analytics.generate_weekly_report",
            "schedule": crontab(hour=9, minute=0, day_of_week="monday"), # Monday 9:00 AM
        },
    },
)

# ─── App Context Bridging ─────────────────────────────────────────────────────
# We use this to bridge sync Celery with async FastAPI database sessions
def run_async(func):
    import asyncio
    return asyncio.run(func)
