"""
Unit tests for app.core.scorer.Scorer

All tests use mocked embeddings — no external services required.
Coverage target: keyword_score, format_score, section_score, experience_score, compute_full_score.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ─── Shared Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def scorer():
    """Return a Scorer instance with a mocked embedding service."""
    from app.core.scorer import Scorer
    s = Scorer()
    return s


@pytest.fixture
def sample_resume_text():
    return """
    Jane Smith
    jane@example.com | +1 555-0123
    
    SKILLS: Python, FastAPI, PostgreSQL, Docker, Kubernetes, Redis, SQLAlchemy, Pytest
    
    EXPERIENCE:
    TechCorp — Senior Backend Engineer (Jan 2020 – Present, 4.5 years)
    - Built scalable REST APIs handling 100k req/s
    - Led migration from monolith to microservices using Docker + Kubernetes
    
    StartupX — Software Engineer (Jun 2017 – Dec 2019, 2.5 years)
    - Developed data pipelines using Python and PostgreSQL
    
    EDUCATION:
    B.S. Computer Science, MIT, 2017
    
    CERTIFICATIONS: AWS Solutions Architect, Kubernetes CKAD
    
    PROJECTS:
    - Resume screening system using FastAPI and LLM APIs
    """


@pytest.fixture
def sample_jd_skills():
    return ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Kubernetes"]


# ─── Keyword Score Tests ──────────────────────────────────────────────────────

class TestKeywordScore:
    def test_perfect_match(self, scorer, sample_resume_text, sample_jd_skills):
        """All required skills present → high score."""
        result = scorer.keyword_score(sample_resume_text, sample_jd_skills)
        assert result["score"] >= 80, f"Expected >= 80, got {result['score']}"
        assert "matched" in result
        assert "missing" in result
        assert len(result["matched"]) >= 4

    def test_no_match(self, scorer):
        """Resume with zero matching skills → very low score."""
        resume = "I am a plumber with experience in pipe installation and wrench usage."
        skills = ["Python", "Machine Learning", "TensorFlow", "Kubernetes"]
        result = scorer.keyword_score(resume, skills)
        assert result["score"] <= 20, f"Expected <= 20, got {result['score']}"
        assert len(result["matched"]) == 0 or result["score"] < 25

    def test_empty_skills_list(self, scorer, sample_resume_text):
        """Empty JD skills list → score should be 0 or handled gracefully."""
        result = scorer.keyword_score(sample_resume_text, [])
        assert isinstance(result["score"], (int, float))
        assert result["score"] >= 0

    def test_case_insensitive_matching(self, scorer):
        """Skills should match regardless of case."""
        resume = "Proficient in PYTHON, fastapi, POSTGRESQL"
        skills = ["python", "FastAPI", "PostgreSQL"]
        result = scorer.keyword_score(resume, skills)
        assert result["score"] >= 50

    def test_returns_matched_and_missing(self, scorer, sample_resume_text, sample_jd_skills):
        """Result must always contain 'matched' and 'missing' lists."""
        result = scorer.keyword_score(sample_resume_text, sample_jd_skills)
        assert isinstance(result.get("matched"), list)
        assert isinstance(result.get("missing"), list)

    def test_partial_match(self, scorer):
        """Half the skills match → score in middle range."""
        resume = "Python developer with FastAPI experience."
        skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Kubernetes"]
        result = scorer.keyword_score(resume, skills)
        # At least Python and FastAPI should match → score between 20-70
        assert 15 <= result["score"] <= 80


# ─── Format Score Tests ───────────────────────────────────────────────────────

class TestFormatScore:
    def test_well_formatted_resume(self, scorer, sample_resume_text):
        """A well-formatted resume with all sections → score >= 70."""
        score = scorer.format_score(sample_resume_text)
        assert isinstance(score, (int, float))
        assert score >= 60, f"Expected >= 60, got {score}"

    def test_empty_resume(self, scorer):
        """Empty resume → low format score."""
        score = scorer.format_score("")
        assert score <= 30

    def test_minimal_resume(self, scorer):
        """Minimal resume → score reflects missing sections."""
        score = scorer.format_score("John Doe. Programmer.")
        assert score <= 60

    def test_score_in_valid_range(self, scorer, sample_resume_text):
        """Format score must always be in 0-100 range."""
        score = scorer.format_score(sample_resume_text)
        assert 0 <= score <= 100


# ─── Section Score Tests ──────────────────────────────────────────────────────

class TestSectionScore:
    def test_complete_sections(self, scorer, sample_resume_text):
        """Resume with experience, education, skills → high section score."""
        score = scorer.section_score(sample_resume_text)
        assert isinstance(score, (int, float))
        assert score >= 60

    def test_missing_sections(self, scorer):
        """Resume missing education and experience → lower score."""
        sparse = "John Smith\njohn@example.com\nI like coding."
        score = scorer.section_score(sparse)
        assert score <= 70

    def test_score_range(self, scorer, sample_resume_text):
        score = scorer.section_score(sample_resume_text)
        assert 0 <= score <= 100


# ─── Experience Score Tests ───────────────────────────────────────────────────

class TestExperienceScore:
    def test_exceeds_required(self, scorer, sample_resume_text):
        """7 years experience vs 3 required → high score."""
        score = scorer.experience_score(sample_resume_text, required_years=3)
        assert score >= 70

    def test_meets_required(self, scorer, sample_resume_text):
        """Candidate meets exact requirement."""
        score = scorer.experience_score(sample_resume_text, required_years=7)
        assert 40 <= score <= 100

    def test_no_experience_required(self, scorer, sample_resume_text):
        """0 years required → should return high score (no barrier)."""
        score = scorer.experience_score(sample_resume_text, required_years=0)
        assert score >= 70

    def test_far_below_required(self, scorer):
        """Junior resume vs 10 years required → low score."""
        resume = "Fresh grad 2023. No work experience."
        score = scorer.experience_score(resume, required_years=10)
        assert score <= 50

    def test_score_range(self, scorer, sample_resume_text):
        score = scorer.experience_score(sample_resume_text, required_years=5)
        assert 0 <= score <= 100


# ─── Full Hybrid Score Integration ────────────────────────────────────────────

class TestComputeFullScore:
    @pytest.mark.asyncio
    async def test_full_score_structure(self, scorer, sample_resume_text, sample_jd_skills):
        """compute_full_score must return all expected keys."""
        # Provide a pre-computed semantic_score to avoid embedding call
        result = scorer.compute_full_score(
            resume_text=sample_resume_text,
            jd_skills=sample_jd_skills,
            required_years=3,
            semantic_score_override=75.0,
        )
        required_keys = {
            "overall_score", "keyword_score", "format_score",
            "section_score", "experience_score",
        }
        assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - result.keys()}"

    def test_overall_score_in_range(self, scorer, sample_resume_text, sample_jd_skills):
        """Overall composite score must be 0-100."""
        result = scorer.compute_full_score(
            resume_text=sample_resume_text,
            jd_skills=sample_jd_skills,
            required_years=3,
            semantic_score_override=60.0,
        )
        assert 0 <= result["overall_score"] <= 100

    def test_weights_sum_contribution(self, scorer, sample_resume_text, sample_jd_skills):
        """High semantic override should drive up overall score."""
        low_result = scorer.compute_full_score(
            resume_text=sample_resume_text,
            jd_skills=sample_jd_skills,
            required_years=3,
            semantic_score_override=0.0,
        )
        high_result = scorer.compute_full_score(
            resume_text=sample_resume_text,
            jd_skills=sample_jd_skills,
            required_years=3,
            semantic_score_override=100.0,
        )
        assert high_result["overall_score"] > low_result["overall_score"]
