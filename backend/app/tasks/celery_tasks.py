"""
Celery tasks with:
 - max_retries=3, exponential backoff
 - TaskRecord DB writes (status: pending → running → completed/failed)
 - AnalyticsEvent logging on completion
"""
import asyncio
import time
from datetime import datetime
from celery import Celery
from celery.utils.log import get_task_logger
from ..core.config import settings
from ..core.pipeline import ATSWorkflow
from ..db.database import SessionLocal
from ..db import crud
from ..models import models

logger = get_task_logger(__name__)

celery_app = Celery(
    "ats_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,                    # only ack after completion
    worker_prefetch_multiplier=1,           # one task at a time per worker
)

workflow = ATSWorkflow()


def _update_task_record(db, celery_task_id: str, **kwargs):
    """Helper — update TaskRecord row."""
    record = db.query(models.TaskRecord).filter(
        models.TaskRecord.celery_task_id == celery_task_id
    ).first()
    if record:
        for k, v in kwargs.items():
            setattr(record, k, v)
        db.commit()


def _log_event(db, event_type: str, payload: dict):
    """Append to analytics_events."""
    event = models.AnalyticsEvent(event_type=event_type, payload_json=payload)
    db.add(event)
    db.commit()


# ─── Single-resume task ────────────────────────────────────────────────────────

@celery_app.task(
    name="process_resume_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,          # base delay (seconds); doubles each retry
    acks_late=True,
)
def process_resume_task(
    self,
    job_id: int,
    filename: str,
    file_content: bytes,
    job_description: str,
    req_skills: list,
    min_exp: int,
    task_record_id: int = None,
):
    db = SessionLocal()
    try:
        # Mark as running
        if task_record_id:
            _update_task_record(db, self.request.id, status="running")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            workflow.process(file_content, filename, job_description, req_skills, min_exp)
        )

        pr = result.get("candidate", {})
        b  = result.get("ats_breakdown", {})

        candidate = crud.create_candidate(
            db,
            name=pr.get("name", "Unknown"),
            email=pr.get("email") or "unknown@resume.com",
            phone=pr.get("phone"),
            raw_text=pr.get("raw_text", ""),
            parsed_json=pr,
        )

        score_status = "accept" if (result.get("final_result", {}).get("final_score", 0) >= 70) else \
                       "review"  if (result.get("final_result", {}).get("final_score", 0) >= 40) else "reject"

        screening = models.ScreeningResult(
            candidate_id         = candidate.id,
            job_id               = job_id,
            ats_score            = result.get("final_result", {}).get("final_score", 0),
            llm_score            = 0.0,
            final_score          = result.get("final_result", {}).get("final_score", 0),
            keyword_score        = b.get("keyword_score", 0),
            semantic_score       = b.get("semantic_score", 0),
            format_score         = b.get("format_score", 0),
            section_score        = b.get("section_score", 0),
            interview_questions  = result.get("interview_questions", []),
            jd_profile           = result.get("jd_profile"),
            processing_time_ms   = result.get("processing_time_ms", 0),
            explanation          = result.get("final_result", {}).get("explanation", ""),
            status               = score_status,
        )
        db.add(screening)
        db.commit()

        # ChromaDB indexing (best-effort)
        try:
            from ..core.chatbot import CandidateChatbot
            CandidateChatbot.add_candidate(
                candidate.id,
                pr.get("raw_text", ""),
                {"name": candidate.name, "email": candidate.email, "job_id": job_id}
            )
        except Exception as ce:
            logger.warning(f"ChromaDB index failed: {ce}")

        payload = {
            "candidate_id": candidate.id,
            "job_id":       job_id,
            "final_score":  result.get("final_result", {}).get("final_score", 0),
            "filename":     filename,
        }
        _log_event(db, "resume_screened", payload)

        if task_record_id:
            _update_task_record(
                db, self.request.id,
                status="completed",
                result_json=payload,
                progress=100,
                completed_at=datetime.utcnow(),
            )

        return {"status": "success", "candidate_id": candidate.id, "score": payload["final_score"]}

    except Exception as exc:
        logger.error(f"Resume task failed: {exc}")
        if task_record_id:
            try:
                _update_task_record(
                    db, self.request.id,
                    status="failed",
                    error=str(exc),
                    completed_at=datetime.utcnow(),
                )
            except Exception:
                pass
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


# ─── Batch processing task ────────────────────────────────────────────────────

@celery_app.task(
    name="process_batch_task",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def process_batch_task(
    self,
    batch_job_id: int,
    job_id: int,
    filenames: list,
    file_contents: list,   # List[bytes]
    job_description: str,
    req_skills: list,
    min_exp: int,
):
    db = SessionLocal()
    try:
        batch = db.query(models.BatchJob).filter(models.BatchJob.id == batch_job_id).first()
        if batch:
            batch.status = "processing"
            db.commit()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        results = []
        for i, (fname, fcontent) in enumerate(zip(filenames, file_contents)):
            try:
                r = loop.run_until_complete(
                    workflow.process(
                        bytes(fcontent) if isinstance(fcontent, list) else fcontent,
                        fname, job_description, req_skills, min_exp
                    )
                )
                pr  = r.get("candidate", {})
                fr  = r.get("final_result", {})
                b   = r.get("ats_breakdown", {})

                candidate = crud.create_candidate(
                    db,
                    name=pr.get("name", "Unknown"),
                    email=pr.get("email") or f"unknown{i}@resume.com",
                    phone=pr.get("phone"),
                    raw_text=pr.get("raw_text", ""),
                    parsed_json=pr,
                )
                score_status = "accept" if fr.get("final_score", 0) >= 70 else \
                               "review"  if fr.get("final_score", 0) >= 40 else "reject"

                screening = models.ScreeningResult(
                    candidate_id=candidate.id, job_id=job_id,
                    ats_score=fr.get("final_score", 0), llm_score=0.0,
                    final_score=fr.get("final_score", 0),
                    keyword_score=b.get("keyword_score", 0),
                    semantic_score=b.get("semantic_score", 0),
                    format_score=b.get("format_score", 0),
                    section_score=b.get("section_score", 0),
                    interview_questions=r.get("interview_questions", []),
                    jd_profile=r.get("jd_profile"),
                    processing_time_ms=r.get("processing_time_ms", 0),
                    explanation=fr.get("explanation", ""),
                    status=score_status,
                )
                db.add(screening)
                db.commit()

                results.append({
                    "filename":     fname,
                    "candidate_id": candidate.id,
                    "name":         candidate.name,
                    "email":        candidate.email,
                    "final_score":  fr.get("final_score", 0),
                    "verdict":      score_status,
                    "keyword_score":  b.get("keyword_score", 0),
                    "semantic_score": b.get("semantic_score", 0),
                })

                if batch:
                    batch.completed_files = i + 1
                    db.commit()

            except Exception as file_exc:
                logger.error(f"Batch sub-file error [{fname}]: {file_exc}")
                results.append({"filename": fname, "error": str(file_exc), "final_score": 0})

        # Sort by score desc
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        if batch:
            batch.status = "completed"
            batch.result_json = results
            batch.completed_at = datetime.utcnow()
            db.commit()

        _log_event(db, "batch_completed", {"batch_id": batch_job_id, "count": len(results)})
        return {"status": "success", "results": results}

    except Exception as exc:
        logger.error(f"Batch task failed: {exc}")
        if batch:
            try:
                batch.status = "failed"
                db.commit()
            except Exception:
                pass
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))
    finally:
        db.close()
