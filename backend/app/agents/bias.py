from typing import Any, Dict, List
from .base import BaseAgent
from ..services.llm_service import _call_model, _parse_json_response

class BiasDetectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("BiasDetectorAgent")

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        resume_text = input_data.get("resume_text", "")
        parsed_resume = input_data.get("parsed_resume", {})

        prompt = f"""
        You are a hiring bias detection specialist. Analyze the resume content for unconscious bias.
        Resume Text: {resume_text[:4000]}
        Extracted Data: {parsed_resume}

        Identify:
        1. Gender bias indicators (pronouns, gendered activities).
        2. Age bias (graduation years, long experience).
        3. Name-based bias (socio-economic or ethnic associations).
        4. School prestige bias (ivy league, etc).

        Return ONLY a JSON object:
        {{
          "bias_flags": ["list of strings"],
          "bias_risk_level": "LOW | MED | HIGH",
          "flagged_phrases": ["list of strings"],
          "recommendation": "string"
        }}
        """
        raw_resp = await _call_model(prompt, context="BiasDetectorAgent")
        return _parse_json_response(raw_resp) or {
            "bias_flags": [],
            "bias_risk_level": "LOW",
            "flagged_phrases": [],
            "recommendation": "Could not perform LLM bias analysis."
        }
