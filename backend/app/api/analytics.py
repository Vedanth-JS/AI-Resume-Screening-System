"""
Enterprise Analytics API — Funnels, trends, diversity, recruiting, skills, reports.
All endpoints are org-scoped, with optional job-level filtering.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_db
from ..models import models
from ..core.auth_dependencies import ViewerOnly, RecruiterOnly, AdminOnly
from ..services.analytics_service import AnalyticsService
import io

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _get_service(db: AsyncSession, user: models.User) -> AnalyticsService:
    return AnalyticsService(db, user.org_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Overview
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/overview")
async def analytics_overview(
    days: int = Query(30, ge=7, le=365, description="Time range in days"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_overview(days)


# ═══════════════════════════════════════════════════════════════════════════════
# Hiring Funnel
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/funnel")
async def hiring_funnel(
    job_id: Optional[int] = Query(None, description="Filter by specific job"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_hiring_funnel(job_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Score Distribution
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/score-distribution")
async def score_distribution(
    job_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_score_distribution(job_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Time-to-Hire
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/time-to-hire")
async def time_to_hire(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_time_to_hire()


# ═══════════════════════════════════════════════════════════════════════════════
# Skill Trends
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/skill-trends")
async def skill_trends(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_skill_trends()


# ═══════════════════════════════════════════════════════════════════════════════
# Recruiter Performance
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/recruiters")
async def recruiter_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(AdminOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_recruiter_analytics()


# ═══════════════════════════════════════════════════════════════════════════════
# University Analytics
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/universities")
async def university_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_university_analytics()


# ═══════════════════════════════════════════════════════════════════════════════
# Country / Location Analytics
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/geography")
async def country_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_country_analytics()


# ═══════════════════════════════════════════════════════════════════════════════
# Diversity & Bias Metrics
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/diversity")
async def diversity_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(AdminOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_diversity_metrics()


# ═══════════════════════════════════════════════════════════════════════════════
# Volume Trends (chart data)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/volume-trends")
async def volume_trends(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = _get_service(db, current_user)
    return await svc.get_volume_trends(days)


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/export/csv")
async def export_analytics_csv(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = _get_service(db, current_user)
    csv_data = await svc.export_analytics_csv()
    return StreamingResponse(
        io.BytesIO(csv_data.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
    )
