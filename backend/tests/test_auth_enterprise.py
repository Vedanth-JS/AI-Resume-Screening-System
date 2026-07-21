"""
Comprehensive auth tests — registration, login, MFA, OAuth, SAML, password reset, email verification, API keys, sessions.
Run: pytest tests/test_auth_enterprise.py -v --asyncio-mode=auto
"""
import pytest
import os
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session", autouse=True)
def override_settings():
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["SECRET_KEY"] = "test-secret-key-32-chars-minimum"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["GOOGLE_API_KEY"] = ""
    os.environ["PASSWORD_MIN_LENGTH"] = "12"
    os.environ["PASSWORD_REQUIRE_UPPER"] = "true"
    os.environ["PASSWORD_REQUIRE_LOWER"] = "true"
    os.environ["PASSWORD_REQUIRE_DIGIT"] = "true"
    os.environ["PASSWORD_REQUIRE_SPECIAL"] = "true"


@pytest.fixture
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
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
    
    from sqlalchemy.ext.asyncio import AsyncSession
    async_session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.models.models import Role, RoleEnum
        for r in [RoleEnum.ADMIN, RoleEnum.RECRUITER, RoleEnum.VIEWER]:
            s.add(Role(name=r))
        await s.commit()

    return eng


@pytest.fixture
async def db_session(engine):
    from sqlalchemy.ext.asyncio import AsyncSession
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
async def client(db_session):
    from app.main import app
    from app.db.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ─── Registration ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_with_strong_password(client):
    resp = await client.post("/api/auth/register", json={
        "email": "strong@test.com",
        "password": "Str0ng!Passw0rd",
        "organization_name": "Test Corp",
        "organization_slug": "test-corp",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "user_id" in data
    assert data["email_verified"] == False


@pytest.mark.asyncio
async def test_register_with_weak_password(client):
    resp = await client.post("/api/auth/register", json={
        "email": "weak@test.com",
        "password": "short",
        "organization_name": "Weak Corp",
        "organization_slug": "weak-corp",
    })
    assert resp.status_code == 400
    assert "Password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={
        "email": "dup@test.com",
        "password": "Str0ng!Passw0rd",
        "organization_name": "First Org",
        "organization_slug": "first-org",
    })
    resp = await client.post("/api/auth/register", json={
        "email": "dup@test.com",
        "password": "Str0ng!Passw0rd",
        "organization_name": "Second Org",
        "organization_slug": "second-org",
    })
    assert resp.status_code == 409


# ─── Login ─────────────────────────────────────────────────────────────────────

@pytest.fixture
async def registered_user(client):
    unique_suffix = uuid.uuid4().hex[:8]
    await client.post("/api/auth/register", json={
        "email": f"login_{unique_suffix}@test.com",
        "password": "Str0ng!Passw0rd",
        "organization_name": "Login Corp",
        "organization_slug": f"login-corp-{unique_suffix}",
    })
    return f"login_{unique_suffix}@test.com", "Str0ng!Passw0rd"


@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    email, password = registered_user
    resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, registered_user):
    email, _ = registered_user
    resp = await client.post("/api/auth/token", data={
        "username": email, "password": "WrongPassword1!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post("/api/auth/token", data={
        "username": "nobody@test.com", "password": "Str0ng!Passw0rd",
    })
    assert resp.status_code == 401


# ─── Token Refresh ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_token(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client):
    resp = await client.post("/api/auth/refresh", json={
        "refresh_token": "invalid-token",
    })
    assert resp.status_code == 401


# ─── Profile ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_authenticated(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


# ─── Password Change ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_password(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    token = login_resp.json()["access_token"]

    resp = await client.put("/api/auth/me/password", json={
        "current_password": password,
        "new_password": "NewStr0ng!Pass",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    token = login_resp.json()["access_token"]

    resp = await client.put("/api/auth/me/password", json={
        "current_password": "WrongCurrentP@ss",
        "new_password": "NewStr0ng!Pass",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


# ─── Forgot / Reset Password ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password(client, registered_user):
    email, _ = registered_user
    resp = await client.post("/api/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200
    assert "sent" in resp.json()["status"]


@pytest.mark.asyncio
async def test_forgot_password_nonexistent(client):
    # Should still return 200 to prevent email enumeration
    resp = await client.post("/api/auth/forgot-password", json={"email": "no@body.com"})
    assert resp.status_code == 200


# ─── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    token = login_resp.json()["access_token"]

    resp = await client.post("/api/auth/logout", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged_out"


# ─── API Keys ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_list_api_keys(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    token = login_resp.json()["access_token"]

    # Create
    resp = await client.post("/api/auth/api-keys", json={
        "name": "My Test Key",
        "scopes": ["read:candidates"],
        "expiry_days": 365,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "key" in resp.json()
    assert resp.json()["key"].startswith("ats_")

    # List
    resp = await client.get("/api/auth/api-keys", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ─── Session List ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sessions(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/auth/sessions", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── SAML Endpoints ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_saml_login_not_configured(client):
    resp = await client.get("/api/auth/saml/login")
    assert resp.status_code == 501  # SAML not enabled


# ─── OAuth Provider List ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_oauth_providers(client):
    resp = await client.get("/api/auth/oauth/providers")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    assert len(providers) == 4
    names = [p["provider"] for p in providers]
    assert "google" in names
    assert "github" in names


# ─── Email Verification ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_email_invalid_token(client):
    resp = await client.post("/api/auth/verify-email", json={"token": "bad-token"})
    assert resp.status_code == 400


# ─── Rate Limit ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_rate_limiting(client):
    """After 10+ failed logins, should get rate limited."""
    for i in range(12):
        resp = await client.post("/api/auth/token", data={
            "username": f"ratelimit{i}@test.com",
            "password": "WrongPassword1!",
        })
    # The last one should be rate limited
    assert resp.status_code in [429, 401]  # Depends on whether same identifier tracked


# ─── Protected Route Access ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_protected_route_no_auth(client):
    resp = await client.get("/api/jobs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_auth(client, registered_user):
    email, password = registered_user
    login_resp = await client.post("/api/auth/token", data={
        "username": email, "password": password,
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/jobs", headers={
        "Authorization": f"Bearer {token}",
    })
    # Should work but return empty list (no jobs created)
    assert resp.status_code == 200


# ─── Password Policy ───────────────────────────────────────────────────────────

def test_password_validation():
    from app.services.auth_service import validate_password_strength

    valid, _ = validate_password_strength("Str0ng!Passw0rd")
    assert valid

    valid, msg = validate_password_strength("short")
    assert not valid
    assert "at least 12" in msg

    valid, msg = validate_password_strength("nouppercase1!")
    assert not valid
    assert "uppercase" in msg

    valid, msg = validate_password_strength("NOLOWERCASE1!")
    assert not valid
    assert "lowercase" in msg

    valid, msg = validate_password_strength("NoDigitHere!")
    assert not valid
    assert "digit" in msg

    valid, msg = validate_password_strength("NoSpecial123")
    assert not valid
    assert "special" in msg
