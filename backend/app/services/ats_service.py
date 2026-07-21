"""
ATS Service — Centralised business logic for pipeline, notes, activities, interviews, offers, talent pools.
All operations are org-scoped and audit-logged.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, func, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.models import User, Candidate, JobPosting, Application, Organization
from ..models.ats_models import (
    Department,
    PipelineStage,
    PipelineStageEnum,
    CandidateNote,
    ActivityLog,
    Interview,
    InterviewType,
    OfferLetter,
    OfferStatus,
    EmailTemplate,
    TalentPool,
    RejectionReason,
    BulkOperation,
)
from ..core.logger import log


class ATSService:
    def __init__(self, db: AsyncSession, org_id: int, user_id: int):
        self.db = db
        self.org_id = org_id
        self.user_id = user_id

    # ═══════════════════════════════════════════════════════════════════════════
    # Pipeline Management
    # ═══════════════════════════════════════════════════════════════════════════

    async def advance_stage(self, application_id: int, new_stage: PipelineStageEnum, notes: str = "") -> PipelineStage:
        app = await self.db.get(Application, application_id)
        if not app or app.org_id != self.org_id:
            raise ValueError("Application not found")

        # Mark previous stage as completed
        prev = await self.db.execute(
            select(PipelineStage)
            .where(
                PipelineStage.application_id == application_id,
                PipelineStage.stage == app.status,
            )
            .order_by(PipelineStage.created_at.desc())
            .limit(1)
        )
        prev_stage = prev.scalars().first()
        if prev_stage:
            prev_stage.status = "completed"
            prev_stage.completed_at = datetime.now(timezone.utc)
            prev_stage.completed_by = self.user_id

        # Create new stage
        stage = PipelineStage(
            application_id=application_id,
            stage=new_stage,
            status="active",
            notes=notes,
            assigned_to=self.user_id,
        )
        self.db.add(stage)

        # Update application status
        app.status = new_stage.value

        # Log activity
        await self._log_activity("stage_advanced", "application", application_id, {
            "from": app.status,
            "to": new_stage.value,
            "notes": notes,
        })

        await self.db.commit()
        await self.db.refresh(stage)
        return stage

    async def get_pipeline(self, job_id: int) -> Dict[PipelineStageEnum, List[Application]]:
        """Get all applications for a job grouped by pipeline stage."""
        stmt = (
            select(Application)
            .options(selectinload(Application.candidate), selectinload(Application.pipeline_stages))
            .where(Application.job_id == job_id, Application.org_id == self.org_id)
            .order_by(Application.created_at.desc())
        )
        apps = (await self.db.execute(stmt)).scalars().all()

        pipeline: Dict[PipelineStageEnum, List[Application]] = {}
        for stage in PipelineStageEnum:
            pipeline[stage] = []

        for app in apps:
            current_stage = PipelineStageEnum(app.status) if app.status else PipelineStageEnum.APPLIED
            if current_stage in pipeline:
                pipeline[current_stage].append(app)
        return pipeline

    # ═══════════════════════════════════════════════════════════════════════════
    # Notes & Comments
    # ═══════════════════════════════════════════════════════════════════════════

    async def add_note(self, candidate_id: int, content: str, is_private: bool = False, tags: dict = None) -> CandidateNote:
        note = CandidateNote(
            candidate_id=candidate_id,
            author_id=self.user_id,
            content=content,
            is_private=is_private,
            tags=tags or {},
        )
        self.db.add(note)
        await self._log_activity("note_added", "candidate", candidate_id, {"content_preview": content[:100]})
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def get_notes(self, candidate_id: int) -> List[CandidateNote]:
        stmt = (
            select(CandidateNote)
            .options(selectinload(CandidateNote.author))
            .where(
                CandidateNote.candidate_id == candidate_id,
                CandidateNote.is_private == False,  # only non-private visible to team
            )
            .order_by(CandidateNote.created_at.desc())
        )
        return (await self.db.execute(stmt)).scalars().all()

    # ═══════════════════════════════════════════════════════════════════════════
    # Activity Timeline
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_activity(self, entity_type: str = None, entity_id: int = None, limit: int = 50) -> List[ActivityLog]:
        stmt = select(ActivityLog).where(ActivityLog.org_id == self.org_id)
        if entity_type:
            stmt = stmt.where(ActivityLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(ActivityLog.entity_id == entity_id)
        stmt = stmt.order_by(ActivityLog.created_at.desc()).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

    async def _log_activity(self, action: str, entity_type: str, entity_id: int, details: dict = None):
        log_entry = ActivityLog(
            org_id=self.org_id,
            user_id=self.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
        self.db.add(log_entry)

    # ═══════════════════════════════════════════════════════════════════════════
    # Interviews
    # ═══════════════════════════════════════════════════════════════════════════

    async def schedule_interview(
        self,
        application_id: int,
        interview_type: InterviewType,
        scheduled_at: datetime,
        duration_minutes: int = 60,
        location: str = "",
        interviewers: list = None,
    ) -> Interview:
        app = await self.db.get(Application, application_id)
        if not app or app.org_id != self.org_id:
            raise ValueError("Application not found")

        interview = Interview(
            org_id=self.org_id,
            application_id=application_id,
            interview_type=interview_type,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            location=location,
            interviewers=interviewers or [],
            status="scheduled",
        )
        self.db.add(interview)

        # Advance pipeline to appropriate stage
        await self.advance_stage(application_id, PipelineStageEnum.PHONE_SCREEN)

        await self._log_activity("interview_scheduled", "interview", interview.id, {
            "type": interview_type.value,
            "scheduled_at": scheduled_at.isoformat(),
        })
        await self.db.commit()
        await self.db.refresh(interview)
        return interview

    async def get_upcoming_interviews(self, days: int = 7) -> List[Interview]:
        cutoff = datetime.now(timezone.utc)
        stmt = (
            select(Interview)
            .where(
                Interview.org_id == self.org_id,
                Interview.scheduled_at >= cutoff,
            )
            .order_by(Interview.scheduled_at)
        )
        return (await self.db.execute(stmt)).scalars().all()

    # ═══════════════════════════════════════════════════════════════════════════
    # Offer Letters
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_offer(
        self,
        application_id: int,
        title: str,
        salary: float,
        content_html: str,
        start_date: datetime,
        expiry_days: int = 7,
        currency: str = "USD",
    ) -> OfferLetter:
        app = await self.db.get(Application, application_id)
        if not app or app.org_id != self.org_id:
            raise ValueError("Application not found")

        offer = OfferLetter(
            org_id=self.org_id,
            application_id=application_id,
            title=title,
            salary=salary,
            currency=currency,
            start_date=start_date,
            expiry_date=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + __import__("datetime").timedelta(days=expiry_days),
            content_html=content_html,
            status=OfferStatus.DRAFT,
        )
        self.db.add(offer)

        # Advance pipeline
        await self.advance_stage(application_id, PipelineStageEnum.OFFER_EXTENDED)

        await self._log_activity("offer_created", "offer", offer.id, {"title": title, "salary": salary})
        await self.db.commit()
        await self.db.refresh(offer)
        return offer

    async def send_offer(self, offer_id: int) -> OfferLetter:
        offer = await self.db.get(OfferLetter, offer_id)
        if not offer or offer.org_id != self.org_id:
            raise ValueError("Offer not found")

        offer.status = OfferStatus.SENT
        await self._log_activity("offer_sent", "offer", offer_id)
        await self.db.commit()
        return offer

    async def get_offers_for_application(self, application_id: int) -> List[OfferLetter]:
        stmt = (
            select(OfferLetter)
            .where(OfferLetter.application_id == application_id)
            .order_by(OfferLetter.created_at.desc())
        )
        return (await self.db.execute(stmt)).scalars().all()

    # ═══════════════════════════════════════════════════════════════════════════
    # Rejections
    # ═══════════════════════════════════════════════════════════════════════════

    async def reject_candidate(self, application_id: int, reason_id: int = None, notes: str = "") -> PipelineStage:
        app = await self.db.get(Application, application_id)
        if not app or app.org_id != self.org_id:
            raise ValueError("Application not found")

        stage = await self.advance_stage(application_id, PipelineStageEnum.REJECTED, notes)

        # Log with reason
        reason = None
        if reason_id:
            reason = await self.db.get(RejectionReason, reason_id)
        await self._log_activity("candidate_rejected", "application", application_id, {
            "reason": reason.reason if reason else notes,
        })
        return stage

    # ═══════════════════════════════════════════════════════════════════════════
    # Talent Pools
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_pool(self, name: str, description: str = "", criteria: dict = None) -> TalentPool:
        pool = TalentPool(
            org_id=self.org_id,
            name=name,
            description=description,
            criteria=criteria or {},
            owner_id=self.user_id,
        )
        self.db.add(pool)
        await self.db.commit()
        await self.db.refresh(pool)
        return pool

    async def add_to_pool(self, pool_id: int, candidate_id: int):
        await self.db.execute(
            talent_pool_candidates.insert().values(
                talent_pool_id=pool_id,
                candidate_id=candidate_id,
                added_by=self.user_id,
                added_at=datetime.now(timezone.utc),
            )
        )
        await self._log_activity("added_to_pool", "candidate", candidate_id, {"pool_id": pool_id})
        await self.db.commit()

    async def list_pools(self) -> List[TalentPool]:
        stmt = select(TalentPool).where(TalentPool.org_id == self.org_id)
        return (await self.db.execute(stmt)).scalars().all()

    # ═══════════════════════════════════════════════════════════════════════════
    # Email Templates
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_template(self, name: str, subject: str, body_html: str, type: str, variables: dict = None) -> EmailTemplate:
        template = EmailTemplate(
            org_id=self.org_id,
            name=name,
            subject=subject,
            body_html=body_html,
            type=type,
            variables=variables or {},
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def list_templates(self, template_type: str = None) -> List[EmailTemplate]:
        stmt = select(EmailTemplate).where(EmailTemplate.org_id == self.org_id)
        if template_type:
            stmt = stmt.where(EmailTemplate.type == template_type)
        return (await self.db.execute(stmt)).scalars().all()

    # ═══════════════════════════════════════════════════════════════════════════
    # Bulk Operations
    # ═══════════════════════════════════════════════════════════════════════════

    async def bulk_stage_change(
        self, application_ids: List[int], new_stage: PipelineStageEnum, notes: str = ""
    ) -> BulkOperation:
        op = BulkOperation(
            org_id=self.org_id,
            initiated_by=self.user_id,
            operation_type="stage_change",
            target_count=len(application_ids),
            status="running",
        )
        self.db.add(op)
        await self.db.flush()

        completed, failed = 0, 0
        for aid in application_ids:
            try:
                await self.advance_stage(aid, new_stage, notes)
                # Avoid over-committing within the loop
                completed += 1
            except Exception as e:
                log.error("bulk_stage_change.error", application_id=aid, error=str(e))
                failed += 1

        op.completed_count = completed
        op.failed_count = failed
        op.status = "completed" if failed == 0 else "completed_with_errors"
        op.result_summary = {"completed": completed, "failed": failed, "stage": new_stage.value}
        await self.db.commit()
        return op

    async def bulk_reject(self, application_ids: List[int], reason_id: int = None, notes: str = "") -> BulkOperation:
        op = BulkOperation(
            org_id=self.org_id,
            initiated_by=self.user_id,
            operation_type="reject",
            target_count=len(application_ids),
            status="running",
        )
        self.db.add(op)
        await self.db.flush()

        completed, failed = 0, 0
        for aid in application_ids:
            try:
                await self.reject_candidate(aid, reason_id, notes)
                completed += 1
            except Exception as e:
                log.error("bulk_reject.error", application_id=aid, error=str(e))
                failed += 1

        op.completed_count = completed
        op.failed_count = failed
        op.status = "completed" if failed == 0 else "completed_with_errors"
        op.result_summary = {"completed": completed, "failed": failed}
        await self.db.commit()
        return op

    # ═══════════════════════════════════════════════════════════════════════════
    # Department Management
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_department(self, name: str, description: str = "") -> Department:
        dept = Department(org_id=self.org_id, name=name, description=description)
        self.db.add(dept)
        await self.db.commit()
        await self.db.refresh(dept)
        return dept

    async def list_departments(self) -> List[Department]:
        stmt = select(Department).where(Department.org_id == self.org_id)
        return (await self.db.execute(stmt)).scalars().all()


# Import talent_pool_candidates table for use in service methods
from ..models.ats_models import talent_pool_candidates
