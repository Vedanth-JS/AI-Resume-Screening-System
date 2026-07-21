"""
Enterprise-Grade API Endpoints — Compliance, Webhooks, Calendar, Workflows.
Provides Greenhouse/Lever-comparable enterprise features.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field

from ..db.database import get_db
from ..core.auth_dependencies import AdminOnly, RecruiterOnly, ViewerOnly, get_current_user
from ..services.compliance_service import (
    ComplianceService,
    EEOComplianceReporter,
    enforce_retention_policy,
    ConsentManager,
)
from ..services.workflow_engine import (
    WorkflowEngine,
    StageType,
    StageTransition,
    PipelineTemplate,
)
from ..services.webhook_service import (
    WebhookService,
    WebhookEvent,
    CalendarService,
    CalendarProvider,
)
from ..core.logger import log

router = APIRouter(prefix="/api/enterprise", tags=["Enterprise"])


# ═══════════════════════════════════════════════════════════════════════════════
# GDPR / CCPA Compliance
# ═══════════════════════════════════════════════════════════════════════════════

class WebhookSubscribeRequest(BaseModel):
    url: str
    events: List[str]
    description: str = ""

class WebhookResponse(BaseModel):
    id: str
    url: str
    events: List[str]
    is_active: bool
    verify_token: Optional[str] = None


@router.get("/gdpr/dsar/{candidate_id}", tags=["Compliance"])
async def data_subject_access_request(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(AdminOnly),
):
    """GDPR Article 15 — Return all personal data held on a candidate."""
    data = await ComplianceService.get_candidate_data(
        db, candidate_id, current_user.org_id
    )
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.delete("/gdpr/erase/{candidate_id}", tags=["Compliance"])
async def right_to_erasure(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(AdminOnly),
):
    """GDPR Article 17 — Permanently delete all candidate data."""
    result = await ComplianceService.delete_candidate_data(
        db, candidate_id, current_user.org_id
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/gdpr/consent/{candidate_id}/withdraw", tags=["Compliance"])
async def withdraw_consent(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(AdminOnly),
):
    """Allow a candidate to withdraw data processing consent."""
    result = await ComplianceService.withdraw_consent(db, candidate_id)
    return result


@router.get("/compliance/eeo-report", tags=["Compliance"])
async def generate_eeo_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(AdminOnly),
):
    """Generate EEOC/OFCCP compliance report."""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    report = await EEOComplianceReporter.generate_eeo_report(
        db, current_user.org_id, start, end
    )
    return report


@router.get("/compliance/gdpr-report", tags=["Compliance"])
async def generate_gdpr_report(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(AdminOnly),
):
    """Generate GDPR Article 30 record of processing activities."""
    report = await EEOComplianceReporter.generate_gdpr_compliance_report(
        db, current_user.org_id
    )
    return report


@router.post("/compliance/retention/enforce", tags=["Compliance"])
async def enforce_data_retention(
    retention_days: int = Query(365, ge=30, le=2555),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(AdminOnly),
):
    """Manually trigger data retention enforcement."""
    result = await enforce_retention_policy(db, retention_days)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Webhook Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/webhooks", tags=["Webhooks"])
async def create_webhook(
    request: WebhookSubscribeRequest,
    current_user=Depends(RecruiterOnly),
):
    """Subscribe to webhook events."""
    events = [WebhookEvent(e) for e in request.events if e in [ev.value for ev in WebhookEvent]]
    if not events:
        raise HTTPException(400, "No valid events specified")

    sub = WebhookService.subscribe(
        url=request.url,
        events=events,
        org_id=current_user.org_id,
        description=request.description,
    )
    return {
        "id": sub.id,
        "url": sub.url,
        "events": [e.value for e in sub.events],
        "is_active": sub.is_active,
        "verify_token": sub.secret,  # Only returned on creation
    }


@router.get("/webhooks", tags=["Webhooks"])
async def list_webhooks(
    current_user=Depends(ViewerOnly),
):
    """List all webhook subscriptions."""
    return WebhookService.list_subscriptions(current_user.org_id)


@router.delete("/webhooks/{subscription_id}", tags=["Webhooks"])
async def delete_webhook(
    subscription_id: str,
    current_user=Depends(RecruiterOnly),
):
    """Remove a webhook subscription."""
    if WebhookService.unsubscribe(subscription_id):
        return {"status": "deleted", "id": subscription_id}
    raise HTTPException(404, "Webhook not found")


# ═══════════════════════════════════════════════════════════════════════════════
# Calendar Integration — Interview Scheduling
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/calendar/availability", tags=["Calendar"])
async def get_interview_slots(
    provider: str = Query("google", regex="^(google|outlook_365|apple)$"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    duration_minutes: int = Query(60, ge=15, le=240),
    current_user=Depends(RecruiterOnly),
):
    """Get available interview time slots from a calendar provider."""
    cal_provider = CalendarProvider(provider)
    start = datetime.fromisoformat(start_date) if start_date else datetime.now(timezone.utc)
    end = datetime.fromisoformat(end_date) if end_date else start + timedelta(days=14)

    slots = await CalendarService.get_available_slots(
        cal_provider, start, end, duration_minutes, current_user.email
    )
    return {"provider": provider, "slots": slots, "count": len(slots)}


@router.post("/calendar/schedule", tags=["Calendar"])
async def schedule_interview(
    provider: str = Query("google"),
    start_time: str = Query(...),
    end_time: str = Query(...),
    title: str = Query("Candidate Interview"),
    description: str = Query(""),
    candidate_email: str = Query(...),
    current_user=Depends(RecruiterOnly),
):
    """Schedule an interview and send calendar invites."""
    cal_provider = CalendarProvider(provider)
    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)

    result = await CalendarService.schedule_interview(
        provider=cal_provider,
        start_time=start,
        end_time=end,
        attendees=[current_user.email, candidate_email],
        title=title,
        description=description,
    )

    # Also send calendar invite to candidate
    if candidate_email:
        await CalendarService.send_calendar_invite(
            to_email=candidate_email,
            event_details={
                "event_id": result["event_id"],
                "start": start_time,
                "end": end_time,
                "title": title,
                "description": description,
            },
            provider=cal_provider,
        )

    return result


@router.delete("/calendar/{event_id}", tags=["Calendar"])
async def cancel_interview(
    event_id: str,
    provider: str = Query("google"),
    current_user=Depends(RecruiterOnly),
):
    """Cancel a scheduled interview."""
    cal_provider = CalendarProvider(provider)
    result = await CalendarService.cancel_interview(cal_provider, event_id)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow Engine
# ═══════════════════════════════════════════════════════════════════════════════


class TransitionRequest(BaseModel):
    transition: str  # approve, reject, skip, revert, hold
    current_stage: str
    notes: Optional[str] = None

class PipelineDefinition(BaseModel):
    name: str
    stages: List[dict]


@router.get("/workflow/pipelines", tags=["Workflow"])
async def list_pipelines():
    """Get available hiring pipeline templates."""
    return {
        "pipelines": [
            {
                "name": "standard",
                "stages": [
                    {
                        "name": s.name.value,
                        "order": s.order,
                        "required": s.required,
                        "requires_approval": s.requires_approval,
                        "sla_hours": s.sla_hours,
                    }
                    for s in WorkflowEngine.get_pipeline_for_job("standard")
                ],
            },
            {
                "name": "express",
                "stages": [
                    {
                        "name": s.name.value,
                        "order": s.order,
                        "required": s.required,
                        "sla_hours": s.sla_hours,
                    }
                    for s in WorkflowEngine.get_pipeline_for_job("express")
                ],
            },
            {
                "name": "executive",
                "stages": [
                    {"name": s.name.value, "order": s.order}
                    for s in WorkflowEngine.get_pipeline_for_job("executive")
                ],
            },
        ]
    }


@router.post("/workflow/application/{application_id}/transition", tags=["Workflow"])
async def transition_application(
    application_id: int,
    request: TransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RecruiterOnly),
):
    """Advance, reject, skip, revert, or hold an application through a hiring pipeline."""
    transition = StageTransition(request.transition)
    current_stage = StageType(request.current_stage)

    result = await WorkflowEngine.transition_application(
        db=db,
        application_id=application_id,
        transition=transition,
        current_stage=current_stage,
        performed_by=current_user.id,
        notes=request.notes,
    )

    if "error" in result:
        raise HTTPException(400, result["error"])

    # Publish webhook event
    await WebhookService.publish(
        WebhookEvent.STAGE_CHANGED,
        {
            "application_id": application_id,
            "from_stage": request.current_stage,
            "to_stage": result["new_stage"],
            "transition": request.transition,
            "performed_by": current_user.id,
        },
        current_user.org_id,
    )

    return result


@router.get("/workflow/sla-breaches", tags=["Workflow"])
async def check_sla_breaches(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(ViewerOnly),
):
    """Check for applications exceeding SLA time limits."""
    breaches = await WorkflowEngine.check_sla_breaches(db, current_user.org_id)
    return {"breaches": breaches, "count": len(breaches)}


@router.get("/workflow/automation-rules", tags=["Workflow"])
async def list_automation_rules():
    """List available automation rules."""
    return {
        "rules": [
            {
                "name": r.name,
                "trigger_event": r.trigger_event,
                "conditions": r.conditions,
                "actions": [a["type"] for a in r.actions],
            }
            for r in WorkflowEngine.DEFAULT_RULES
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Candidate Self-Service Portal
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/public/candidate/{token}", tags=["Candidate Portal"])
async def candidate_self_service(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Candidate self-service: view application status using consent token."""
    candidate_id = ConsentManager.verify_consent_token(token)
    if not candidate_id:
        raise HTTPException(401, "Invalid or expired consent token")

    data = await ComplianceService.get_candidate_data(db, candidate_id, None)
    # Filter sensitive fields for candidate view
    return {
        "name": data.get("candidate", {}).get("name"),
        "applications": data.get("applications", []),
        "screening_results": data.get("screening_results", []),
        "request_timestamp": data.get("request_timestamp"),
    }


@router.post("/public/consent/withdraw/{token}", tags=["Candidate Portal"])
async def candidate_withdraw_consent_public(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint for candidates to withdraw consent."""
    candidate_id = ConsentManager.verify_consent_token(token)
    if not candidate_id:
        raise HTTPException(401, "Invalid or expired consent token")

    result = await ComplianceService.withdraw_consent(db, candidate_id)
    return result
