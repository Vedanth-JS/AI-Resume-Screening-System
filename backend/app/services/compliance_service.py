"""
Enterprise Compliance Service — GDPR, CCPA, EEOC, OFCCP.
Data subject access requests, consent management, retention policies,
compliance report generation, and right-to-delete orchestration.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, text
from ..models.models import Candidate, Application, User
from ..core.logger import log
from ..core.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# Data Subject Access Request (DSAR) — GDPR Article 15-20
# ═══════════════════════════════════════════════════════════════════════════════

class ComplianceService:
    """Handles all compliance and data subject requests."""

    @staticmethod
    async def get_candidate_data(db: AsyncSession, candidate_id: int, org_id: int) -> Dict[str, Any]:
        """GDPR Article 15: Right of Access — return all data held on a candidate."""
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.org_id == org_id,
        )
        result = await db.execute(stmt)
        candidate = result.scalars().first()
        if not candidate:
            return {"error": "Candidate not found"}

        # Get all applications
        app_stmt = select(Application).where(
            Application.candidate_id == candidate_id,
            Application.org_id == org_id,
        )
        applications = (await db.execute(app_stmt)).scalars().all()

        # Get all screening results
        from ..models.models import ScreeningResult
        scr_stmt = select(ScreeningResult).where(
            ScreeningResult.application_id.in_([a.id for a in applications])
        )
        screenings = (await db.execute(scr_stmt)).scalars().all()

        # Get all audit logs
        from ..models.event_models import AuditLog
        audit_stmt = select(AuditLog).where(
            AuditLog.entity_type == "candidate",
            AuditLog.entity_id == str(candidate_id),
        )
        audits = (await db.execute(audit_stmt)).scalars().all()

        return {
            "request_timestamp": datetime.now(timezone.utc).isoformat(),
            "candidate": {
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "raw_resume_text": candidate.raw_text,
                "parsed_data": candidate.parsed_json,
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            },
            "applications": [
                {
                    "id": a.id,
                    "job_id": a.job_id,
                    "status": a.status,
                    "score": a.score,
                    "applied_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in applications
            ],
            "screening_results": [
                {
                    "id": s.id,
                    "overall_score": s.overall_score,
                    "reasoning": s.reasoning,
                    "bias_flags": s.bias_flags,
                    "screened_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in screenings
            ],
            "audit_history": [
                {
                    "action": a.action,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "performed_by": a.user_id,
                }
                for a in audits[:50]
            ],
        }

    @staticmethod
    async def delete_candidate_data(db: AsyncSession, candidate_id: int, org_id: int) -> Dict[str, str]:
        """GDPR Article 17: Right to Erasure — permanently delete all candidate data."""
        # Verify candidate exists in this org
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.org_id == org_id,
        )
        result = await db.execute(stmt)
        candidate = result.scalars().first()
        if not candidate:
            return {"error": "Candidate not found"}

        # Remove applications
        await db.execute(
            delete(Application).where(Application.candidate_id == candidate_id)
        )
        # Remove screening results
        from ..models.models import ScreeningResult
        await db.execute(
            delete(ScreeningResult).where(
                ScreeningResult.application_id.in_(
                    select(Application.id).where(Application.candidate_id == candidate_id)
                )
            )
        )
        # Remove candidate
        await db.execute(
            delete(Candidate).where(Candidate.id == candidate_id)
        )
        await db.commit()

        log.info("dsar_delete_complete", candidate_id=candidate_id, org_id=org_id)
        return {"status": "deleted", "candidate_id": candidate_id}

    @staticmethod
    async def get_consent_status(db: AsyncSession, candidate_id: int) -> Dict[str, Any]:
        """Check whether a candidate has provided data processing consent."""
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        result = await db.execute(stmt)
        candidate = result.scalars().first()
        if not candidate:
            return {"error": "Candidate not found"}
        return {
            "candidate_id": candidate_id,
            "consent_given": getattr(candidate, "consent_given", None),
            "consent_date": getattr(candidate, "consent_date", None),
            "processing_purpose": "Recruitment and talent acquisition",
            "data_retention_days": 365,
        }

    @staticmethod
    async def withdraw_consent(db: AsyncSession, candidate_id: int) -> Dict[str, str]:
        """Allow candidate to withdraw processing consent + trigger deletion."""
        await db.execute(
            update(Candidate)
            .where(Candidate.id == candidate_id)
            .values(consent_given=False, consent_withdrawn_at=datetime.now(timezone.utc))
        )
        await db.commit()
        log.info("consent_withdrawn", candidate_id=candidate_id)
        return {"status": "consent_withdrawn", "next_step": "Data will be deleted per retention policy"}


# ═══════════════════════════════════════════════════════════════════════════════
# EEOC / OFCCP Compliance Reporting
# ═══════════════════════════════════════════════════════════════════════════════

class EEOComplianceReporter:
    """Generate EEOC and OFCCP compliance reports."""

    @staticmethod
    async def generate_eeo_report(
        db: AsyncSession,
        org_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate EEO-1 Component 1 style report."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=365)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Get all applications in date range for this org
        stmt = select(Application).where(
            Application.org_id == org_id,
            Application.created_at >= start_date,
            Application.created_at <= end_date,
        )
        result = await db.execute(stmt)
        applications = result.scalars().all()

        report = {
            "report_type": "EEO-1",
            "period": f"{start_date.date()} to {end_date.date()}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_applicants": len(applications),
            "applicants_by_status": {},
            "score_distribution": {
                "0-39": 0,
                "40-69": 0,
                "70-100": 0,
            },
            "recommendations": [],
        }

        for app in applications:
            status = app.status or "unknown"
            report["applicants_by_status"][status] = report["applicants_by_status"].get(status, 0) + 1

            if app.score is not None:
                if app.score < 40:
                    report["score_distribution"]["0-39"] += 1
                elif app.score < 70:
                    report["score_distribution"]["40-69"] += 1
                else:
                    report["score_distribution"]["70-100"] += 1

        # Flag potential adverse impact
        total = len(applications)
        if total > 0:
            rejected_low = report["score_distribution"]["0-39"]
            if rejected_low / total > 0.5:
                report["recommendations"].append(
                    "High rejection rate in lowest score band — review screening thresholds for adverse impact."
                )

        return report

    @staticmethod
    async def generate_gdpr_compliance_report(db: AsyncSession, org_id: int) -> Dict[str, Any]:
        """Generate GDPR Article 30 record of processing activities."""
        # Count candidates with consent
        consent_stmt = select(Candidate).where(
            Candidate.org_id == org_id,
            Candidate.consent_given == True,
        )
        consent_count = len((await db.execute(consent_stmt)).scalars().all())

        # Count total candidates
        total_stmt = select(Candidate).where(Candidate.org_id == org_id)
        total_count = len((await db.execute(total_stmt)).scalars().all())

        # Check for pending DSARs (simplified — would query a dedicated table)
        return {
            "report_type": "GDPR_ARTICLE_30",
            "organisation_id": org_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_processing_activities": [
                {
                    "purpose": "Recruitment and candidate screening",
                    "data_categories": ["Name", "Email", "Phone", "Resume", "Work History", "Skills"],
                    "legal_basis": "Consent",
                    "total_data_subjects": total_count,
                    "subjects_with_consent": consent_count,
                    "retention_period_days": 365,
                    "data_shared_with": ["LLM API Providers (Gemini)", "Cloud Infrastructure (GCP)"],
                    "cross_border_transfers": True,
                    "safeguards": "Standard contractual clauses, data encryption at rest and in transit",
                }
            ],
            "recommendations": [
                "Ensure consent is collected before processing any candidate data",
                "Implement automated data deletion after retention period",
                "Document all third-party data processors (Article 28)",
            ] if consent_count < total_count else [],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Data Retention Enforcement
# ═══════════════════════════════════════════════════════════════════════════════

async def enforce_retention_policy(db: AsyncSession, retention_days: int = 365):
    """Scheduled task: Delete candidates beyond retention period or with withdrawn consent."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    # Delete candidates with withdrawn consent older than 30 days
    withdrawn_cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    stmt = select(Candidate).where(
        (Candidate.created_at < cutoff) |
        ((Candidate.consent_withdrawn_at < withdrawn_cutoff) & (Candidate.consent_withdrawn_at.isnot(None)))
    )

    result = await db.execute(stmt)
    expired = result.scalars().all()

    for candidate in expired:
        await ComplianceService.delete_candidate_data(db, candidate.id, candidate.org_id)

    log.info("retention_enforcement_complete", deleted_count=len(expired))
    return {"deleted": len(expired)}


# ═══════════════════════════════════════════════════════════════════════════════
# Consent Token System
# ═══════════════════════════════════════════════════════════════════════════════

class ConsentManager:
    """Generate and verify consent tokens for candidate data access."""

    @staticmethod
    def generate_consent_token(candidate_id: int) -> str:
        """Generate a signed token for candidate self-service access."""
        import jwt
        payload = {
            "sub": f"candidate:{candidate_id}",
            "type": "consent_access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_consent_token(token: str) -> Optional[int]:
        """Verify token and extract candidate_id."""
        import jwt
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "consent_access":
                return None
            sub = payload.get("sub", "")
            if sub.startswith("candidate:"):
                return int(sub.split(":", 1)[1])
        except Exception:
            pass
        return None
