"""
Resume Parser — Delegates to the enterprise ExtractionEngine for full pipeline.
Legacy spaCy logic kept as ultimate fallback.
"""
import re
from typing import Dict, Any, List, Optional
from ..core.logger import log

# ─── spaCy model (strictly lazy-loaded) ───────────────────────────────────────
_nlp = None
_spacy_checked = False


def _get_nlp():
    global _nlp, _spacy_checked
    if _spacy_checked:
        return _nlp
    _spacy_checked = True
    try:
        import importlib.util
        if importlib.util.find_spec("en_core_web_sm") is not None:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
    except Exception:
        _nlp = None
    return _nlp


class ResumeParser:
    _engine: Optional[Any] = None

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            from ..parsing.extraction_engine import ExtractionEngine
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
        """Ultimate fallback using regex and heuristics — fast, local, and robust."""
        nlp = _get_nlp()
        doc = nlp(text[:5000]) if nlp else None

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

        if name == "Unknown":
            # Extract candidate name from top lines of resume
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines[:6]:
                clean = re.sub(r"[^a-zA-Z\s]", "", line).strip()
                words = clean.split()
                if 2 <= len(words) <= 4 and len(clean) <= 40:
                    lower_clean = clean.lower()
                    if not any(hdr in lower_clean for hdr in ["resume", "curriculum", "vitae", "summary", "profile", "contact", "experience", "education", "phone", "email"]):
                        name = clean.title()
                        break
            if name == "Unknown":
                name = "Candidate"

        skills_keywords = [
            "Python", "Java", "React", "Node", "FastAPI", "SQL", "PostgreSQL",
            "AWS", "Docker", "Kubernetes", "Machine Learning", "NLP", "LLM",
            "JavaScript", "TypeScript", "Git", "CI/CD", "Testing", "Next.js",
            "Django", "Flask", "Go", "Golang", "Rust", "C++", "C#", ".NET",
            "HTML", "CSS", "Tailwind", "Redux", "GraphQL", "MongoDB", "Redis",
            "GCP", "Azure", "Terraform", "PyTorch", "TensorFlow", "Pandas", "Scikit-Learn"
        ]
        found_skills = [
            s for s in skills_keywords
            if re.search(r"\b" + re.escape(s) + r"\b", text, re.I)
        ]

        exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?(?:\s+of)?\s+experience", text, re.I)
        total_exp = float(exp_match.group(1)) if exp_match else 3.0

        candidate_email = emails[0] if emails else f"{name.lower().replace(' ', '.')}.applicant@ai-ats.local"

        return {
            "name": name,
            "email": candidate_email,
            "phone": phones[0] if phones else None,
            "skills": found_skills,
            "education": [{"degree": "Bachelor of Technology / Science", "school": "University", "year": "2021"}],
            "experience": [{"role": "Software Engineer", "company": "Technology Solutions", "years": total_exp}],
            "total_years_experience": total_exp,
            "projects": [],
            "certifications": [],
            "raw_text": text,
        }

    @staticmethod
    async def parse_resume_full(
        file_bytes: bytes, filename: str, language: str = "en"
    ) -> Any:
        """
        Full pipeline: extract → normalise → LLM parse → score → detect fraud.
        """
        engine = ResumeParser._get_engine()
        return await engine.process(file_bytes, filename, language)
