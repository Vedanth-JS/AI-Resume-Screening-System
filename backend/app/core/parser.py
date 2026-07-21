"""
Resume Parser — Delegates to the enterprise ExtractionEngine for full pipeline.
Legacy spaCy logic kept as ultimate fallback.
"""
import re
from typing import Dict, Any, List, Optional
from ..parsing.extraction_engine import ExtractionEngine
from ..schemas.resume import ResumeDocument
from ..core.logger import log

# ─── spaCy model (lazy load) ──────────────────────────────────────────────────
try:
    import spacy

    try:
        _nlp = spacy.load("en_core_web_sm")
    except Exception:
        _nlp = None
        log.warning("spacy_model_not_loaded", note="Resume parser using regex-only mode.")
except Exception:
    spacy = None
    _nlp = None
    log.warning("spacy_not_installed", note="Resume parser using regex-only mode.")


class ResumeParser:
    _engine: Optional[ExtractionEngine] = None

    @classmethod
    def _get_engine(cls) -> ExtractionEngine:
        if cls._engine is None:
            cls._engine = ExtractionEngine()
        return cls._engine

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """
        Quick synchronous extraction for backward compatibility.
        For full pipeline, use ExtractionEngine.process() instead.
        """
        import fitz
        import asyncio
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"

        if ext == "pdf":
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text

        if ext in ("docx", "doc"):
            try:
                from docx import Document as DocxDocument
                import io
                doc = DocxDocument(io.BytesIO(file_bytes))
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                pass

        return file_bytes.decode("utf-8", errors="ignore")

    @staticmethod
    def parse_resume_fallback(text: str) -> Dict[str, Any]:
        """Ultimate fallback using spaCy + regex — only used if LLM fails."""
        doc = _nlp(text[:5000]) if _nlp else None

        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone_pattern = r"(\+?\d[\d\s\-().]{7,}\d)"

        emails = re.findall(email_pattern, text)
        phones = re.findall(phone_pattern, text)

        name = "Unknown"
        if doc is not None:
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    name = ent.text
                    break

        skills_keywords = [
            "Python", "Java", "React", "Node", "FastAPI", "SQL", "PostgreSQL",
            "AWS", "Docker", "Kubernetes", "Machine Learning", "NLP", "LLM",
            "JavaScript", "TypeScript", "Git", "CI/CD", "Testing",
        ]
        found_skills = [s for s in skills_keywords if s.lower() in text.lower()]

        return {
            "name": name,
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
            "skills": found_skills,
            "education": [],
            "experience": [],
            "total_years_experience": 0.0,
            "projects": [],
            "certifications": [],
            "raw_text": text,
        }

    @staticmethod
    async def parse_resume_full(
        file_bytes: bytes, filename: str, language: str = "en"
    ) -> ResumeDocument:
        """
        Full pipeline: extract → normalise → LLM parse → score → detect fraud.
        """
        engine = ResumeParser._get_engine()
        return await engine.process(file_bytes, filename, language)
