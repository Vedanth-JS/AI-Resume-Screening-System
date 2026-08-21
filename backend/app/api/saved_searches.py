"""
Saved Search Presets — CRUD API for recruiter filter presets.
Allows saving/loading named filter states for the candidates list.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..db.database import get_db
from ..models import models
from ..schemas.schemas import SavedSearchCreate, SavedSearchResponse
from ..api.auth import get_current_user_with_role, RoleEnum

router = APIRouter(prefix="/saved-searches", tags=["Saved Searches"])
RecruiterOnly = get_current_user_with_role(RoleEnum.RECRUITER)
ViewerOnly = get_current_user_with_role(RoleEnum.VIEWER)


@router.get("/", response_model=List[SavedSearchResponse], summary="List saved filter presets")
async def list_saved_searches(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    """Return all saved search presets for the current user."""
    stmt = (
        select(models.SavedSearch)
        .where(
            models.SavedSearch.user_id == current_user.id,
            models.SavedSearch.org_id == current_user.org_id,
        )
        .order_by(models.SavedSearch.created_at.desc())
    )
    results = (await db.execute(stmt)).scalars().all()
    return results


@router.post("/", response_model=SavedSearchResponse, status_code=201, summary="Save a filter preset")
async def create_saved_search(
    payload: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    """
    Save the current candidate filter state as a named preset.
    Each user can have up to 20 saved searches.
    """
    # Limit to 20 per user
    count_stmt = select(models.SavedSearch).where(
        models.SavedSearch.user_id == current_user.id,
    )
    existing = (await db.execute(count_stmt)).scalars().all()
    if len(existing) >= 20:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Maximum 20 saved searches per user. Delete some before adding more.",
        )

    saved = models.SavedSearch(
        org_id=current_user.org_id,
        user_id=current_user.id,
        name=payload.name,
        filters=payload.filters,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return saved


@router.delete("/{search_id}", status_code=204, summary="Delete a saved filter preset")
async def delete_saved_search(
    search_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    """Delete a saved search preset owned by the current user."""
    stmt = select(models.SavedSearch).where(
        models.SavedSearch.id == search_id,
        models.SavedSearch.user_id == current_user.id,
    )
    saved = (await db.execute(stmt)).scalars().first()
    if not saved:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved search not found")

    await db.execute(
        delete(models.SavedSearch).where(models.SavedSearch.id == search_id)
    )
    await db.commit()
    return None
