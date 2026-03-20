import os
from openai import OpenAI
import numpy as np
from typing import Dict, Any, List

# Initialize OpenAI Client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    # Use a dummy key to prevent initialization error; calls will fail gracefully in try-except below
    api_key = "sk-no-key-provided-local-dev"
client = OpenAI(api_key=api_key)

class Scorer:
    @staticmethod
    def get_embedding(text: str) -> List[float]:
        try:
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting OpenAI embedding: {e}")
            return [0.0] * 1536 # Default size for text-embedding-3-small

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        a = np.array(v1)
        b = np.array(v2)
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    @staticmethod
    def compute_semantic_similarity(jd_text: str, resume_text: str) -> float:
        emb1 = Scorer.get_embedding(jd_text)
        emb2 = Scorer.get_embedding(resume_text)
        return Scorer.cosine_similarity(emb1, emb2)

    @staticmethod
    def calculate_total_score(
        skills_matched: List[str],
        required_skills: List[str],
        candidate_exp: int,
        required_exp: int,
        candidate_edu: str,
        required_edu: str,
        semantic_score: float,
        weights: Dict[str, float] = None
    ) -> Dict[str, float]:
        if weights is None:
            weights = {
                "skills": 0.40,
                "experience": 0.25,
                "education": 0.15,
                "semantic": 0.20
            }

        # Skills Score
        if not required_skills:
            skills_score = 1.0
        else:
            match_count = len([s for s in skills_matched if s.lower() in [rs.lower() for rs in required_skills]])
            skills_score = match_count / len(required_skills)

        # Experience Score
        if required_exp == 0:
            exp_score = 1.0
        else:
            exp_score = min(candidate_exp / required_exp, 1.0)

        # Education Score
        edu_score = 1.0 if candidate_edu.lower() == required_edu.lower() else 0.5
        if candidate_edu == "Not Specified": edu_score = 0.2

        total = (
            weights["skills"] * skills_score +
            weights["experience"] * exp_score +
            weights["education"] * edu_score +
            weights["semantic"] * semantic_score
        )

        return {
            "total_score": round(total, 2),
            "skills_score": round(skills_score, 2),
            "experience_score": round(exp_score, 2),
            "education_score": round(edu_score, 2),
            "semantic_score": round(semantic_score, 2)
        }
