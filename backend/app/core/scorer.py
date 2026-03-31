"""
4-Component ATS Scoring Engine
─────────────────────────────
1. Keyword Match   (30%) – rapidfuzz fuzzy matching of JD terms in resume
2. Semantic Score  (40%) – SentenceTransformer cosine similarity
3. Format Score    (15%) – headings, bullets, contact info, date formats
4. Section Score   (15%) – presence of key resume sections
"""
import re
from typing import Dict, Any, List, Tuple
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz, process as rf_process
from ..core.config import settings
from ..core.logger import log

# Load model once at module import — shared across all workers in the process
_model = SentenceTransformer("all-MiniLM-L6-v2")

# Resume sections we expect
_EXPECTED_SECTIONS = [
    "summary", "objective", "profile",
    "education", "academic",
    "experience", "work", "employment", "internship",
    "skills", "technical skills", "competencies",
    "projects", "portfolio",
    "certifications", "certificates", "awards",
    "contact", "email", "phone",
]

# Date pattern for format checks
_DATE_PATTERN = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b"
    r"|\b\d{4}\s*[-–]\s*(\d{4}|present|current)\b",
    re.IGNORECASE,
)

_BULLET_PATTERN = re.compile(r"^[\s]*[•\-\*▶►✓→]\s+", re.MULTILINE)
_HEADING_PATTERN = re.compile(r"^[A-Z][A-Z\s]{3,}$", re.MULTILINE)
_EMAIL_PATTERN   = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_PATTERN   = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
_URL_PATTERN     = re.compile(r"(linkedin|github|portfolio|website)[\./]", re.IGNORECASE)


class Scorer:
    # ─── 1. Keyword Match ────────────────────────────────────────────────────

    @staticmethod
    def keyword_score(resume_text: str, jd_keywords: List[str]) -> Dict[str, Any]:
        """
        For each JD keyword, use rapidfuzz to find the best fuzzy match in the
        resume. A match above threshold=75 counts as a hit.
        Returns score (0–1), matched list, missing list.
        """
        if not jd_keywords:
            return {"score": 1.0, "matched": [], "missing": [], "fuzzy_details": []}

        resume_lower = resume_text.lower()
        matched, missing, details = [], [], []

        for kw in jd_keywords:
            # Check exact first
            if kw.lower() in resume_lower:
                matched.append(kw)
                details.append({"keyword": kw, "ratio": 100, "match": "exact"})
                continue

            # Fuzzy check — search in 200-char windows of the resume
            best_ratio = 0
            words = resume_lower.split()
            for i in range(0, len(words), 30):
                chunk = " ".join(words[i : i + 30])
                ratio = fuzz.partial_ratio(kw.lower(), chunk)
                best_ratio = max(best_ratio, ratio)

            if best_ratio >= 75:
                matched.append(kw)
                details.append({"keyword": kw, "ratio": best_ratio, "match": "fuzzy"})
            else:
                missing.append(kw)
                details.append({"keyword": kw, "ratio": best_ratio, "match": "none"})

        score = len(matched) / len(jd_keywords) if jd_keywords else 1.0
        return {"score": round(score, 3), "matched": matched, "missing": missing, "fuzzy_details": details}

    # ─── 2. Semantic Score ───────────────────────────────────────────────────

    @staticmethod
    def semantic_score(resume_text: str, jd_text: str) -> float:
        """Cosine similarity between SentenceTransformer embeddings."""
        if not resume_text or not jd_text:
            return 0.0
        try:
            emb1 = _model.encode(resume_text[:3000], convert_to_tensor=True)
            emb2 = _model.encode(jd_text[:3000],    convert_to_tensor=True)
            return float(util.cos_sim(emb1, emb2)[0][0])
        except Exception as e:
            log.warning("semantic_score_error", error=str(e))
            return 0.0

    # ─── 3. Format Score ─────────────────────────────────────────────────────

    @staticmethod
    def format_score(resume_text: str) -> Dict[str, Any]:
        """
        Checks structural quality of the resume.
        Returns score (0–1) and a breakdown dict.
        """
        checks = {
            "has_email":     bool(_EMAIL_PATTERN.search(resume_text)),
            "has_phone":     bool(_PHONE_PATTERN.search(resume_text)),
            "has_url":       bool(_URL_PATTERN.search(resume_text)),
            "has_bullets":   bool(_BULLET_PATTERN.search(resume_text)),
            "has_dates":     bool(_DATE_PATTERN.search(resume_text)),
            "has_headings":  bool(_HEADING_PATTERN.search(resume_text)),
            "reasonable_len": 200 <= len(resume_text.split()) <= 1500,
        }
        passed = sum(checks.values())
        score = passed / len(checks)
        suggestions = []
        if not checks["has_email"]:
            suggestions.append("Add a professional email address.")
        if not checks["has_phone"]:
            suggestions.append("Include a phone number.")
        if not checks["has_url"]:
            suggestions.append("Add a LinkedIn or GitHub URL.")
        if not checks["has_bullets"]:
            suggestions.append("Use bullet points to list responsibilities and achievements.")
        if not checks["has_dates"]:
            suggestions.append("Include date ranges (e.g., 'Jun 2022 – Present') for each role.")
        if not checks["has_headings"]:
            suggestions.append("Use clear section headings (EDUCATION, EXPERIENCE, SKILLS).")
        if not checks["reasonable_len"]:
            wc = len(resume_text.split())
            if wc < 200:
                suggestions.append("Resume is too short. Add more detail about your experience.")
            else:
                suggestions.append("Resume is very long. Consider trimming to 1–2 pages.")

        return {"score": round(score, 3), "checks": checks, "suggestions": suggestions}

    # ─── 4. Section Completeness ─────────────────────────────────────────────

    @staticmethod
    def section_score(resume_text: str) -> Dict[str, Any]:
        """Check which expected sections are present."""
        text_lower = resume_text.lower()
        groups = {
            "contact":        ["contact", "email", "phone"],
            "summary":        ["summary", "objective", "profile", "about"],
            "education":      ["education", "academic", "university", "degree"],
            "experience":     ["experience", "work", "employment", "internship"],
            "skills":         ["skills", "technical skills", "competencies", "technologies"],
            "projects":       ["projects", "portfolio", "personal projects"],
            "certifications": ["certifications", "certificates", "awards", "achievements"],
        }
        found, missing = {}, []
        for group, keywords in groups.items():
            hit = any(kw in text_lower for kw in keywords)
            found[group] = hit
            if not hit:
                missing.append(group)

        score = sum(found.values()) / len(groups)
        suggestions = [f"Add a '{s.title()}' section to your resume." for s in missing]
        return {"score": round(score, 3), "sections_found": found, "missing_sections": missing, "suggestions": suggestions}

    # ─── Composite Score ─────────────────────────────────────────────────────

    @staticmethod
    def compute_full_score(
        resume_text: str,
        jd_text: str,
        jd_keywords: List[str],
    ) -> Dict[str, Any]:
        """
        Run all 4 components and return a unified breakdown.
        Weights are read from settings so they can be tuned via env vars.
        """
        kw    = Scorer.keyword_score(resume_text, jd_keywords)
        sem   = Scorer.semantic_score(resume_text, jd_text)
        fmt   = Scorer.format_score(resume_text)
        sec   = Scorer.section_score(resume_text)

        w = settings
        overall = (
            kw["score"]  * w.WEIGHT_KEYWORD  +
            sem          * w.WEIGHT_SEMANTIC  +
            fmt["score"] * w.WEIGHT_FORMAT    +
            sec["score"] * w.WEIGHT_SECTION
        )
        overall_pct = round(overall * 100, 2)

        # Improvement suggestions (deduplicated, top 5)
        all_suggestions = fmt["suggestions"] + sec["suggestions"]
        if kw["missing"]:
            all_suggestions.append(
                f"Missing keywords from JD: {', '.join(kw['missing'][:5])}. "
                "Incorporate them naturally into your experience descriptions."
            )
        suggestions = list(dict.fromkeys(all_suggestions))[:5]

        return {
            "overall_score":   overall_pct,
            "keyword_score":   round(kw["score"] * 100, 2),
            "semantic_score":  round(sem * 100, 2),
            "format_score":    round(fmt["score"] * 100, 2),
            "section_score":   round(sec["score"] * 100, 2),
            "keyword_detail":  kw,
            "format_detail":   fmt,
            "section_detail":  sec,
            "suggestions":     suggestions,
            "weights": {
                "keyword":  w.WEIGHT_KEYWORD,
                "semantic": w.WEIGHT_SEMANTIC,
                "format":   w.WEIGHT_FORMAT,
                "section":  w.WEIGHT_SECTION,
            },
        }

    # ─── Legacy compat (used by chatbot RAG) ────────────────────────────────

    @staticmethod
    def get_similarity(text1: str, text2: str) -> float:
        return Scorer.semantic_score(text1, text2)
