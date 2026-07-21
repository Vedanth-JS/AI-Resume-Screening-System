"""
Unit & integration tests for the AI ATS backend.
Run: pytest tests/ -v --asyncio-mode=auto
"""
import pytest
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, NullPool

# ─── In-memory test DB setup ─────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(autouse=True)
def override_settings():
    """Override settings before any app import."""
    import os
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ["GOOGLE_API_KEY"] = ""

@pytest.fixture
async def engine():
    from app.db.database import Base
    import app.models.models  # noqa: F401
    import app.models.auth_models  # noqa: F401
    import app.models.ats_models  # noqa: F401
    eng = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed roles
    async_session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        from app.models.models import Role, RoleEnum
        for r in [RoleEnum.ADMIN, RoleEnum.RECRUITER, RoleEnum.VIEWER]:
            session.add(Role(name=r))
        await session.commit()
        
    return eng

@pytest.fixture
async def db_session(engine):
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()

@pytest.fixture
async def client(db_session):
    """AsyncClient for FastAPI app with DB override."""
    from app.main import app
    from app.db.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ─── Auth tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    if data["status"] != "ok":
        raise ValueError(f"HEALTH DATA: {data}")
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    register_data = {
        "email": "test@example.com",
        "password": "TestPass!123456",
        "organization_name": "Test Org",
        "organization_slug": "test-org"
    }
    resp = await client.post("/api/auth/register", json=register_data)
    assert resp.status_code == 200

    # Login
    resp = await client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "TestPass!123456"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/auth/token",
        data={"username": "test@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


# ─── Jobs tests ──────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_token(client):
    unique_suffix = uuid.uuid4().hex[:8]
    register_data = {
        "email": f"recruiter_{unique_suffix}@test.com",
        "password": "TestPass!123456",
        "organization_name": "Recruitment Corp",
        "organization_slug": f"recruitment-corp-{unique_suffix}"
    }
    await client.post("/api/auth/register", json=register_data)
    resp = await client.post(
        "/api/auth/token",
        data={"username": register_data["email"], "password": "TestPass!123456"},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_list_jobs(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Create job
    job_data = {
        "title": "Senior Python Engineer",
        "description": "We need a Python expert with FastAPI experience.",
        "required_skills": ["python", "fastapi", "postgresql"],
        "min_experience": 3,
        "required_education": "Bachelor's Degree",
    }
    resp = await client.post("/api/jobs", json=job_data, headers=headers)
    assert resp.status_code == 200
    job = resp.json()
    assert job["title"] == "Senior Python Engineer"
    job_id = job["id"]

    # List jobs
    resp = await client.get("/api/jobs", headers=headers)
    assert resp.status_code == 200
    jobs = resp.json()
    assert any(j["id"] == job_id for j in jobs)

@pytest.mark.asyncio
async def test_get_job_not_found(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = await client.get("/api/jobs/99999", headers=headers)
    assert resp.status_code == 404


# ─── ATS Scorer unit tests ───────────────────────────────────────────────────

def test_keyword_score_exact():
    from app.core.scorer import Scorer
    resume = "I have experience with Python, FastAPI, and PostgreSQL."
    kws    = ["python", "fastapi", "postgresql"]
    result = Scorer.keyword_score(resume, kws)
    assert result["score"] == 1.0
    assert len(result["matched"]) == 3
    assert len(result["missing"]) == 0

def test_keyword_score_partial():
    from app.core.scorer import Scorer
    resume = "Experienced in Python development."
    kws    = ["python", "java", "ruby"]
    result = Scorer.keyword_score(resume, kws)
    assert 0 < result["score"] < 1.0
    assert "python" in result["matched"]

def test_keyword_score_empty_keywords():
    from app.core.scorer import Scorer
    result = Scorer.keyword_score("Some resume text", [])
    assert result["score"] == 1.0

def test_format_score_full():
    from app.core.scorer import Scorer
    resume = """
    John Doe | john@email.com | +1 555-123-4567 | linkedin.com/in/john
    
    EDUCATION
    B.S. Computer Science, MIT, 2018 – 2022
    
    EXPERIENCE
    • Built Python APIs using FastAPI  Jun 2022 – Present
    • Led team of 5 engineers
    
    SKILLS
    Python, FastAPI, PostgreSQL, Docker
    """
    result = Scorer.format_score(resume)
    assert result["score"] >= 0.7

def test_section_score():
    from app.core.scorer import Scorer
    resume = """
    EDUCATION: B.S. CS
    EXPERIENCE: Software Engineer at XYZ
    SKILLS: Python, Java
    PROJECTS: Built a chat app
    CERTIFICATIONS: AWS Certified
    """
    result = Scorer.section_score(resume)
    assert result["score"] >= 0.5
    assert "education" in result["sections_found"]

def test_compute_full_score_structure(monkeypatch):
    from app.core.scorer import Scorer
    monkeypatch.setattr(Scorer, "semantic_score_st", lambda x, y: 85.0)
    resume = "Python developer with 5 years experience. SKILLS: Python, FastAPI. linkedin.com/johndoe"
    jd     = "We need a Python engineer with FastAPI experience."
    result = Scorer.compute_full_score(resume, jd, ["python", "fastapi"])
    assert "overall_score" in result
    assert "keyword_score" in result
    assert "semantic_score" in result
    assert "format_score" in result
    assert "section_score" in result
    assert 0 <= result["overall_score"] <= 100


# ─── Analytics endpoint ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_overview_auth_required(client):
    resp = await client.get("/api/analytics/overview")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_analytics_overview_returns_structure(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = await client.get("/api/analytics/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_applications" in data
    assert "average_score" in data
    assert "active_jobs" in data
    assert "status_distribution" in data


# ─── LLM service (mocked) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_resume_data_no_api_key():
    """Without API key, should return empty dict (not crash)."""
    from app.services.llm_service import LLMService
    result = await LLMService.extract_resume_data("John Doe, Python developer.")
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_generate_interview_questions_fallback():
    """Without API key, should return at least 1 fallback question."""
    from app.services.llm_service import LLMService
    result = await LLMService.generate_interview_questions(
        resume_gaps=["docker", "kubernetes"],
        jd_text="We need a DevOps engineer with Docker and Kubernetes experience.",
    )
    assert isinstance(result, list)
    assert len(result) >= 1


# ─── Candidates endpoint ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_candidates_empty(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = await client.get("/api/candidates", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
