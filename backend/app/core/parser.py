import spacy
import re
import fitz  # PyMuPDF
from typing import Dict, Any, List

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class ResumeParser:
    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        text = ""
        if filename.lower().endswith(".pdf"):
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text()
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
        return text

    @staticmethod
    def parse_resume_fallback(text: str) -> Dict[str, Any]:
        """Base extraction logic using spaCy/Regex if LLM fails or is disabled."""
        doc = nlp(text)
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{10})'
        
        emails = re.findall(email_pattern, text)
        phones = re.findall(phone_pattern, text)
        
        name = "Unknown"
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text
                break
        
        # Basic common skills list for fallback
        skills_keywords = [
            "Python", "Java", "React", "Node", "FastAPI", "SQL", "PostgreSQL", 
            "AWS", "Docker", "Kubernetes", "Machine Learning", "NLP", "LLM", 
            "JavaScript", "TypeScript", "Git", "CI/CD", "Testing"
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
            "raw_text": text
        }
