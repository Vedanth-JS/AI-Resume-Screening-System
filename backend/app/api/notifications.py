from fastapi import APIRouter, Depends, status, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..models import models
from ..schemas import schemas
from ..db.database import get_db
from ..api.auth import get_current_user_with_role, RoleEnum

router = APIRouter(prefix="/notifications", tags=["Notifications"])
ViewerOnly = get_current_user_with_role(RoleEnum.VIEWER)
AdminOnly = get_current_user_with_role(RoleEnum.ADMIN)

@router.get("/", response_model=List[schemas.NotificationResponse])
async def list_notifications(
    current_user: models.User = Depends(ViewerOnly),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(models.Notification).where(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: models.User = Depends(ViewerOnly),
    db: AsyncSession = Depends(get_db)
):
    stmt = update(models.Notification).where(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id
    ).values(is_read=True)
    await db.execute(stmt)
    await db.commit()
    return {"status": "success"}

@router.post("/", response_model=schemas.NotificationResponse)
async def create_notification(
    data: schemas.NotificationCreate,
    current_user: models.User = Depends(AdminOnly),
    db: AsyncSession = Depends(get_db)
):
    new_notif = models.Notification(
        user_id=data.user_id,
        message=data.message
    )
    db.add(new_notif)
    await db.commit()
    await db.refresh(new_notif)
    return new_notif
