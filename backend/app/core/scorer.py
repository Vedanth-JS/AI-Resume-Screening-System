"""
Multi-component ATS Scoring Engine (v3.0)
────────────────────────────────────────
1. Keyword Match    (30%) — Taxonomy-aware + rapidfuzz fuzzy
2. Semantic Score   (35%) — Gemini 768d embedding cosine similarity
3. Format Score     (15%) — headings, bullets, contact info, dates
4. Section Score    (10%) — presence of key resume sections
5. Experience Match (10%) — years comparison with diminishing returns

All scores are 0–100. Weights are configurable via settings.
"""
import re
from typing import Dict, Any, List, Tuple, Optional
from rapidfuzz import fuzz
from ..core.config import settings
from ..core.logger import log

# ─── SentenceTransformer fallback (lazy-loaded, may not be installed) ────────
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _ST_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    st_util = None
    _ST_AVAILABLE = False

_st_model = None


def _get_st_model():
    global _st_model
    if not _ST_AVAILABLE:
        return None
    if _st_model is None:
        try:
            _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _st_model = None
    return _st_model

# ─── Regex patterns ──────────────────────────────────────────────────────────
_DATE_PATTERN   = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b|\b\d{4}\s*[-–]\s*(\d{4}|present|current)\b", re.I)
_BULLET_PATTERN = re.compile(r"^[\s]*[•\-\*▶►✓→]\s+", re.MULTILINE)
_HEADING_PATTERN = re.compile(r"^[A-Z][A-Z\s&]{3,}$", re.MULTILINE)
_EMAIL_PATTERN  = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_PATTERN  = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
_URL_PATTERN    = re.compile(r"(linkedin|github|portfolio|website)[\./]", re.I)

_EXPECTED_SECTIONS = {
    "contact":        ["contact", "email", "phone"],
    "summary":        ["summary", "objective", "profile", "about"],
    "education":      ["education", "academic", "university", "degree"],
    "experience":     ["experience", "work", "employment", "internship"],
    "skills":         ["skills", "technical skills", "competencies", "technologies"],
    "projects":       ["projects", "portfolio", "personal projects"],
    "certifications": ["certifications", "certificates", "awards", "achievements"],
}


class Scorer:
    # ═══════════════════════════════════════════════════════════════════════════
    # 1. Keyword Match (0–100)
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def keyword_score(resume_text: str, jd_keywords: List[str]) -> Dict[str, Any]:
        if not jd_keywords:
            return {"score": 1.0, "matched": [], "missing": [], "synonym_matches": [], "fuzzy_details": []}

        # Step 1: taxonomy-aware scoring
        try:
            from ..core.skill_synonyms import enrich_keyword_score
            result = enrich_keyword_score(resume_text, jd_keywords)
        except Exception as e:
            log.warning("keyword_score.synonym_fallback", error=str(e))
            result = None

        if result is None:
            result = {"fuzzy_details": [], "matched": [], "missing": list(jd_keywords), "synonym_matches": []}
            for kw in jd_keywords:
                result["fuzzy_details"].append({"keyword": kw, "score": 0.0, "match_type": "none"})

        # Step 2: fuzzy fallback for unmatched keywords
        resume_lower = resume_text.lower()
        for detail in result["fuzzy_details"]:
            if detail["match_type"] == "none":
                kw = detail["keyword"]
                words = resume_lower.split()
                best_ratio = 0
                # sliding window for efficiency
                chunk_size = 40
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i : i + chunk_size])
                    ratio = fuzz.partial_ratio(kw.lower(), chunk)
                    best_ratio = max(best_ratio, ratio)
                if best_ratio >= 70:
                    credit = round(best_ratio / 100, 3)
                    detail["match_type"] = f"fuzzy:{best_ratio}"
                    detail["score"] = credit
                    if kw in result["missing"]:
                        result["missing"].remove(kw)
                        result["matched"].append(kw)
                    result["synonym_matches"].append(
                        {"keyword": kw, "matched_via": f"fuzzy:{best_ratio}", "credit": credit}
                    )

        # Step 3: recompute weighted score
        total_credit = sum(d["score"] for d in result["fuzzy_details"])
        result["score"] = round(total_credit / len(jd_keywords), 3)
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. Semantic Score (0–100) via Gemini embeddings
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    async def semantic_score_gemini(resume_text: str, jd_text: str) -> float:
        """Use Gemini text-embedding-004 (768 dimensions) for semantic similarity."""
        if not resume_text or not jd_text:
            return 0.0
        try:
            from ..services.llm_service import get_embedding
            resume_vec = await get_embedding(resume_text[:3000])
            jd_vec = await get_embedding(jd_text[:3000])
            if not resume_vec or not jd_vec:
                return 0.0
            dot = sum(a * b for a, b in zip(resume_vec, jd_vec))
            norm_a = sum(a * a for a in resume_vec) ** 0.5
            norm_b = sum(b * b for b in jd_vec) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return round(float(dot / (norm_a * norm_b)) * 100, 2)
        except Exception as e:
            log.warning("semantic_score_gemini.error", error=str(e))
            return 0.0

    @staticmethod
    def semantic_score_st(resume_text: str, jd_text: str) -> float:
        """SentenceTransformer fallback (all-MiniLM-L6-v2, 384 dimensions)."""
        if not _ST_AVAILABLE or not resume_text or not jd_text:
            return 0.0
        try:
            model = _get_st_model()
            if model is None:
                return 0.0
            emb1 = model.encode(resume_text[:3000], convert_to_tensor=True)
            emb2 = model.encode(jd_text[:3000], convert_to_tensor=True)
            return round(float(st_util.cos_sim(emb1, emb2)[0][0]) * 100, 2)
        except Exception as e:
            log.warning("semantic_score_st.error", error=str(e))
            return 0.0

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. Format Score (0–100)
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def format_score(resume_text: str) -> Dict[str, Any]:
        checks = {
            "has_email":    bool(_EMAIL_PATTERN.search(resume_text)),
            "has_phone":    bool(_PHONE_PATTERN.search(resume_text)),
            "has_url":      bool(_URL_PATTERN.search(resume_text)),
            "has_bullets":  bool(_BULLET_PATTERN.search(resume_text)),
            "has_dates":    bool(_DATE_PATTERN.search(resume_text)),
            "has_headings": bool(_HEADING_PATTERN.search(resume_text)),
            "reasonable_len": 200 <= len(resume_text.split()) <= 1500,
        }
        passed = sum(checks.values())
        raw = passed / len(checks)
        suggestions = []
        if not checks["has_email"]:    suggestions.append("Add a professional email address.")
        if not checks["has_phone"]:    suggestions.append("Include a phone number.")
        if not checks["has_url"]:      suggestions.append("Add a LinkedIn or GitHub URL.")
        if not checks["has_bullets"]:  suggestions.append("Use bullet points to list achievements.")
        if not checks["has_dates"]:    suggestions.append("Include date ranges for each role.")
        if not checks["has_headings"]: suggestions.append("Use clear section headings (EDUCATION, EXPERIENCE, SKILLS).")
        if not checks["reasonable_len"]:
            wc = len(resume_text.split())
            suggestions.append(
                "Resume is too short — add more detail." if wc < 200
                else "Resume is too long — trim to 1-2 pages."
            )
        return {"score": round(raw * 100, 2), "checks": checks, "suggestions": suggestions}

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. Section Completeness (0–100)
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def section_score(resume_text: str) -> Dict[str, Any]:
        text_lower = resume_text.lower()
        found, missing = {}, []
        for group, keywords in _EXPECTED_SECTIONS.items():
            hit = any(kw in text_lower for kw in keywords)
            found[group] = hit
            if not hit:
                missing.append(group)
        raw = sum(found.values()) / len(_EXPECTED_SECTIONS)
        suggestions = [f"Add a '{s.title()}' section to your resume." for s in missing]
        return {"score": round(raw * 100, 2), "sections_found": found, "missing_sections": missing, "suggestions": suggestions}

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. Experience Match (0–100)
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def experience_score(candidate_years: float, required_years: int) -> float:
        """
        Diminishing returns beyond the requirement.
        0        → 0
        req      → 70
        req+2    → 90
        req+5+   → 100
        """
        if required_years <= 0:
            return 80.0  # no requirement specified → assume adequate
        ratio = candidate_years / required_years
        if ratio >= 1.0:
            # Sigmoid-like curve: 70 + 30 * (1 - e^(-k*(ratio-1)))
            import math
            bonus = 30 * (1 - math.exp(-1.5 * (ratio - 1)))
            return round(min(70.0 + bonus, 100.0), 2)
        else:
            return round(ratio * 70.0, 2)

    # ═══════════════════════════════════════════════════════════════════════════
    # Composite Score
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def compute_full_score(
        resume_text: str,
        jd_text: str,
        jd_keywords: List[str],
        candidate_years: float = 0,
        required_years: int = 0,
        semantic_score_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compute all 5 components and weighted total.
        Setting `semantic_score_override` skips ST fallback (used when Gemini
        embeddings have already been computed externally).
        """
        kw  = Scorer.keyword_score(resume_text, jd_keywords)
        fmt = Scorer.format_score(resume_text)
        sec = Scorer.section_score(resume_text)
        exp = Scorer.experience_score(candidate_years, required_years)

        # Semantic: use override if provided, else try SentenceTransformer
        if semantic_score_override is not None:
            sem = semantic_score_override
        else:
            sem = Scorer.semantic_score_st(resume_text, jd_text)

        w = settings
        overall = (
            (kw["score"] * 100) * w.WEIGHT_KEYWORD +
            sem          * w.WEIGHT_SEMANTIC  +
            fmt["score"] * w.WEIGHT_FORMAT    +
            sec["score"] * w.WEIGHT_SECTION   +
            exp * 0.10   # experience weight
        )

        # Normalise so weights always sum to their intended proportion
        total_weight = w.WEIGHT_KEYWORD + w.WEIGHT_SEMANTIC + w.WEIGHT_FORMAT + w.WEIGHT_SECTION + 0.10
        overall = (overall / total_weight) if total_weight > 0 else overall

        all_suggestions = fmt["suggestions"] + sec["suggestions"]
        if kw["missing"]:
            all_suggestions.append(
                f"Missing keywords from JD: {', '.join(kw['missing'][:5])}. "
                "Incorporate them naturally into your experience descriptions."
            )
        suggestions = list(dict.fromkeys(all_suggestions))[:5]

        return {
            "overall_score":    round(overall, 2),
            "keyword_score":    kw["score"],
            "semantic_score":   sem,
            "format_score":     fmt["score"],
            "section_score":    sec["score"],
            "experience_score": exp,
            "keyword_detail":   kw,
            "format_detail":    fmt,
            "section_detail":   sec,
            "suggestions":      suggestions,
            "weights": {
                "keyword":    w.WEIGHT_KEYWORD,
                "semantic":   w.WEIGHT_SEMANTIC,
                "format":     w.WEIGHT_FORMAT,
                "section":    w.WEIGHT_SECTION,
                "experience": 0.10,
            },
        }

    @staticmethod
    def get_similarity(text1: str, text2: str) -> float:
        return Scorer.semantic_score_st(text1, text2)
