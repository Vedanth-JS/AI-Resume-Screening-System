"""
Enterprise Workflow Engine — Configurable hiring pipeline stages,
automatic stage transitions, trigger-action rules, and approval chains.
Comparable to Greenhouse, Lever, Ashby workflow automation.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.logger import log


# ═══════════════════════════════════════════════════════════════════════════════
# Stage Definitions — Standard Hiring Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class StageType(str, Enum):
    """Standardized hiring stages used across enterprise ATS platforms."""
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    TAKE_HOME = "take_home"
    ONSITE_INTERVIEW = "onsite_interview"
    FINAL_ROUND = "final_round"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class StageTransition(str, Enum):
    APPROVE = "approve"         # Move forward
    REJECT = "reject"           # Reject candidate
    SKIP = "skip"               # Skip this stage (accelerated)
    REVERT = "revert"           # Move back to previous stage
    HOLD = "hold"               # Keep in current stage

@dataclass
class Stage:
    name: StageType
    order: int
    required: bool = True
    requires_approval: bool = False
    auto_transition_after_days: Optional[int] = None  # Auto-move after N days
    sla_hours: Optional[int] = 48  # Alert if candidate in stage > N hours

# ═══════════════════════════════════════════════════════════════════════════════
# Standard Pipeline Templates
# ═══════════════════════════════════════════════════════════════════════════════

STANDARD_PIPELINE = [
    Stage(StageType.APPLIED, order=1, required=True),
    Stage(StageType.PHONE_SCREEN, order=2, required=True, requires_approval=True, sla_hours=48),
    Stage(StageType.TECHNICAL_ASSESSMENT, order=3, required=False, sla_hours=72),
    Stage(StageType.ONSITE_INTERVIEW, order=4, required=True, requires_approval=True, sla_hours=96),
    Stage(StageType.OFFER, order=5, required=True, requires_approval=True, sla_hours=168),
    Stage(StageType.HIRED, order=6, required=True),
]

EXPRESS_PIPELINE = [
    Stage(StageType.APPLIED, order=1, required=True),
    Stage(StageType.TECHNICAL_ASSESSMENT, order=2, required=True, sla_hours=48),
    Stage(StageType.OFFER, order=3, required=True, requires_approval=True, sla_hours=72),
    Stage(StageType.HIRED, order=4, required=True),
]

PipelineTemplate = List[Stage]

# ═══════════════════════════════════════════════════════════════════════════════
# Trigger-Action Rules Engine
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AutomationRule:
    """Automatically trigger actions based on events. Like Greenhouse's 'Job Setup Rules'."""
    name: str
    trigger_event: str  # e.g., "application.created", "stage.changed", "score.threshold"
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    org_id: Optional[int] = None

class WorkflowEngine:
    """Core workflow automation engine."""

    # Pre-built automation templates
    DEFAULT_RULES = [
        AutomationRule(
            name="Auto-reject below threshold",
            trigger_event="score.calculated",
            conditions={"score_lt": 30},
            actions=[
                {"type": "update_status", "status": "REJECTED"},
                {"type": "send_email", "template": "auto_rejection"},
                {"type": "add_note", "text": "Automatically rejected — score below 30%"},
            ],
        ),
        AutomationRule(
            name="Fast-track high scorers",
            trigger_event="score.calculated",
            conditions={"score_gt": 85},
            actions=[
                {"type": "add_note", "text": "High potential candidate — fast track"},
                {"type": "notify_recruiter", "priority": "high"},
                {"type": "skip_stage", "stage": "phone_screen"},
            ],
        ),
        AutomationRule(
            name="SLA breach alert",
            trigger_event="stage.time_exceeded",
            conditions={"hours_exceeded": 48},
            actions=[
                {"type": "notify_recruiter", "priority": "urgent"},
                {"type": "send_email", "template": "sla_breach_alert"},
            ],
        ),
        AutomationRule(
            name="Equal opportunity check",
            trigger_event="stage.changed",
            conditions={"from_stage": StageType.TECHNICAL_ASSESSMENT, "to_stage": StageType.REJECTED},
            actions=[
                {"type": "trigger_audit", "audit_type": "adverse_impact"},
                {"type": "require_approval", "approvers": ["hiring_manager", "hrbp"]},
            ],
        ),
    ]

    @staticmethod
    def get_pipeline_for_job(job_type: str = "standard") -> List[Stage]:
        """Return pipeline stages for a job type."""
        pipelines = {
            "standard": STANDARD_PIPELINE,
            "express": EXPRESS_PIPELINE,
            "executive": [
                Stage(StageType.APPLIED, order=1, required=True),
                Stage(StageType.ONSITE_INTERVIEW, order=2, required=True, requires_approval=True),
                Stage(StageType.FINAL_ROUND, order=3, required=True, requires_approval=True),
                Stage(StageType.OFFER, order=4, required=True, requires_approval=True),
                Stage(StageType.HIRED, order=5, required=True),
            ],
        }
        return pipelines.get(job_type, STANDARD_PIPELINE)

    @staticmethod
    async def transition_application(
        db: AsyncSession,
        application_id: int,
        transition: StageTransition,
        current_stage: StageType,
        performed_by: int,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a stage transition for an application."""
        from ..models.models import Application

        # Get application
        stmt = select(Application).where(Application.id == application_id)
        result = await db.execute(stmt)
        app = result.scalars().first()
        if not app:
            return {"error": "Application not found"}

        pipeline = WorkflowEngine.get_pipeline_for_job("standard")
        current_stage_order = next((s.order for s in pipeline if s.name == current_stage), 0)

        if transition == StageTransition.APPROVE:
            # Find next stage
            next_stages = [s for s in pipeline if s.order > current_stage_order and s.name != StageType.REJECTED]
            if next_stages:
                next_stage = next_stages[0].name
                app.status = next_stage.value
                app.stage_updated_at = datetime.now(timezone.utc)
            else:
                return {"error": "No next stage available"}

        elif transition == StageTransition.REJECT:
            app.status = StageType.REJECTED.value
            app.rejected_at = datetime.now(timezone.utc)

        elif transition == StageTransition.SKIP:
            # Skip to next non-required stage or fall back to normal approve
            skippable = [s for s in pipeline if s.order > current_stage_order and not s.required]
            if skippable:
                next_stage = skippable[0].name
                app.status = next_stage.value
            else:
                return await WorkflowEngine.transition_application(
                    db, application_id, StageTransition.APPROVE, current_stage, performed_by
                )

        elif transition == StageTransition.REVERT:
            prev_stages = [s for s in pipeline if s.order < current_stage_order]
            if prev_stages:
                prev_stage = prev_stages[-1].name
                app.status = prev_stage.value

        elif transition == StageTransition.HOLD:
            # No-op, stay in current stage
            return {"status": "held", "stage": current_stage.value}

        # Log the transition
        log.info(
            "stage_transition",
            application_id=application_id,
            from_stage=current_stage.value,
            to_stage=app.status,
            performed_by=performed_by,
            notes=notes,
        )

        await db.commit()
        return {
            "application_id": application_id,
            "previous_stage": current_stage.value,
            "new_stage": app.status,
            "transition": transition.value,
        }

    @staticmethod
    async def check_sla_breaches(db: AsyncSession, org_id: int) -> List[Dict]:
        """Check all active applications for SLA breaches."""
        from ..models.models import Application

        stmt = select(Application).where(
            Application.org_id == org_id,
            Application.status.notin_([
                StageType.HIRED.value, StageType.REJECTED.value,
                StageType.WITHDRAWN.value
            ])
        )
        result = await db.execute(stmt)
        applications = result.scalars().all()

        breaches = []
        now = datetime.now(timezone.utc)
        pipeline = WorkflowEngine.get_pipeline_for_job("standard")

        for app in applications:
            current_stage_def = next(
                (s for s in pipeline if s.name.value == app.status), None
            )
            if current_stage_def and current_stage_def.sla_hours:
                elapsed = now - (app.stage_updated_at or app.created_at)
                if elapsed.total_seconds() / 3600 > current_stage_def.sla_hours:
                    breaches.append({
                        "application_id": app.id,
                        "stage": app.status,
                        "elapsed_hours": elapsed.total_seconds() / 3600,
                        "sla_hours": current_stage_def.sla_hours,
                    })

        return breaches

    @staticmethod
    def execute_automation_rules(
        event: str,
        context: Dict[str, Any],
        org_id: Optional[int] = None,
    ) -> List[Dict]:
        """Execute trigger-action rules for a given event."""
        triggered_actions = []

        applicable_rules = [
            r for r in WorkflowEngine.DEFAULT_RULES
            if r.trigger_event == event and r.is_active
            and (r.org_id is None or r.org_id == org_id)
        ]

        for rule in applicable_rules:
            if WorkflowEngine._check_conditions(rule.conditions, context):
                for action in rule.actions:
                    triggered_actions.append({
                        "rule": rule.name,
                        "action": action,
                        "context": context,
                    })
                    log.info("automation_rule_fired", rule=rule.name, action=action["type"])

        return triggered_actions

    @staticmethod
    def _check_conditions(conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate whether conditions are met."""
        for key, value in conditions.items():
            if key == "score_lt":
                if context.get("score", 100) >= value:
                    return False
            elif key == "score_gt":
                if context.get("score", 0) <= value:
                    return False
            elif key == "hours_exceeded":
                if context.get("elapsed_hours", 0) <= value:
                    return False
            elif key == "from_stage" and context.get("from_stage") != value:
                return False
            elif key == "to_stage" and context.get("to_stage") != value:
                return False
        return True
