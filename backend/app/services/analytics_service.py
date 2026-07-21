"""
Enterprise Analytics Service — Comprehensive hiring metrics, funnels, diversity, trends.
All queries are org-scoped and use optimized aggregation queries.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy import select, func, text, case, extract, cast, Float, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from collections import Counter, defaultdict

from ..models.models import (
    Candidate, JobPosting, Application, ScreeningResult,
    Organization, User, AuditLog,
)
from ..models.auth_models import AuthAuditLog
from ..core.logger import log


class AnalyticsService:
    def __init__(self, db: AsyncSession, org_id: int):
        self.db = db
        self.org_id = org_id

    # ═══════════════════════════════════════════════════════════════════════════
    # Dashboard Overview
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_overview(self, days: int = 30) -> Dict[str, Any]:
        """Org-wide dashboard summary."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Total applications
        total_stmt = select(func.count(Application.id)).where(
            Application.org_id == self.org_id,
            Application.deleted_at.is_(None),
        )
        total = (await self.db.execute(total_stmt)).scalar() or 0

        # Applications in period
        period_stmt = select(func.count(Application.id)).where(
            Application.org_id == self.org_id,
            Application.created_at >= cutoff,
            Application.deleted_at.is_(None),
        )
        period_total = (await self.db.execute(period_stmt)).scalar() or 0

        # Average score
        avg_stmt = select(func.avg(Application.score)).where(
            Application.org_id == self.org_id,
            Application.score.isnot(None),
            Application.deleted_at.is_(None),
        )
        avg_score = (await self.db.execute(avg_stmt)).scalar() or 0

        # Status distribution
        status_stmt = select(
            Application.status, func.count(Application.id)
        ).where(
            Application.org_id == self.org_id,
            Application.deleted_at.is_(None),
        ).group_by(Application.status)
        status_rows = (await self.db.execute(status_stmt)).all()
        status_dist = {row[0]: row[1] for row in status_rows}

        # Active jobs
        job_stmt = select(func.count(JobPosting.id)).where(
            JobPosting.org_id == self.org_id,
            JobPosting.status == "active",
            JobPosting.deleted_at.is_(None),
        )
        active_jobs = (await self.db.execute(job_stmt)).scalar() or 0

        # Trends (last 7 days vs previous 7)
        prev_cutoff = cutoff - timedelta(days=days)
        prev_stmt = select(func.count(Application.id)).where(
            Application.org_id == self.org_id,
            Application.created_at.between(prev_cutoff, cutoff),
            Application.deleted_at.is_(None),
        )
        prev_total = (await self.db.execute(prev_stmt)).scalar() or 1
        trend_pct = round(((period_total - prev_total) / max(prev_total, 1)) * 100, 1)

        return {
            "total_applications": total,
            "period_applications": period_total,
            "average_score": round(float(avg_score), 1),
            "active_jobs": active_jobs,
            "status_distribution": status_dist,
            "period_days": days,
            "trend_percent": trend_pct,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Hiring Funnel
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_hiring_funnel(self, job_id: Optional[int] = None) -> Dict[str, Any]:
        """Funnel: Applied → Screened → Interviewed → Offered → Hired."""
        base_filter = [Application.org_id == self.org_id, Application.deleted_at.is_(None)]
        if job_id:
            base_filter.append(Application.job_id == job_id)

        applied = (await self.db.execute(
            select(func.count(Application.id)).where(*base_filter)
        )).scalar() or 0

        screened = (await self.db.execute(
            select(func.count(Application.id)).where(
                *base_filter,
                Application.score.isnot(None),
            )
        )).scalar() or 0

        # Scored >= 70 = interviewed/advanced
        advanced = (await self.db.execute(
            select(func.count(Application.id)).where(
                *base_filter,
                Application.score >= 70,
            )
        )).scalar() or 0

        hired = (await self.db.execute(
            select(func.count(Application.id)).where(
                *base_filter,
                Application.status.in_(["HIRED", "OFFER_ACCEPTED"]),
            )
        )).scalar() or 0

        return {
            "stages": [
                {"name": "Applied", "count": applied},
                {"name": "Screened", "count": screened},
                {"name": "Advanced", "count": advanced},
                {"name": "Hired", "count": hired},
            ],
            "conversion_rate": round(hired / max(applied, 1) * 100, 1),
            "screening_pass_rate": round(advanced / max(screened, 1) * 100, 1),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Score Distribution
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_score_distribution(self, job_id: Optional[int] = None) -> List[Dict]:
        """Score buckets for histogram."""
        filters = [Application.org_id == self.org_id, Application.score.isnot(None), Application.deleted_at.is_(None)]
        if job_id:
            filters.append(Application.job_id == job_id)

        rows = (await self.db.execute(
            select(Application.score).where(*filters)
        )).scalars().all()

        buckets = Counter()
        for s in rows:
            bucket = min(int(float(s) // 10) * 10, 90)
            buckets[f"{bucket}-{bucket+10}"] += 1

        return [{"range": k, "count": v} for k, v in sorted(buckets.items())]

    # ═══════════════════════════════════════════════════════════════════════════
    # Time-to-Hire
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_time_to_hire(self) -> Dict[str, Any]:
        """Average days from application to hire."""
        rows = (await self.db.execute(
            select(
                func.avg(
                    func.extract('epoch', Application.updated_at - Application.created_at) / 86400
                )
            ).where(
                Application.org_id == self.org_id,
                Application.status.in_(["HIRED", "OFFER_ACCEPTED"]),
                Application.deleted_at.is_(None),
            )
        )).scalar()

        avg_days = round(float(rows or 0), 1)

        # By job
        job_rows = (await self.db.execute(
            select(
                JobPosting.title,
                func.avg(
                    func.extract('epoch', Application.updated_at - Application.created_at) / 86400
                )
            ).join(Application, Application.job_id == JobPosting.id).where(
                Application.org_id == self.org_id,
                Application.status.in_(["HIRED", "OFFER_ACCEPTED"]),
                Application.deleted_at.is_(None),
            ).group_by(JobPosting.id, JobPosting.title).order_by(func.avg(
                func.extract('epoch', Application.updated_at - Application.created_at) / 86400
            ).asc()).limit(10)
        )).all()

        return {
            "average_days": avg_days,
            "by_job": [{"job": r[0], "days": round(float(r[1]), 1)} for r in job_rows],
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Skill Trends
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_skill_trends(self) -> Dict[str, Any]:
        """Most in-demand skills across jobs, and skills candidates are bringing."""
        # Job demand
        jobs = (await self.db.execute(
            select(JobPosting.required_skills).where(
                JobPosting.org_id == self.org_id,
                JobPosting.deleted_at.is_(None),
            )
        )).scalars().all()

        demand = Counter()
        for skills in jobs:
            if isinstance(skills, list):
                for s in skills:
                    demand[str(s).lower().strip()] += 1
            elif isinstance(skills, str):
                demand[skills.lower().strip()] += 1

        # Candidate supply
        candidates = (await self.db.execute(
            select(Candidate.parsed_json).where(
                Candidate.org_id == self.org_id,
                Candidate.deleted_at.is_(None),
            )
        )).scalars().all()

        supply = Counter()
        for parsed in candidates:
            if isinstance(parsed, dict):
                for s in (parsed.get("skills") or []):
                    supply[str(s).lower().strip()] += 1

        # Gap analysis
        gaps = []
        for skill, demand_count in demand.most_common(20):
            supply_count = supply.get(skill, 0)
            gap_ratio = round((demand_count - supply_count) / max(demand_count, 1) * 100, 1)
            gaps.append({
                "skill": skill,
                "demand": demand_count,
                "supply": supply_count,
                "gap_percent": gap_ratio,
            })

        return {
            "top_demand": [{"skill": k, "count": v} for k, v in demand.most_common(15)],
            "top_supply": [{"skill": k, "count": v} for k, v in supply.most_common(15)],
            "skill_gaps": sorted(gaps, key=lambda x: x["gap_percent"], reverse=True)[:10],
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Recruiter Analytics
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_recruiter_analytics(self) -> List[Dict]:
        """Performance metrics per recruiter (via audit logs)."""
        rows = (await self.db.execute(
            select(
                User.id, User.email,
                func.count(AuditLog.id).label("actions"),
                func.max(AuditLog.created_at).label("last_active"),
            ).join(AuditLog, AuditLog.user_id == User.id).where(
                User.org_id == self.org_id,
                AuditLog.created_at >= datetime.now(timezone.utc) - timedelta(days=30),
            ).group_by(User.id, User.email).order_by(func.count(AuditLog.id).desc())
        )).all()

        return [
            {
                "user_id": r[0],
                "email": r[1][:3] + "***",  # Masked for privacy
                "actions": r[2],
                "last_active": r[3].isoformat() if r[3] else None,
            }
            for r in rows
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # University / Education Analytics
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_university_analytics(self) -> Dict[str, Any]:
        """Top schools and degrees in candidate pool."""
        candidates = (await self.db.execute(
            select(Candidate.parsed_json, Application.score).join(
                Application, Application.candidate_id == Candidate.id
            ).where(
                Candidate.org_id == self.org_id,
                Candidate.deleted_at.is_(None),
                Application.score.isnot(None),
            )
        )).all()

        schools = Counter()
        school_scores: Dict[str, list] = defaultdict(list)
        degrees = Counter()

        for parsed, score in candidates:
            if isinstance(parsed, dict):
                for edu in (parsed.get("education") or []):
                    if isinstance(edu, dict):
                        school = edu.get("school", "").strip()
                        degree = edu.get("degree", "").strip()
                        if school:
                            schools[school] += 1
                            school_scores[school].append(float(score))
                        if degree:
                            degrees[degree] += 1

        top_schools = []
        for school, count in schools.most_common(10):
            scores_list = school_scores.get(school, [0])
            avg = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0
            top_schools.append({"school": school, "candidates": count, "avg_score": avg})

        return {
            "top_schools": top_schools,
            "top_degrees": [{"degree": k, "count": v} for k, v in degrees.most_common(10)],
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Country / Location Analytics
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_country_analytics(self) -> Dict[str, Any]:
        """Geographic distribution of candidates."""
        candidates = (await self.db.execute(
            select(Candidate.parsed_json).where(
                Candidate.org_id == self.org_id,
                Candidate.deleted_at.is_(None),
            )
        )).scalars().all()

        locations = Counter()
        for parsed in candidates:
            if isinstance(parsed, dict):
                loc = parsed.get("location", "")
                if loc:
                    # Try to extract country (last part after comma)
                    parts = [p.strip() for p in loc.split(",")]
                    country = parts[-1] if len(parts) > 1 else loc
                    locations[country] += 1
                else:
                    locations["Unknown"] += 1

        return {
            "top_locations": [
                {"location": k, "count": v}
                for k, v in locations.most_common(20)
            ],
            "total_locations": len(locations),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Diversity Metrics
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_diversity_metrics(self) -> Dict[str, Any]:
        """Bias detection results and score fairness."""
        # Bias flags from screening
        flags = (await self.db.execute(
            select(ScreeningResult.bias_flags).join(
                Application, ScreeningResult.application_id == Application.id
            ).where(Application.org_id == self.org_id)
        )).scalars().all()

        flag_counter = Counter()
        for f in flags:
            if isinstance(f, dict):
                for k in f:
                    flag_counter[k] += 1

        # Score distribution analysis
        scores = (await self.db.execute(
            select(Application.score).where(
                Application.org_id == self.org_id,
                Application.score.isnot(None),
                Application.deleted_at.is_(None),
            )
        )).scalars().all()

        score_list = [float(s) for s in scores if s is not None]
        score_list.sort()

        return {
            "bias_flags": dict(flag_counter),
            "total_flags": sum(flag_counter.values()),
            "score_percentiles": {
                "p25": score_list[len(score_list)//4] if len(score_list) >= 4 else 0,
                "p50": score_list[len(score_list)//2] if len(score_list) >= 2 else 0,
                "p75": score_list[3*len(score_list)//4] if len(score_list) >= 4 else 0,
                "p90": score_list[9*len(score_list)//10] if len(score_list) >= 10 else 0,
            },
            "score_std_dev": round(_stddev(score_list), 2) if score_list else 0,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Trends / Volume Over Time
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_volume_trends(self, days: int = 30) -> List[Dict]:
        """Daily application volume for line chart."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (await self.db.execute(
            select(
                func.date(Application.created_at).label("day"),
                func.count(Application.id).label("count"),
            ).where(
                Application.org_id == self.org_id,
                Application.created_at >= cutoff,
                Application.deleted_at.is_(None),
            ).group_by(func.date(Application.created_at)).order_by("day")
        )).all()

        # Fill in missing days
        result = []
        for i in range(days):
            date = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()
            count = next((r[1] for r in rows if r[0] == date), 0)
            result.append({"date": date.isoformat(), "count": count})
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Export
    # ═══════════════════════════════════════════════════════════════════════════

    async def export_analytics_csv(self) -> str:
        """Generate CSV export of all analytics data."""
        import csv, io
        output = io.StringIO()
        writer = csv.writer(output)

        overview = await self.get_overview()
        writer.writerow(["Metric", "Value"])
        for k, v in overview.items():
            if not isinstance(v, dict):
                writer.writerow([k, v])

        funnel = await self.get_hiring_funnel()
        writer.writerow([])
        writer.writerow(["Stage", "Count"])
        for s in funnel["stages"]:
            writer.writerow([s["name"], s["count"]])

        skills = await self.get_skill_trends()
        writer.writerow([])
        writer.writerow(["Skill", "Demand", "Supply", "Gap %"])
        for g in skills.get("skill_gaps", []):
            writer.writerow([g["skill"], g["demand"], g["supply"], g["gap_percent"]])

        output.seek(0)
        return output.getvalue()


def _stddev(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5
