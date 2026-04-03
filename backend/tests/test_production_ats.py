import pytest
from app.scoring.ats_scorer import ATSScorer
from app.bias.detector import BiasDetector
from app.bias.anonymizer import CandidateAnonymizer

import nltk
try:
    nltk.download('punkt_tab')
    nltk.download('wordnet')
    nltk.download('averaged_perceptron_tagger_eng')
except Exception:
    pass

def test_ats_scorer_components():
    scorer = ATSScorer()
    resume = {
        "raw_text": "Experienced Python developer with React and FastAPI skills. AWS Certified.",
        "skills": ["Python", "React", "FastAPI"],
        "total_years_exp": 5,
        "certifications": ["AWS Certified"]
    }
    job = {
        "description": "Looking for a Python and React expert for backend roles.",
        "required_skills": ["Python", "React", "Node.js"],
        "min_experience": 3
    }
    
    result = scorer.score(resume, job)
    
    assert result["total_score"] > 0
    assert "keyword_match" in result["component_scores"]
    assert result["component_scores"]["experience_relevance"] == 20.0 # 5 > 3
    assert result["component_scores"]["certifications"] == 5.0

def test_bias_detector():
    detector = BiasDetector()
    text = "He is a digital native who graduated in 1995 from a national institute."
    
    audit = detector.run_bias_audit(text, "John Doe")
    
    assert "Graduation year 1995 detected (potential age bias)" in audit["flags"]
    assert "Gendered pronoun 'he' detected" in audit["flags"]
    assert audit["prestige_analysis"]["is_prestigious"] is True
    assert audit["risk_level"] in ["MED", "HIGH"]

def test_anonymizer_pii_scrubbing():
    anonymizer = CandidateAnonymizer()
    text = "Contact me at john.doe@example.com or call +1-555-0199. Graduated in 2015."
    
    scrubbed = anonymizer.anonymize_text(text)
    
    assert "[EMAIL]" in scrubbed
    assert "[PHONE]" in scrubbed
    assert "[YEAR]" in scrubbed
    assert "john.doe" not in scrubbed
