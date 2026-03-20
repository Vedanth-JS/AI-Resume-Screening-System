from app.core.extractor import FeatureExtractor
from app.core.scorer import Scorer
from app.core.bias_detector import BiasDetector

def test_skill_extraction():
    text = "Successful candidate has experience in Python and React."
    extractor = FeatureExtractor(text)
    skills = extractor.extract_skills()
    assert "Python" in skills
    assert "React" in skills

def test_bias_detection():
    jd = "We are looking for a rockstar developer."
    biases = BiasDetector.detect_bias(jd)
    assert any(b["word"] == "rockstar" for b in biases)

def test_scoring_weights():
    scores = Scorer.calculate_total_score(
        skills_matched=["Python"],
        required_skills=["Python"],
        candidate_exp=5,
        required_exp=5,
        candidate_edu="Bachelor",
        required_edu="Bachelor",
        semantic_score=1.0
    )
    assert scores["total_score"] == 1.0
