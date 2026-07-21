"""
ATS API v2 — Full Applicant Tracking System endpoints.
Pipeline management, notes, activity timeline, interviews, offers,
talent pools, email templates, departments, bulk operations.
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..db.database import get_db
from ..models import models
from ..models.ats_models import (
    PipelineStageEnum,
    InterviewType,
    OfferStatus,
    CommunicationType,
)
from ..services.ats_service import ATSService
from ..api.auth import get_current_user_with_role
from ..models.models import RoleEnum

router = APIRouter(prefix="/api/v2/ats", tags=["ATS v2"])

# ─── Auth dependencies ────────────────────────────────────────────────────────
RecruiterOnly = get_current_user_with_role(RoleEnum.RECRUITER)
AdminOnly = get_current_user_with_role(RoleEnum.ADMIN)
ViewerOnly = get_current_user_with_role(RoleEnum.VIEWER)


# ═══════════════════════════════════════════════════════════════════════════════
# Request Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class AdvanceStageRequest(BaseModel):
    new_stage: PipelineStageEnum
    notes: str = ""

class NoteCreateRequest(BaseModel):
    candidate_id: int
    content: str
    is_private: bool = False
    tags: dict = Field(default_factory=dict)

class InterviewScheduleRequest(BaseModel):
    application_id: int
    interview_type: InterviewType
    scheduled_at: datetime
    duration_minutes: int = 60
    location: str = ""
    interviewers: list = Field(default_factory=list)

class OfferCreateRequest(BaseModel):
    application_id: int
    title: str
    salary: float
    content_html: str
    start_date: datetime
    expiry_days: int = 7
    currency: str = "USD"

class RejectRequest(BaseModel):
    application_id: int
    reason_id: Optional[int] = None
    notes: str = ""

class PoolCreateRequest(BaseModel):
    name: str
    description: str = ""
    criteria: dict = Field(default_factory=dict)

class PoolAddRequest(BaseModel):
    pool_id: int
    candidate_id: int

class TemplateCreateRequest(BaseModel):
    name: str
    subject: str
    body_html: str
    type: str = "general"
    variables: dict = Field(default_factory=dict)

class DepartmentCreateRequest(BaseModel):
    name: str
    description: str = ""

class BulkStageChangeRequest(BaseModel):
    application_ids: List[int]
    new_stage: PipelineStageEnum
    notes: str = ""

class BulkRejectRequest(BaseModel):
    application_ids: List[int]
    reason_id: Optional[int] = None
    notes: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/pipeline/advance")
async def advance_stage(
    req: AdvanceStageRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    try:
        stage = await svc.advance_stage(req.application_id, req.new_stage, req.notes)
        return {"stage": stage.stage, "status": stage.status, "id": stage.id}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/pipeline/{job_id}")
async def get_pipeline(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    pipeline = await svc.get_pipeline(job_id)
    return {
        stage.value: len(apps)
        for stage, apps in pipeline.items()
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Notes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/notes")
async def add_note(
    req: NoteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    note = await svc.add_note(req.candidate_id, req.content, req.is_private, req.tags)
    return {"id": note.id, "content": note.content[:200]}


@router.get("/notes/{candidate_id}")
async def get_notes(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    notes = await svc.get_notes(candidate_id)
    return [
        {
            "id": n.id,
            "author": n.author.email if n.author else "Unknown",
            "content": n.content,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "tags": n.tags,
        }
        for n in notes
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Activity Timeline
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/activity")
async def get_activity(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    logs = await svc.get_activity(entity_type, entity_id, limit)
    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "user_id": l.user_id,
        }
        for l in logs
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Interviews
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/interviews/schedule")
async def schedule_interview(
    req: InterviewScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    try:
        interview = await svc.schedule_interview(
            req.application_id,
            req.interview_type,
            req.scheduled_at,
            req.duration_minutes,
            req.location,
            req.interviewers,
        )
        return {"id": interview.id, "status": interview.status, "scheduled_at": interview.scheduled_at.isoformat()}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/interviews/upcoming")
async def get_upcoming_interviews(
    days: int = Query(7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    interviews = await svc.get_upcoming_interviews(days)
    return [
        {
            "id": i.id,
            "application_id": i.application_id,
            "type": i.interview_type.value if i.interview_type else None,
            "scheduled_at": i.scheduled_at.isoformat() if i.scheduled_at else None,
            "duration": i.duration_minutes,
            "status": i.status,
        }
        for i in interviews
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Offers
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/offers")
async def create_offer(
    req: OfferCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    try:
        offer = await svc.create_offer(
            req.application_id,
            req.title,
            req.salary,
            req.content_html,
            req.start_date,
            req.expiry_days,
            req.currency,
        )
        return {"id": offer.id, "status": offer.status.value, "token": offer.token}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/offers/{offer_id}/send")
async def send_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    try:
        offer = await svc.send_offer(offer_id)
        return {"id": offer.id, "status": offer.status.value}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/offers/{application_id}")
async def get_offers(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    offers = await svc.get_offers_for_application(application_id)
    return [
        {"id": o.id, "title": o.title, "salary": o.salary, "status": o.status.value, "created_at": o.created_at.isoformat()}
        for o in offers
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Rejections
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/reject")
async def reject_candidate(
    req: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    try:
        stage = await svc.reject_candidate(req.application_id, req.reason_id, req.notes)
        return {"stage": stage.stage.value, "status": stage.status}
    except ValueError as e:
        raise HTTPException(404, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Talent Pools
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/pools")
async def create_pool(
    req: PoolCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    pool = await svc.create_pool(req.name, req.description, req.criteria)
    return {"id": pool.id, "name": pool.name}


@router.post("/pools/add")
async def add_to_pool(
    req: PoolAddRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    await svc.add_to_pool(req.pool_id, req.candidate_id)
    return {"status": "success"}


@router.get("/pools")
async def list_pools(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    pools = await svc.list_pools()
    return [{"id": p.id, "name": p.name, "description": p.description} for p in pools]


# ═══════════════════════════════════════════════════════════════════════════════
# Email Templates
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/templates")
async def create_template(
    req: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(AdminOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    template = await svc.create_template(req.name, req.subject, req.body_html, req.type, req.variables)
    return {"id": template.id, "name": template.name}


@router.get("/templates")
async def list_templates(
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    templates = await svc.list_templates(type)
    return [{"id": t.id, "name": t.name, "subject": t.subject, "type": t.type} for t in templates]


# ═══════════════════════════════════════════════════════════════════════════════
# Departments
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/departments")
async def create_department(
    req: DepartmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(AdminOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    dept = await svc.create_department(req.name, req.description)
    return {"id": dept.id, "name": dept.name}


@router.get("/departments")
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    depts = await svc.list_departments()
    return [{"id": d.id, "name": d.name, "description": d.description} for d in depts]


# ═══════════════════════════════════════════════════════════════════════════════
# Bulk Operations
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/bulk/stage-change")
async def bulk_stage_change(
    req: BulkStageChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    op = await svc.bulk_stage_change(req.application_ids, req.new_stage, req.notes)
    return {
        "id": op.id,
        "status": op.status,
        "target": op.target_count,
        "completed": op.completed_count,
        "failed": op.failed_count,
    }


@router.post("/bulk/reject")
async def bulk_reject(
    req: BulkRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(RecruiterOnly),
):
    svc = ATSService(db, current_user.org_id, current_user.id)
    op = await svc.bulk_reject(req.application_ids, req.reason_id, req.notes)
    return {
        "id": op.id,
        "status": op.status,
        "target": op.target_count,
        "completed": op.completed_count,
        "failed": op.failed_count,
    }
