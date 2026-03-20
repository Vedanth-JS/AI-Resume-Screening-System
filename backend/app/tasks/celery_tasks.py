from celery import Celery
import os
from ..core.parser import ResumeParser
from ..core.extractor import FeatureExtractor
from ..core.scorer import Scorer
from ..db.database import SessionLocal
from ..db import crud, models
import logging

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

@celery_app.task
def process_resume_task(job_id: int, filename: str, file_content: bytes, candidate_email: str):
    db = SessionLocal()
    try:
        # 1. Parse
        raw_text = ResumeParser.extract_text(file_content, filename)
        
        # 2. Extract Features
        extractor = FeatureExtractor(raw_text)
        skills = extractor.extract_skills()
        exp = extractor.extract_experience()
        edu = extractor.extract_education()
        entities = extractor.extract_entities()
        name = entities.get("PERSON", ["Unknown"])[0]
        
        # 3. Get Job Details
        job = crud.get_job_posting(db, job_id)
        if not job:
            return {"error": "Job not found"}
        
        # 4. Score
        # TF-IDF for now, can add BERT
        semantic_score = Scorer.compute_tfidf_similarity(job.description, raw_text)
        
        scores = Scorer.calculate_total_score(
            skills_matched=skills,
            required_skills=job.required_skills,
            candidate_exp=exp,
            required_exp=job.min_experience,
            candidate_edu=edu,
            required_edu=job.required_education,
            semantic_score=semantic_score
        )
        
        # 5. Determine Status
        status = "reject"
        if scores["total_score"] >= 0.7:
            status = "accept"
        elif scores["total_score"] >= 0.5:
            status = "review"
            
        # 6. Save Candidate
        candidate = crud.create_candidate(
            db, name=name, email=candidate_email, path=filename,
            text=raw_text, skills=skills, exp=exp, edu=edu
        )
        
        # 7. Save Result
        matched = [s for s in skills if s.lower() in [js.lower() for js in job.required_skills]]
        missing = [s for s in job.required_skills if s.lower() not in [cs.lower() for cs in skills]]
        
        crud.create_screening_result(
            db, job_id=job.id, candidate_id=candidate.id,
            scores=scores, matched=matched, missing=missing, status=status
        )
        
        return {"status": "success", "candidate": name, "score": scores["total_score"]}
        
    except Exception as e:
        logging.error(f"Error processing resume: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
