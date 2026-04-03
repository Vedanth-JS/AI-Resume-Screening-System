import json
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from typing import Dict, List, Any
from pathlib import Path

# Ensure NLTK data is available
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt')
    nltk.download('wordnet')
    nltk.download('averaged_perceptron_tagger')

class ATSScorer:
    def __init__(self, ontology_path: str = "app/resources/skills_ontology.json"):
        self.ontology = self._load_ontology(ontology_path)

    def _load_ontology(self, path: str) -> Dict[str, List[str]]:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _extract_keywords(self, text: str) -> List[str]:
        """Simple keyword extraction using NLTK: Nouns and Adjectives."""
        tokens = word_tokenize(text.lower())
        tagged = nltk.pos_tag(tokens)
        keywords = [word for word, pos in tagged if pos.startswith(('NN', 'JJ'))]
        return list(set(keywords))

    def _get_synonyms(self, word: str) -> List[str]:
        synonyms = set()
        for syn in wordnet.synsets(word):
            for l in syn.lemmas():
                synonyms.add(l.name().replace('_', ' '))
        return list(synonyms)

    def score(self, resume: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates ATS Score (Total 100).
        - Keyword Match (30)
        - Skills Coverage (25)
        - Experience Relevance (20)
        - Education Match (10)
        - Format Quality (10)
        - Certifications (5)
        """
        component_scores = {
            "keyword_match": 0.0,
            "skills_coverage": 0.0,
            "experience_relevance": 0.0,
            "education_match": 0.0,
            "format_quality": 10.0, # Default for now
            "certifications": 0.0
        }

        # 1. Keyword Match (30 pts)
        jd_keywords = self._extract_keywords(job.get("description", ""))
        resume_text = resume.get("raw_text", "").lower()
        matched_keywords = []
        for kw in jd_keywords:
            if kw in resume_text:
                matched_keywords.append(kw)
            else:
                # Check ontology and synonyms
                syns = self._get_synonyms(kw)
                if any(s in resume_text for s in syns):
                    matched_keywords.append(kw)
        
        kw_ratio = len(matched_keywords) / len(jd_keywords) if jd_keywords else 0
        component_scores["keyword_match"] = round(kw_ratio * 30, 2)

        # 2. Skills Coverage (25 pts)
        req_skills = [s.lower() for s in job.get("required_skills", [])]
        cand_skills = [s.lower() for s in resume.get("skills", [])]
        matched_skills = []
        for rs in req_skills:
            if rs in cand_skills:
                matched_skills.append(rs)
            else:
                # Ontology check
                for group, members in self.ontology.items():
                    if rs in [m.lower() for m in members]:
                        if any(m.lower() in cand_skills for m in members):
                            matched_skills.append(rs)
                            break
        
        skill_ratio = len(matched_skills) / len(req_skills) if req_skills else 0
        component_scores["skills_coverage"] = round(skill_ratio * 25, 2)

        # 3. Experience Relevance (20 pts)
        req_exp = job.get("min_experience", 0)
        cand_exp = resume.get("total_years_exp", 0)
        if cand_exp >= req_exp:
            component_scores["experience_relevance"] = 20.0
        else:
            component_scores["experience_relevance"] = round((cand_exp / req_exp) * 20, 2) if req_exp > 0 else 20.0

        # 4. Education Match (10 pts)
        # Placeholder for complex degree matching
        component_scores["education_match"] = 10.0 # Default full for now

        # 5. Certifications (5 pts)
        # Simple count for now
        if resume.get("certifications"):
            component_scores["certifications"] = 5.0

        total_score = sum(component_scores.values())

        return {
            "total_score": round(total_score, 2),
            "component_scores": component_scores,
            "matched_keywords": matched_keywords,
            "missing_keywords": [kw for kw in jd_keywords if kw not in matched_keywords],
            "improvement_suggestions": [
                "Include keywords: " + ", ".join(jd_keywords[:5]),
                "Highlight relevant skills: " + ", ".join(req_skills[:5])
            ]
        }
