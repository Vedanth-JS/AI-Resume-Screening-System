from typing import Dict, Any
from ..services.llm_service import _call_model, _parse_json_response

class FeedbackService:
    @staticmethod
    async def generate_candidate_feedback(resume_text: str, scoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates personalized improvement report using Gemini.
        """
        prompt = f"""
        You are a career coach and resume expert. Based on the candidate's resume and the ATS scoring result, 
        generate a supportive and professional feedback report.
        
        Resume Content: {resume_text[:2000]}
        Scoring Details: {scoring_result}
        
        Return ONLY a JSON object with these sections:
        {{
          "strengths": ["list of strings"],
          "gaps": ["list of strings"],
          "recommended_skills_to_add": ["list of strings"],
          "resume_format_tips": ["list of strings"],
          "overall_verdict": "string"
        }}
        """
        raw_resp = _call_model(prompt, context="FeedbackService")
        return _parse_json_response(raw_resp) or {
            "strengths": [],
            "gaps": ["Technical analysis failed."],
            "recommended_skills": [],
            "resume_format_tips": ["Ensure your resume is in a clean, parsable PDF format."],
            "overall_verdict": "Inconclusive"
        }
