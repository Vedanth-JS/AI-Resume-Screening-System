from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import database
from ..api.auth import get_current_user, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from ..models import models
from ..schemas import schemas
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok", "service": "AI ATS Backend"}

@router.get("/config")
def config():
    return {
        "algorithm": ALGORITHM,
        "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
    }

@router.get("/db/ping")
def db_ping(db: Session = Depends(database.get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "alive"}

@router.get("/user/me", response_model=schemas.UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
