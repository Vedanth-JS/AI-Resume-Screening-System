"""
DEPRECATED — Legacy ATS scorer (NLTK-based).
This module has been replaced by app.core.scorer (v3.0) which uses:
- Gemini 768d embeddings for semantic scoring
- Skill taxonomy + rapidfuzz for keyword matching
- Sigmoid diminishing-returns experience scoring
- 5-component weighted composite

Kept for backwards compatibility only. New imports should use:
    from app.core.scorer import Scorer
"""
import json
from typing import Dict, List, Any

from ..core.scorer import Scorer as _NewScorer
from ..core.logger import log


class ATSScorer:
    """Legacy wrapper — delegates to the new Scorer engine."""

    def __init__(self, ontology_path: str = "app/resources/skills_ontology.json"):
        log.warning("ats_scorer.deprecated", note="Use app.core.scorer.Scorer instead.")
        self.ontology = {}
        try:
            with open(ontology_path, "r") as f:
                self.ontology = json.load(f)
        except Exception:
            pass

    def score(self, resume: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy sync wrapper — only works with pre-computed keyword detail."""
        from ..core.scorer import Scorer
        resume_text = resume.get("raw_text", "")
        jd_text = job.get("description", "")
        jd_keywords = [
            k
            for k in self.ontology.keys()
            if k.lower() in jd_text.lower()
        ]
        result = Scorer.compute_full_score(
            resume_text,
            jd_text,
            jd_keywords or ["python", "react", "sql"],
            candidate_years=resume.get("total_years_exp", 0),
            required_years=job.get("min_experience", 0),
        )

        candidate_years = float(resume.get("total_years_exp", 0) or 0)
        required_years = float(job.get("min_experience", 0) or 0)
        if required_years <= 0:
            experience_relevance = 20.0
        elif candidate_years >= required_years:
            experience_relevance = 20.0
        else:
            experience_relevance = round((candidate_years / required_years) * 20.0, 2)

        return {
            "total_score": result["overall_score"],
            "component_scores": {
                "keyword_match": result["keyword_score"],
                "skills_coverage": result["keyword_score"],
                "experience_relevance": experience_relevance,
                "education_match": 80.0,
                "format_quality": result["format_score"],
                "certifications": 5.0,
            },
            "matched_keywords": result["keyword_detail"].get("matched", []),
            "missing_keywords": result["keyword_detail"].get("missing", []),
            "improvement_suggestions": result["suggestions"],
        }
