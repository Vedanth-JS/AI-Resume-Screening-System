from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from database import get_db
from models import Screening
from schemas import ScreeningOut

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=list[ScreeningOut])
def get_candidates(
    job_id: int = Query(..., description="Job ID to filter candidates by"),
    db: Session = Depends(get_db),
):
    screenings = (
        db.query(Screening)
        .options(joinedload(Screening.candidate))
        .filter(Screening.job_id == job_id)
        .order_by(desc(Screening.score))
        .all()
    )
    return screenings
