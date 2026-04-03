import json
import re
from typing import Any, Dict, Optional
from .base import BaseAgent
from ..services.llm_service import _call_model, _parse_json_response

class ResumeParserAgent(BaseAgent):
    def __init__(self):
        super().__init__("ResumeParserAgent")

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {"raw_text": "..."}
        Output: Structured JSON
        """
        raw_text = input_data.get("raw_text", "")
        if not raw_text:
            return {"error": "No raw text provided"}

        prompt = f"""
        You are an expert resume parser. Extract structured information from the resume text below.
        Return ONLY a valid JSON object with these exact keys:
        {{
          "name": "Full Name",
          "email": "email@example.com",
          "phone": "string",
          "education": [{{"school": "string", "degree": "string", "year": "string"}}],
          "experience": [{{"company": "string", "role": "string", "duration": "string", "years": 0.0}}],
          "skills": ["skill1", "skill2"],
          "certifications": ["cert1"],
          "projects": [{{"title": "string", "description": "string"}}],
          "total_years_exp": 0.0
        }}
        Resume Text:
        {raw_text[:6000]}
        """
        
        raw_resp = _call_model(prompt, context="ResumeParserAgent")
        parsed = _parse_json_response(raw_resp)
        
        if not parsed or not parsed.get("name") or parsed.get("name") == "string":
            # Fallback to regex extraction if LLM fails or returns placeholder
            parsed = self._fallback_extraction(raw_text, parsed or {})
            parsed["extraction_method"] = "hybrid_fallback"
        else:
            parsed["extraction_method"] = "llm"
            
        return parsed

    def _fallback_extraction(self, text: str, existing: Dict[str, Any]) -> Dict[str, Any]:
        """Regex-based fallback for critical fields."""
        # Email pattern
        email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        # Phone pattern (simplified)
        phone_match = re.search(r"(\+?\d[\d\s-]{7,}\d)", text)
        
        # Name heuristic (first line usually)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        name = lines[0] if lines else "Unknown Candidate"
        if len(name) > 50: name = name[:50]

        return {
            "name": existing.get("name") or name,
            "email": existing.get("email") or (email_match.group(0) if email_match else None),
            "phone": existing.get("phone") or (phone_match.group(0) if phone_match else None),
            "education": existing.get("education", []),
            "experience": existing.get("experience", []),
            "skills": existing.get("skills", []),
            "certifications": existing.get("certifications", []),
            "projects": existing.get("projects", []),
            "total_years_exp": existing.get("total_years_exp", 0.0)
        }
