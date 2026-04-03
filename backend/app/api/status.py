from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_db
from ..api.auth import get_current_user_with_role, RoleEnum
from ..models import models
from ..schemas import schemas
from sqlalchemy import text

router = APIRouter()
ViewerOnly = get_current_user_with_role(RoleEnum.VIEWER)

@router.get("/health")
async def health():
    return {"status": "ok", "service": "AI ATS Backend"}

@router.get("/db/ping")
async def db_ping(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"db": "alive"}

@router.get("/user/me", response_model=schemas.UserResponse)
async def me(current_user: models.User = Depends(ViewerOnly)):
    return current_user
