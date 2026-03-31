from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from ..models import models
from ..schemas import schemas
from ..db import database, crud
from ..api.auth import get_current_user, check_admin

router = APIRouter()

@router.get("/notifications", response_model=List[schemas.NotificationResponse])
def list_notifications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    return crud.get_user_notifications(db, current_user.id)

@router.post("/notifications", response_model=schemas.NotificationResponse)
def create_notification_endpoint(
    user_id: int,
    message: str,
    admin: models.User = Depends(check_admin),
    db: Session = Depends(database.get_db)
):
    return crud.create_notification(db, user_id, message)
