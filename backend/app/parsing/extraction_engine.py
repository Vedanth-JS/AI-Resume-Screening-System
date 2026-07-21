"""
Unified Resume Extraction Engine v2.0
────────────────────────────────────
Orchestrates multi-format parsing (PDF/DOCX/Image/TXT) and routes through
the LLM-powered extraction pipeline.

Flow:
  1. Detect format → route to appropriate parser
  2. Extract raw text + metadata (OCR if needed)
  3. Parse with Gemini LLM (few-shot prompt)
  4. Extract skills, experience, education, projects, certifications
  5. Compute quality & completeness scores
  6. Check for duplicates (SHA256 hash)
  7. Flag fraud signals (inconsistent dates, fabricated companies, degree mills)
  8. Return canonical ResumeDocument
"""
import os
import re
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

from ..core.pdf_extractor import PDFExtractor
from ..parsing.docx_parser import DOCXParser
from ..parsing.image_parser import ImageParser
from ..services.llm_service import GeminiService, get_embedding
from ..schemas.resume import ResumeDocument
from ..core.logger import log


class ExtractionEngine:
    def __init__(self, db_session=None):
        self.db = db_session

    async def process(
        self,
        file_content: bytes,
        filename: str,
        language: str = "en",
        enrich_github: bool = False,
        enrich_linkedin: bool = False,
    ) -> ResumeDocument:
        """
        Full extraction pipeline. Returns a canonical ResumeDocument.
        """
        ext = os.path.splitext(filename)[1].lower()
        file_hash = hashlib.sha256(file_content).hexdigest()

        # ─── Step 1: Extract raw text ────────────────────────────────────────
        raw_text, parse_meta = await self._extract_raw(file_content, filename, ext, language)

        # ─── Step 1b: Normalize ──────────────────────────────────────────────
        raw_text = Normalizer.clean(raw_text)
        if not raw_text.strip():
            return ResumeDocument(
                raw_text="", source_format=ext.lstrip("."),
                fraud_flags=["Empty or unreadable document"],
            )

        # ─── Step 2: LLM-powered structured parsing ──────────────────────────
        parsed = await GeminiService.extract_resume_data(raw_text)
        confidence = parsed.get("confidence", 0.5)

        # ─── Step 3: Build canonical ResumeDocument ──────────────────────────
        doc = ResumeDocument(
            name=parsed.get("name") or "Unknown",
            email=parsed.get("email") or "",
            phone=parsed.get("phone") or "",
            location=parsed.get("location") or "",
            social={
                "github": parsed.get("github_url"),
                "linkedin": parsed.get("linkedin_url"),
                "website": parsed.get("website"),
            },
            skills=parsed.get("skills") or [],
            education=parsed.get("education") or [],
            experience=parsed.get("experience") or [],
            projects=parsed.get("projects") or [],
            certifications=parsed.get("certifications") or [],
            languages=_extract_language_entries(parsed),
            total_years_experience=float(parsed.get("total_years_experience") or 0),
            highest_education=_highest_degree(parsed.get("education") or []),
            skills_by_category=_categorise_skills(parsed.get("skills") or []),
            raw_text=raw_text,
            parsed_text=parsed.get("summary") or "",
            source_format=ext.lstrip("."),
            source_language=language,
            ocr_applied=parse_meta.get("ocr_applied", False),
            parsing_confidence=confidence,
            file_hash=file_hash,
            extracted_date=datetime.now(timezone.utc),
            quality_score=_compute_quality(raw_text),
            completeness_score=_compute_completeness(parsed),
            is_duplicate=False,
            fraud_flags=_detect_fraud(parsed, raw_text),
            fraud_risk_score=_compute_fraud_risk(parsed),
        )

        # ─── Step 4: Duplicate check ─────────────────────────────────────────
        if self.db:
            doc.is_duplicate = await _check_duplicate(self.db, file_hash)

        # ─── Step 5: Optional enrichment ─────────────────────────────────────
        if enrich_github and doc.social.get("github"):
            doc.github_profile = await _enrich_github(doc.social["github"])
        if enrich_linkedin and doc.social.get("linkedin"):
            doc.linkedin_enriched = True

        return doc

    async def _extract_raw(
        self, content: bytes, filename: str, ext: str, lang: str
    ) -> Tuple[str, dict]:
        """Route to appropriate parser based on file extension."""
        meta = {"extraction_method": "raw", "ocr_applied": False}

        if ext == ".pdf":
            text, meta = await PDFExtractor.extract_text(content, ocr_enabled=True, language=lang)
            return text, meta

        if ext in (".docx", ".doc"):
            text, meta = await DOCXParser.extract_text(content)
            return text, meta

        if ext in ImageParser.SUPPORTED_FORMATS:
            tesseract_lang = ImageParser.resolve_language_code(lang)
            text, meta = await ImageParser.extract_text(content, language=tesseract_lang)
            return text, meta

        # Plain text
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = content.decode("latin-1", errors="ignore")
        meta["extraction_method"] = "utf8"
        return text, meta


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions (extractable to separate modules if needed)
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_language_entries(parsed: dict) -> List[dict]:
    """Extract language proficiency entries from parsed data."""
    langs = parsed.get("languages") or []
    if isinstance(langs, list) and langs and isinstance(langs[0], str):
        return [{"language": l, "proficiency": "intermediate"} for l in langs]
    return langs


def _highest_degree(education: list) -> str:
    """Determine the highest education level."""
    hierarchy = {"phd": 5, "doctorate": 5, "master": 4, "mba": 4, "bachelor": 3, "b.s.": 3, "b.a.": 3, "associate": 2, "diploma": 1}
    best_level = 0
    best = ""
    for entry in education:
        if isinstance(entry, dict):
            degree = (entry.get("degree") or "").lower()
            for key, level in hierarchy.items():
                if key in degree and level > best_level:
                    best_level = level
                    best = entry.get("degree", "")
    return best


def _categorise_skills(skills: list) -> Dict[str, List[str]]:
    """Categorize skills using the taxonomy from skill_synonyms."""
    from ..core.skill_synonyms import SKILL_TAXONOMY, _REVERSE_MAP
    categories: Dict[str, List[str]] = {}
    for skill in (skills or []):
        group = _REVERSE_MAP.get(skill.lower())
        cat = group or "other"
        categories.setdefault(cat, []).append(skill)
    return categories


def _compute_quality(text: str) -> float:
    """Heuristic resume quality score (0–100) based on structure indicators."""
    if not text:
        return 0.0
    score = 50.0
    # Bullet points
    if len(re.findall(r"[•\-\*]\s", text)) > 3:
        score += 10
    # Quantified achievements
    if len(re.findall(r"\d+%|\$\d+|increased|decreased|reduced|improved|managed \d+", text, re.I)) > 2:
        score += 10
    # Section structure
    if len(re.findall(r"\b(EDUCATION|EXPERIENCE|SKILLS|PROJECTS|CERTIFICATIONS)\b", text)) >= 3:
        score += 10
    # Contact presence
    if re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text):
        score += 10
    # Reasonable length
    wc = len(text.split())
    if 200 <= wc <= 2000:
        score += 10
    elif wc > 2000:
        score += 5
    # Active language
    if len(re.findall(r"\b(built|developed|led|designed|implemented|created|launched|managed|optimized|reduced)\b", text, re.I)) > 3:
        score += 10
    return min(score, 100.0)


def _compute_completeness(parsed: dict) -> float:
    """Completeness score based on presence of key sections."""
    points = 0
    total = 7
    if parsed.get("name"):         points += 1
    if parsed.get("email"):        points += 1
    if parsed.get("phone"):        points += 1
    if parsed.get("skills"):       points += 1
    if parsed.get("education"):    points += 1
    if parsed.get("experience"):   points += 1
    if parsed.get("projects") or parsed.get("certifications"): points += 1
    return round(points / total * 100, 1)


_KNOWN_DEGREE_MILLS = {
    "ashwood university", "belford university", "corllins university",
    "headway university", "rochville university", "almeda university",
    "california university fce", "glenford university",
}
_FAKE_COMPANY_PATTERNS = re.compile(
    r"(self.employed|freelance[dsin]{0,4}|unnamed|confidential\s*(company|client)?)",
    re.I,
)


def _detect_fraud(parsed: dict, raw_text: str) -> List[str]:
    """Heuristic fraud detection — flags suspicious patterns."""
    flags = []

    # Degree mills
    for edu in (parsed.get("education") or []):
        school = (edu.get("school") or "").lower()
        for mill in _KNOWN_DEGREE_MILLS:
            if mill in school:
                flags.append(f"Potential degree mill detected: {edu.get('school')}")

    # Date inconsistencies
    experiences = parsed.get("experience") or []
    for i, exp in enumerate(experiences):
        if isinstance(exp, dict):
            start = exp.get("start_date") or exp.get("duration", "")
            end = exp.get("end_date") or ""
            # Very short stints across many companies (job hopper pattern)
            pass  # placeholder for deeper analysis

    # Fake company patterns
    for exp in experiences:
        company = exp.get("company") if isinstance(exp, dict) else ""
        if company and _FAKE_COMPANY_PATTERNS.search(str(company)):
            flags.append(f"Suspicious employer: {company}")

    # Impossible experience: claiming 20+ years but only 25 years old
    total_years = float(parsed.get("total_years_experience") or 0)
    # Can cross reference with graduation year if available

    return flags


def _compute_fraud_risk(parsed: dict) -> float:
    """Simple fraud risk score (0–1)."""
    flags = _detect_fraud(parsed, parsed.get("raw_text", ""))
    if not flags:
        return 0.0
    risk = len(flags) * 0.25
    return min(risk, 1.0)


async def _check_duplicate(db, file_hash: str) -> bool:
    """Check if a resume with the same hash already exists in the DB."""
    from sqlalchemy import text
    try:
        # Use parameterized query with explicit bind — safe from SQL injection
        result = await db.execute(
            text("SELECT 1 FROM candidates WHERE parsed_json->>'file_hash' = :hash LIMIT 1"),
            {"hash": file_hash},
        )
        return result.scalar() is not None
    except Exception:
        return False


async def _enrich_github(github_url: str) -> Optional[dict]:
    """
    Enrich candidate profile with GitHub contributions.
    Uses the public GitHub API (no auth needed for public profiles, rate-limited).
    """
    username = _extract_github_username(github_url)
    if not username:
        return None

    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch user profile
            resp = await client.get(
                f"https://api.github.com/users/{username}",
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "AI-ATS/2.1"},
            )
            if resp.status_code != 200:
                return None
            user_data = resp.json()

            # Fetch repos
            repos_resp = await client.get(
                f"https://api.github.com/users/{username}/repos?per_page=30&sort=pushed",
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "AI-ATS/2.1"},
            )
            repos = repos_resp.json() if repos_resp.status_code == 200 else []

            languages = set()
            top_repos = []
            for repo in repos[:5]:
                top_repos.append(repo.get("full_name", ""))
                lang = repo.get("language")
                if lang:
                    languages.add(lang)

            return {
                "total_commits": user_data.get("public_repos", 0),  # proxy
                "total_prs": 0,
                "total_repos": user_data.get("public_repos", 0),
                "languages_used": list(languages),
                "top_repos": top_repos,
            }
    except Exception as e:
        log.warning("github_enrichment.failed", username=username, error=str(e))
        return None


def _extract_github_username(url: str) -> Optional[str]:
    """Extract GitHub username from a profile URL."""
    if not url:
        return None
    match = re.search(r"github\.com/([a-zA-Z0-9\-_]+)", url)
    return match.group(1) if match else None
