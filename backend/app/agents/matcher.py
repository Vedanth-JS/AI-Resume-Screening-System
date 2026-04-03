import json
import numpy as np
from typing import Any, Dict, List
from .base import BaseAgent
from ..services.llm_service import get_embedding, _call_model, _parse_json_response

class SkillMatcherAgent(BaseAgent):
    def __init__(self):
        super().__init__("SkillMatcherAgent")

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {"resume": {...}, "job": {...}}
        """
        resume = input_data.get("resume", {})
        job = input_data.get("job", {})
        
        resume_skills = resume.get("skills", [])
        job_skills = job.get("required_skills", [])
        if isinstance(job_skills, dict): # if it's JSONB from DB
            job_skills = job_skills.get("must_have", []) + job_skills.get("nice_to_have", [])

        # 1. Cosine similarity on skill embeddings
        skill_score = await self._calculate_skill_similarity(resume_skills, job_skills)
        
        # 2. LLM-based seniority and experience gap analysis
        analysis_prompt = f"""
        Compare the candidate's experience against the job requirements.
        Candidate Experience (JSON): {json.dumps(resume.get('experience', []))}
        Job Requirements: {json.dumps(job)}
        
        Analyze:
        1. Matched skills vs Missing skills.
        2. Experience gap (in years).
        3. Seniority match (Junior/Mid/Senior).
        
        Return ONLY a JSON object:
        {{
          "matched_skills": ["list of strings"],
          "missing_skills": ["list of strings"],
          "experience_gap": "description of gap",
          "seniority_match": "Junior|Mid|Senior matches requirement? YES/NO/PARTIAL",
          "skill_analysis_score": 0.0-100.0
        }}
        """
        raw_analysis = _call_model(analysis_prompt, context="SkillMatcherAgent")
        analysis = _parse_json_response(raw_analysis) or {}
        
        return {
            "skill_score": round(skill_score * 100, 2),
            **analysis
        }

    async def _calculate_skill_similarity(self, resume_skills: List[str], job_skills: List[str]) -> float:
        if not resume_skills or not job_skills:
            return 0.0
            
        resume_text = ", ".join(resume_skills)
        job_text = ", ".join(job_skills)
        
        resume_emb = await get_embedding(resume_text)
        job_emb = await get_embedding(job_text)
        
        if not resume_emb or not job_emb:
            return 0.0
            
        # Cosine similarity: (A . B) / (||A|| * ||B||)
        a = np.array(resume_emb)
        b = np.array(job_emb)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
