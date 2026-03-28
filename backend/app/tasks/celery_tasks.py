from celery import Celery
import os
import asyncio
from ..core.pipeline import ATSWorkflow
from ..db.database import SessionLocal
from ..db import crud
from ..models import models
from ..core.chatbot import CandidateChatbot
import logging

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

workflow = ATSWorkflow()

@celery_app.task(name="process_resume_task")
def process_resume_task(
    job_id: int, 
    filename: str, 
    file_content: bytes, 
    job_description: str, 
    req_skills: list, 
    min_exp: int
):
    loop = asyncio.get_event_loop()
    db = SessionLocal()
    try:
        # Process through multi-agent pipeline
        result = loop.run_until_complete(workflow.process(
            file_content, filename, job_description, req_skills, min_exp
        ))
        
        # Save results to DB
        candidate = crud.create_candidate(
            db, 
            name=result["candidate"]["name"],
            email=result["candidate"]["email"],
            phone=result["candidate"]["phone"],
            raw_text=result["candidate"]["raw_text"],
            parsed_json=result["candidate"]
        )
        
        crud.create_screening_result(
            db,
            candidate_id=candidate.id,
            job_id=job_id,
            ats_score=result["final_result"]["final_score"],
            llm_score=0.0,
            final_score=result["final_result"]["final_score"],
            explanation=result["final_result"]["explanation"]
        )
        
        # Add to ChromaDB
        CandidateChatbot.add_candidate(candidate.id, candidate.raw_text, {"name": candidate.name, "email": candidate.email, "job_id": job_id})
        
        return {"status": "success", "candidate": candidate.name}
    except Exception as e:
        logging.error(f"Error in Celery task: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
