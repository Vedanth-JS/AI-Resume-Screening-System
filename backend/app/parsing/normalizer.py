"""
Resume Text Normalizer — Multilingual normalization, encoding repair, unicode cleanup.
"""
import re
import unicodedata
from typing import Optional

try:
    from ftfy import fix_text as _ftfy_fix
    _FTFY_AVAILABLE = True
except ImportError:
    _ftfy_fix = lambda x: x
    _FTFY_AVAILABLE = False

_EMAIL_CORRECTIONS = {
    "gmial.com": "gmail.com", "gmail.con": "gmail.com",
    "hotmail.con": "hotmail.com", "yaho.com": "yahoo.com",
    "outloo.com": "outlook.com", "icloud.con": "icloud.com",
    "protonmai.com": "protonmail.com",
}

_PHONE_CLEAN = re.compile(r"[\s\-\(\)\.\,\;\:\(\)\[\]\{\}]+")

_SECTION_HEADERS = [
    r"\b(EDUCATION|ACADEMIC|QUALIFICATIONS?)\b",
    r"\b(EXPERIENCE|WORK|EMPLOYMENT|INTERNSHIPS?|PROFESSIONAL)\b",
    r"\b(SKILLS?|TECHNICAL|COMPETENCIES|TECHNOLOGIES|TOOLS?|EXPERTISE)\b",
    r"\b(PROJECTS?|PORTFOLIO|PERSONAL\s*PROJECTS?)\b",
    r"\b(CERTIFICATIONS?|CERTIFICATES?|LICENSES?|CREDENTIALS?)\b",
    r"\b(CONTACT|PERSONAL|PROFILE|SUMMARY|OBJECTIVE|ABOUT)\b",
    r"\b(LANGUAGES?|AWARDS?|ACHIEVEMENTS?|HONORS?|PUBLICATIONS?)\b",
]


class Normalizer:
    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""
        try:
            text = _ftfy_fix(text)
        except Exception:
            pass
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"[\u200b\u200c\u200d\u2060\uFEFF]+", "", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {3,}", " ", text)
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"[•●○◦◉◆◇▪▫►▸✓✔☑☐□]", "•", text)
        text = text.replace("\t", " ")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        return text.strip()

    @staticmethod
    def normalise_email(email: str) -> Optional[str]:
        if not email:
            return None
        email = email.lower().strip()
        for wrong, correct in _EMAIL_CORRECTIONS.items():
            if email.endswith("@" + wrong):
                email = email.replace("@" + wrong, "@" + correct)
        if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
            return None
        return email

    @staticmethod
    def normalise_phone(phone: str) -> Optional[str]:
        if not phone:
            return None
        cleaned = _PHONE_CLEAN.sub("", phone)
        if cleaned.startswith("00") and len(cleaned) > 10:
            cleaned = "+" + cleaned[2:]
        elif not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        if len(cleaned) < 8:
            return None
        return cleaned

    @staticmethod
    def normalise_date(date_str: str) -> Optional[str]:
        if not date_str:
            return None
        try:
            from dateutil.parser import parse as _dateutil_parse
            dt = _dateutil_parse(date_str, fuzzy=True)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        return date_str

    @staticmethod
    def detect_language(text: str) -> str:
        if not text or len(text) < 50:
            return "en"
        try:
            from langdetect import detect
            return detect(text[:2000])
        except Exception:
            pass
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh"
        if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
            return "ja"
        if re.search(r"[\uac00-\ud7af]", text):
            return "ko"
        if re.search(r"[\u0600-\u06ff]", text):
            return "ar"
        if re.search(r"[\u0400-\u04ff]", text):
            return "ru"
        return "en"

    @staticmethod
    def extract_sections(text: str) -> dict:
        sections = {"header": "", "education": "", "experience": "", "skills": "",
                     "projects": "", "certifications": "", "contact": "", "other": ""}
        section_order = ["header", "contact", "summary", "education", "experience",
                         "skills", "projects", "certifications", "languages", "other"]
        current = "header"
        lines = text.split("\n")
        for line in lines:
            matched = None
            stripped = line.strip()
            for i, pattern in enumerate(_SECTION_HEADERS):
                if re.match(pattern, stripped, re.I):
                    matched = list(sections.keys())[i] if i < len(sections) else "other"
                    break
            if matched:
                current = matched
                continue
            sections[current] += line + "\n"
        return {k: v.strip() for k, v in sections.items() if v.strip()}
