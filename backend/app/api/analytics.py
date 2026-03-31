"""
Analytics overview endpoint — aggregates data from the DB for the dashboard.
GET /api/analytics/overview
"""
import math
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db.database import get_db
from ..models import models
from ..api.auth import get_current_user

router = APIRouter()


@router.get("/analytics/overview")
def analytics_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # ─── Core counts ────────────────────────────────────────────────────────
    total_candidates = db.query(func.count(models.Candidate.id)).scalar() or 0
    total_jobs       = db.query(func.count(models.JobPosting.id)).scalar() or 0
    all_scores       = db.query(models.ScreeningResult).all()

    avg_score = 0.0
    if all_scores:
        avg_score = round(sum(r.final_score for r in all_scores) / len(all_scores), 2)

    accept = sum(1 for r in all_scores if r.final_score >= 70)
    review = sum(1 for r in all_scores if 40 <= r.final_score < 70)
    reject = sum(1 for r in all_scores if r.final_score < 40)

    # ─── Score histogram (10 bins: 0-10, 10-20, ..., 90-100) ───────────────
    bins   = [f"{i*10}–{i*10+10}" for i in range(10)]
    counts = [0] * 10
    for r in all_scores:
        idx = min(int(r.final_score // 10), 9)
        counts[idx] += 1
    score_distribution = {"bins": bins, "counts": counts}

    # ─── Top skills (from parsed_json in candidates) ────────────────────────
    from collections import Counter
    skill_counter: Counter = Counter()
    candidates = db.query(models.Candidate).all()
    for c in candidates:
        parsed = c.parsed_json or {}
        for skill in parsed.get("skills", []):
            if isinstance(skill, str) and skill.strip():
                skill_counter[skill.strip().lower()] += 1
    top_skills = [{"skill": s, "count": c} for s, c in skill_counter.most_common(15)]

    # ─── Bias flags (count from bias_reports) ───────────────────────────────
    bias_reports = db.query(models.BiasReport).all()
    bias_gender   = sum(
        1 for b in bias_reports
        if (b.report_json or {}).get("gender_bias", {}).get("status") != "neutral"
    )
    bias_prestige = sum(
        1 for b in bias_reports
        if (b.report_json or {}).get("prestige_bias", {}).get("flag") is True
    )

    # ─── Processing time percentiles ────────────────────────────────────────
    times = sorted(
        r.processing_time_ms for r in all_scores
        if r.processing_time_ms and r.processing_time_ms > 0
    )
    def percentile(data, pct):
        if not data:
            return 0
        k = (len(data) - 1) * pct / 100
        f, c = math.floor(k), math.ceil(k)
        return data[f] if f == c else round(data[f] * (c - k) + data[c] * (k - f))

    processing_time = {
        "p50": percentile(times, 50),
        "p95": percentile(times, 95),
        "p99": percentile(times, 99),
        "sample_count": len(times),
    }

    # ─── Recent activity (last 15 events) ───────────────────────────────────
    events = (
        db.query(models.AnalyticsEvent)
        .order_by(models.AnalyticsEvent.created_at.desc())
        .limit(15)
        .all()
    )
    recent_activity = [
        {
            "event_type": e.event_type,
            "payload":    e.payload_json,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]

    # ─── 4-component breakdown averages ────────────────────────────────────
    def avg_field(field):
        vals = [getattr(r, field) for r in all_scores if getattr(r, field) is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    component_averages = {
        "keyword_avg":  avg_field("keyword_score"),
        "semantic_avg": avg_field("semantic_score"),
        "format_avg":   avg_field("format_score"),
        "section_avg":  avg_field("section_score"),
    }

    return {
        "total_candidates":    total_candidates,
        "total_jobs":          total_jobs,
        "total_screened":      len(all_scores),
        "avg_score":           avg_score,
        "score_breakdown":     {"accept": accept, "review": review, "reject": reject},
        "score_distribution":  score_distribution,
        "top_skills":          top_skills,
        "bias_flags":          {"gender": bias_gender, "prestige": bias_prestige},
        "processing_time":     processing_time,
        "component_averages":  component_averages,
        "recent_activity":     recent_activity,
    }
