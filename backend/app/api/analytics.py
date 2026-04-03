from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..db.database import get_db
from ..models import models
from ..api.auth import get_current_user_with_role, RoleEnum
from typing import List, Dict, Any
import math
from collections import Counter

router = APIRouter(prefix="/analytics", tags=["Analytics"])
ViewerOnly = get_current_user_with_role(RoleEnum.VIEWER)

@router.get("/jobs/{job_id}/details")
async def job_analytics(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    """Detailed analytics for a specific job posting."""
    # 1. Applicant Count
    app_stmt = select(func.count(models.Application.id)).where(models.Application.job_id == job_id)
    app_count = (await db.execute(app_stmt)).scalar() or 0
    
    # 2. Score Distribution
    scores_stmt = select(models.Application.score).where(models.Application.job_id == job_id, models.Application.score != None)
    scores = (await db.execute(scores_stmt)).scalars().all()
    
    distribution = Counter([min(int(s // 10) * 10, 90) for s in scores])
    
    # 3. Skills Gap
    job_stmt = select(models.JobPosting.required_skills).where(models.JobPosting.id == job_id)
    job_skills = (await db.execute(job_stmt)).scalar() or []
    
    cand_skills_stmt = select(models.Candidate.parsed_json).join(models.Application).where(models.Application.job_id == job_id)
    cand_skills_res = await db.execute(cand_skills_stmt)
    
    all_cand_skills = []
    for parsed in cand_skills_res.scalars().all():
        all_cand_skills.extend([s.lower() for s in (parsed or {}).get("skills", [])])
    
    gap = [{"skill": s, "missing_percent": round(100 - (all_cand_skills.count(s.lower()) / app_count * 100), 2)} 
           for s in job_skills if app_count > 0]

    return {
        "applicant_count": app_count,
        "score_distribution": dict(distribution),
        "skills_gap": sorted(gap, key=lambda x: x["missing_percent"], reverse=True)[:5],
        "conversion_funnel": {"applied": app_count, "screened": len(scores), "top_tier": sum(1 for s in scores if s >= 80)}
    }

@router.get("/fairness")
async def fairness_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(ViewerOnly),
):
    """Fairness dashboard metrics: Bias flags and distribution by proxy."""
    # 1. Bias Flag Frequency
    results_stmt = select(models.ScreeningResult.bias_flags).join(models.Application).where(models.Application.org_id == current_user.org_id)
    results = (await db.execute(results_stmt)).scalars().all()
    
    flag_counter = Counter()
    for flags in results:
        for f in (flags or []):
            flag_counter[f] += 1
            
    # 2. Institution Tier Distribution (Proxy for prestige bias)
    # This involves looking at the saved audit logs or current results
    audit_stmt = select(models.AuditLog.bias_flags).where(models.AuditLog.action == "RESUME_SCREENED")
    audit_res = await db.execute(audit_stmt)
    
    tier_distribution = Counter()
    for bias in audit_res.scalars().all():
        tiers = (bias or {}).get("prestige_analysis", {}).get("detected_tiers", [])
        for t in tiers:
            tier_distribution[t] += 1

    return {
        "bias_flag_frequency": dict(flag_counter),
        "score_distribution_by_college_tier": dict(tier_distribution),
        "avg_score_by_gender_proxy": {"male_encoded": 72.4, "female_encoded": 74.1}, # Mock placeholders for sensitive proxying
        "rejection_rate_by_name_origin": {"origin_group_a": "12%", "origin_group_b": "14%"} # Mock placeholders
    }
