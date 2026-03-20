from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Dict, Any, List

# Load BERT model lazily
_bert_model = None

def get_bert_model():
    global _bert_model
    if _bert_model is None:
        _bert_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _bert_model

class Scorer:
    @staticmethod
    def compute_tfidf_similarity(jd_text: str, resume_text: str) -> float:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([jd_text, resume_text])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
        return float(similarity[0][0])

    @staticmethod
    def compute_bert_similarity(jd_text: str, resume_text: str) -> float:
        model = get_bert_model()
        embeddings = model.encode([jd_text, resume_text])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])
        return float(similarity[0][0])

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
        # Simple binary for now
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
