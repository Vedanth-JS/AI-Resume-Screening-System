"""
Celery workers for background screening and batch processing.
Uses asyncio.run() to bridge sync Celery with async AI pipeline.
"""
import asyncio
import time
from datetime import datetime, timezone
from celery import Celery
from celery.utils.log import get_task_logger
from ..core.config import settings
from ..core.pipeline import ATSWorkflow
from ..db.database import AsyncSessionLocal
from ..models import models
from sqlalchemy import select

logger = get_task_logger(__name__)

celery_app = Celery("ats_tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
)

workflow = ATSWorkflow()

async def _get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ─── Tasks ──────────────────────────────────────────────────────────────────

from ..agents.orchestrator import ScreeningOrchestrator
from ..embeddings.pipeline import EmbeddingPipeline
from ..scoring.ats_scorer import ATSScorer
from ..bias.detector import BiasDetector
import hashlib
import json

@celery_app.task(name="screen_resume_task", bind=True, max_retries=3)
def screen_resume_task(self, org_id: int, job_id: int, filename: str, file_content: bytes):
    """
    Task to screen a single resume using the multi-agent pipeline.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            # 1. Fetch Job
            stmt = select(models.JobPosting).where(models.JobPosting.id == job_id, models.JobPosting.org_id == org_id)
            res = await db.execute(stmt)
            job = res.scalars().first()
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # 2. Run Multi-Agent Pipeline
            logger.info(f"Screening {filename} for Org {org_id}")
            orchestrator = ScreeningOrchestrator(db)
            job_data = {
                "id": job.id,
                "description": job.description,
                "required_skills": job.required_skills,
                "min_experience": job.min_experience
            }
            result = await orchestrator.run_pipeline(file_content, job_id, job_data)
            
            # 3. Create Candidate & Application
            parser = result["parser"]
            candidate = models.Candidate(
                org_id=org_id,
                name=parser["name"],
                email=parser["email"],
                phone=parser["phone"],
                raw_text=parser.get("raw_text", ""),
                parsed_json=parser,
                status="processed"
            )
            db.add(candidate)
            await db.flush()
            
            # 4. Generate & Store Embeddings (RAG Pipeline)
            embedder = EmbeddingPipeline(db)
            await embedder.embed_candidate(candidate.id, parser.get("raw_text", ""))
            
            # 5. Production ATS Scoring (NLTK-based)
            ats_scorer = ATSScorer()
            ats_res = ats_scorer.score(parser, job_data)
            
            # 6. Bias Audit
            bias_detector = BiasDetector()
            bias_audit = bias_detector.run_bias_audit(parser.get("raw_text", ""), parser["name"])
            
            # 7. Save Application & Intermediate Agent Results
            score_data = result["score"]
            application = models.Application(
                org_id=org_id,
                candidate_id=candidate.id,
                job_id=job.id,
                score=ats_res["total_score"], # Use production score for ranking
                status="SCREENED"
            )
            db.add(application)
            await db.flush()
            
            screening = models.ScreeningResult(
                application_id=application.id,
                job_id=job.id,
                llm_model=settings.LLM_MODEL,
                prompt_version="2.1-prod-scoring",
                score=ats_res["total_score"],
                
                # Granular Scores
                keyword_score=ats_res["component_scores"]["keyword_match"],
                skills_score=ats_res["component_scores"]["skills_coverage"],
                experience_score=ats_res["component_scores"]["experience_relevance"],
                education_score=ats_res["component_scores"]["education_match"],
                format_score=ats_res["component_scores"]["format_quality"],
                certs_score=ats_res["component_scores"]["certifications"],
                
                reasoning=score_data["reasoning"],
                bias_flags=bias_audit["flags"]
            )
            db.add(screening)
            
            # 8. Immutable Audit Trail
            input_hash = hashlib.sha256(file_content).hexdigest()
            audit_log = models.AuditLog(
                user_id=1, # System/Admin user placeholder
                action="RESUME_SCREENED",
                entity_type="APPLICATION",
                entity_id=application.id,
                model_version="ats-v2.1",
                input_hash=input_hash,
                output_json=ats_res,
                bias_flags=bias_audit
            )
            db.add(audit_log)
            
            await db.commit()
            return {
                "status": "success", 
                "score": ats_res["total_score"], 
                "application_id": application.id,
                "bias_risk": bias_audit["risk_level"]
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(name="batch_process_task", bind=True)
def batch_process_task(self, org_id: int, job_id: int, files: list):
    """
    Task to handle a batch of resumes.
    Eventually this could be a Chord of individual tasks.
    """
    # Simple loop for now, in production use groups/chords
    # ... logic similar to single screen ...
    return {"status": "queued", "count": len(files)}
