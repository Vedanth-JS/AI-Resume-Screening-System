from typing import Dict, Any, List
from .scorer import Scorer
from ..services.llm_service import LLMService
import os

class Agent:
    def __init__(self, name: str):
        self.name = name

    async def execute(self, data: Any):
        raise NotImplementedError

from .parser import ResumeParser
from ..services.llm_service import LLMService

class ParsingAgent(Agent):
    def __init__(self):
        super().__init__("Parser Agent")

    async def execute(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        # 1. Extract raw text
        text = ResumeParser.extract_text(file_content, filename)
        
        # 2. Try LLM extraction
        parsed_data = await LLMService.extract_resume_data(text)
        
        # 3. Fallback if LLM fails
        if not parsed_data or not parsed_data.get("name") or parsed_data.get("name") == "Unknown":
            parsed_data = ResumeParser.parse_resume_fallback(text)
        else:
            # Ensure raw_text is always included
            parsed_data["raw_text"] = text
            
        return parsed_data

class SkillEvaluatorAgent(Agent):
    def __init__(self):
        super().__init__("Skill Evaluator Agent")

    async def execute(self, parsed_resume: Dict[str, Any], req_skills: List[str]) -> Dict[str, Any]:
        res_skills = set([s.lower() for s in parsed_resume.get("skills", [])])
        required = set([s.lower() for s in req_skills])
        
        if not required:
            return {"score": 1.0, "matched": [], "missing": []}
            
        matched = list(required.intersection(res_skills))
        missing = list(required - res_skills)
        score = len(matched) / len(required)
        return {"score": score, "matched": matched, "missing": missing}

class ExperienceAnalyzerAgent(Agent):
    def __init__(self):
        super().__init__("Experience Analyzer Agent")

    async def execute(self, parsed_resume: Dict[str, Any], min_exp: int) -> Dict[str, Any]:
        candidate_exp = parsed_resume.get("total_years_experience", 0)
        if isinstance(candidate_exp, str):
            try: candidate_exp = float(candidate_exp)
            except: candidate_exp = 0.0
            
        score = min(candidate_exp / min_exp, 1.0) if min_exp > 0 else 1.0
        return {"score": score, "candidate_exp": candidate_exp, "required_exp": min_exp}

class LLMEvaluatorAgent(Agent):
    def __init__(self):
        super().__init__("LLM Evaluator Agent")

    async def execute(self, jd_text: str, resume_text: str) -> Dict[str, Any]:
        evaluation = await LLMService.evaluate_candidate(jd_text, resume_text)
        return {"evaluation": evaluation}

class FinalScorerAgent(Agent):
    def __init__(self):
        super().__init__("Final Scorer Agent")

    async def execute(self, skill_result: Dict[str, Any], exp_result: Dict[str, Any], semantic_score: float, edu_match: float = 0.8) -> Dict[str, Any]:
        # Weighted system from Spec: Skills 40%, Experience 30%, Semantic 20%, Education 10%
        total = (
            skill_result["score"] * 0.4 +
            exp_result["score"] * 0.3 +
            semantic_score * 0.2 +
            edu_match * 0.1
        )
        score_val = round(total * 100, 2)
        
        explanation = (
            f"Final ATS Score: {score_val}%. "
            f"Skills Match: {round(skill_result['score']*100)}%, "
            f"Experience Match: {round(exp_result['score']*100)}%, "
            f"Semantic Relevance: {round(semantic_score*100)}%."
        )
        
        return {"final_score": score_val, "explanation": explanation}

class ATSWorkflow:
    def __init__(self):
        self.parser = ParsingAgent()
        self.skill_evaluator = SkillEvaluatorAgent()
        self.exp_analyzer = ExperienceAnalyzerAgent()
        self.llm_evaluator = LLMEvaluatorAgent()
        self.scorer = FinalScorerAgent()

class ATSWorkflow:
    def __init__(self):
        self.parser = ParsingAgent()
        self.skill_evaluator = SkillEvaluatorAgent()
        self.exp_analyzer = ExperienceAnalyzerAgent()
        self.llm_evaluator = LLMEvaluatorAgent()
        self.scorer = FinalScorerAgent()

    async def process(self, file_content: bytes, filename: str, job_description: str, req_skills: List[str], min_exp: int):
        # 1. Parse Resume (Agent 1)
        parsed_data = await self.parser.execute(file_content, filename)
        
        # 2. Match Skills (Agent 2)
        skill_result = await self.skill_evaluator.execute(parsed_data, req_skills)
        
        # 3. Analyze Experience (Agent 3)
        exp_result = await self.exp_analyzer.execute(parsed_data, min_exp)
        
        # 4. Semantic Similarity (Sentence Transformers)
        semantic_score = Scorer.get_similarity(parsed_data["raw_text"], job_description)
        
        # 5. LLM Evaluation & Interview Prep
        llm_result = await self.llm_evaluator.execute(job_description, parsed_data["raw_text"])
        
        # 6. Final Score Aggregation (Agent 4)
        # Using 0.8 as default for education match until EduAgent is specific
        final_result = await self.scorer.execute(skill_result, exp_result, semantic_score)
        
        return {
            "candidate": parsed_data,
            "skill_analysis": skill_result,
            "experience_analysis": exp_result,
            "semantic_score": round(semantic_score * 100, 2),
            "llm_evaluation": llm_result["evaluation"],
            "final_result": final_result
        }
