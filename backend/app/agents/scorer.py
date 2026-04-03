import json
from typing import Any, Dict, List
from .base import BaseAgent
from ..services.llm_service import _call_model, _parse_json_response

class ScoringAgent(BaseAgent):
    def __init__(self):
        super().__init__("ScoringAgent")

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {
            "parser_data": {...},
            "matcher_data": {...},
            "bias_data": {...},
            "job_data": {...},
            "past_hires": ["hire1_summary", "hire2_summary", "hire3_summary"]
        }
        """
        parser = input_data.get("parser_data", {})
        matcher = input_data.get("matcher_data", {})
        bias = input_data.get("bias_data", {})
        job = input_data.get("job_data", {})
        past_hires = input_data.get("past_hires", [])
        
        context_str = "\n".join([f"- {h}" for h in past_hires]) if past_hires else "None"
        
        prompt = f"""
        You are the lead hiring decision agent. Synthesize the findings from multiple AI agents to provide a final hiring recommendation.
        
        Job Requirements: {json.dumps(job)}
        Candidate Parser Output: {json.dumps(parser)}
        Skill Matcher Output: {json.dumps(matcher)}
        Bias Detection Output: {json.dumps(bias)}
        
        Based on these successful past hires for similar roles:
        {context_str}
        
        Evaluate the candidate and return ONLY a JSON object:
        {{
          "overall_score": 0-100,
          "ats_score": 0-100,
          "cultural_fit_score": 0-100,
          "risk_score": 0-100,
          "hire_recommendation": "STRONG_YES | YES | MAYBE | NO",
          "reasoning": "A concise 3-4 sentence explanation of the final decision."
        }}
        """
        raw_resp = _call_model(prompt, context="ScoringAgent")
        return _parse_json_response(raw_resp) or {
            "overall_score": 0.0,
            "hire_recommendation": "NO",
            "reasoning": "Failed to generate AI scoring analysis."
        }
