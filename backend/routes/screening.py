from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from database import get_db
from models import Candidate, Job, Screening
from schemas import ScreenRequest, BatchScreenRequest, ScreeningOut
from ai_service import screen_resume
from models import RecommendationEnum

router = APIRouter(tags=["Screening"])


def _do_screen(candidate: Candidate, job: Job, db: Session) -> Screening:
    """Core screening logic: call AI, save result."""
    result = screen_resume(
        resume_text=candidate.resume_text,
        job_title=job.title,
        job_description=job.description,
        required_skills=job.required_skills or [],
    )

    # Remove old screening for this candidate+job if exists
    db.query(Screening).filter(
        Screening.candidate_id == candidate.id,
        Screening.job_id == job.id
    ).delete()

    screening = Screening(
        candidate_id=candidate.id,
        job_id=job.id,
        score=result.score,
        matched_skills=result.matched_skills,
        missing_skills=result.missing_skills,
        ai_summary=result.summary,
        recommendation=RecommendationEnum(result.recommendation.value),
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)
    # Reload with relationships
    return db.query(Screening).options(joinedload(Screening.candidate)).filter(Screening.id == screening.id).first()


@router.post("/screen", response_model=ScreeningOut)
def screen_single(req: ScreenRequest, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == req.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return _do_screen(candidate, job, db)


@router.post("/screen/batch", response_model=list[ScreeningOut])
def screen_batch(req: BatchScreenRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = []
    for cid in req.candidate_ids:
        candidate = db.query(Candidate).filter(Candidate.id == cid).first()
        if candidate:
            try:
                screening = _do_screen(candidate, job, db)
                results.append(screening)
            except Exception as e:
                print(f"Error screening candidate {cid}: {e}")
    return results


@router.post("/jobs/{job_id}/rescreen", response_model=list[ScreeningOut])
def rescreen_job(job_id: int, db: Session = Depends(get_db)):
    """Re-screen ALL candidates previously screened for this job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_candidate_ids = db.query(Screening.candidate_id).filter(
        Screening.job_id == job_id
    ).distinct().all()
    candidate_ids = [row[0] for row in existing_candidate_ids]

    results = []
    for cid in candidate_ids:
        candidate = db.query(Candidate).filter(Candidate.id == cid).first()
        if candidate:
            try:
                screening = _do_screen(candidate, job, db)
                results.append(screening)
            except Exception as e:
                print(f"Error re-screening candidate {cid}: {e}")
    return results
