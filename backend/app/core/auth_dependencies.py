"""
Enterprise Auth Dependencies — JWT, API Key, ABAC guards.
Provides FastAPI dependency callables for route-level security.
"""
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from ..db.database import get_db
from ..models.models import User, RoleEnum
from ..models.auth_models import UserSession, SessionStatus
from ..services.auth_service import EnterpriseAuthService
from ..services.abac import engine as abac_engine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


# ─── Device Detection ──────────────────────────────────────────────────────────

def _detect_device(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    if "curl" in ua or "python" in ua or "node" in ua or "axios" in ua:
        return "api"
    return "browser"


# ─── JWT Bearer Auth ───────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> User:
    """Extract and validate the current user from JWT Bearer token."""
    if not token:
        raise HTTPException(401, "Not authenticated — Bearer token required")

    svc = EnterpriseAuthService(db)
    payload = svc._safe_decode(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")

    user = await svc._get_user(payload.get("user_id"))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    # Validate session
    stmt = select(UserSession).where(
        UserSession.user_id == user.id,
        UserSession.session_token == token,
        UserSession.status == SessionStatus.ACTIVE,
    )
    # Execute the session lookup correctly based on db type
    if hasattr(db, "execute") and hasattr(db.execute, "__code__") and db.execute.__code__.co_flags & 0x80:
        # Async function (coroutine)
        result = await db.execute(stmt)
    else:
        # Synchronous shim
        result = db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(401, "Session revoked or expired")

    # Check inactivity timeout
    from ..core.config import settings
    if settings.SESSION_INACTIVE_TIMEOUT_MINUTES > 0:
        inactive_limit = datetime.now(timezone.utc) - timedelta(
            minutes=settings.SESSION_INACTIVE_TIMEOUT_MINUTES
        )
        if session.last_activity:
            last_act = session.last_activity
            if last_act.tzinfo is None:
                last_act = last_act.replace(tzinfo=timezone.utc)
            if last_act < inactive_limit:
                session.status = SessionStatus.EXPIRED
                await db.commit()
                raise HTTPException(401, "Session expired due to inactivity")

    # Update last activity
    session.last_activity = datetime.now(timezone.utc)
    await db.commit()

    return user


# ─── API Key Auth ──────────────────────────────────────────────────────────────

async def get_current_user_from_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Authenticate via API key (X-API-Key header or Bearer ats_...)."""
    api_key_raw = request.headers.get("x-api-key")

    if not api_key_raw and request.headers.get("authorization", "").startswith("Bearer "):
        token = request.headers["authorization"][7:]
        if token.startswith("ats_"):
            api_key_raw = token

    if not api_key_raw:
        return None

    svc = EnterpriseAuthService(db, {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    })
    key_info = await svc.verify_api_key(api_key_raw)
    if not key_info:
        raise HTTPException(401, "Invalid or expired API key")

    user = await svc._get_user(key_info["user_id"])
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return user


async def get_current_user_hybrid(
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Try JWT first, fall back to API key."""
    # Try API key first
    api_key_user = await get_current_user_from_api_key(request, db)
    if api_key_user:
        return api_key_user

    # Fall back to JWT
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    if not token or token.startswith("ats_"):
        raise HTTPException(401, "Not authenticated — provide a Bearer token or API key")

    return await get_current_user(token=token, db=db, request=request)


# ─── Role-Based Access Control ─────────────────────────────────────────────────

def require_role(required_role: RoleEnum):
    """RBAC guard — checks user has minimum role level."""
    async def dependency(current_user: User = Depends(get_current_user_hybrid)):
        roles = [
            r.name.value if hasattr(r.name, "value") else str(r.name)
            for r in current_user.roles
        ]
        hierarchy = {"ADMIN": 3, "RECRUITER": 2, "VIEWER": 1}
        user_max = max((hierarchy.get(r, 0) for r in roles), default=0)
        required = hierarchy.get(required_role.value, 0)
        if user_max < required:
            raise HTTPException(403, f"Insufficient permissions — requires {required_role.value}")
        return current_user
    return dependency


# ─── Attribute-Based Access Control ────────────────────────────────────────────

def require_abac(resource_type: str, action: str):
    """
    ABAC guard — evaluates policies based on subject (user), resource, action, and environment.
    Falls back to RBAC if no matching ABAC policy exists.
    """
    async def dependency(
        current_user: User = Depends(get_current_user_hybrid),
        request: Request = None,
    ) -> User:
        roles = [
            r.name.value if hasattr(r.name, "value") else str(r.name)
            for r in current_user.roles
        ]

        subject = {
            "user_id": current_user.id,
            "org_id": current_user.org_id,
            "roles": roles,
        }

        resource = {
            "type": resource_type,
            "org_id": current_user.org_id,
        }

        env = {
            "ip": request.client.host if request and request.client else None,
            "user_agent": request.headers.get("user-agent") if request else None,
        }

        if abac_engine.evaluate(subject, resource, action, env):
            return current_user

        raise HTTPException(403, f"ABAC deny: {action} on {resource_type}")
    return dependency


# ─── Convenience aliases ───────────────────────────────────────────────────────

ViewerOnly = require_role(RoleEnum.VIEWER)
RecruiterOnly = require_role(RoleEnum.RECRUITER)
AdminOnly = require_role(RoleEnum.ADMIN)

# ABAC-aware guards (preferred for new endpoints)
CanReadCandidate = require_abac("candidate", "read")
CanWriteCandidate = require_abac("candidate", "create")
CanManageInterview = require_abac("interview", "create")
CanReadJob = require_abac("job", "read")
CanManageJob = require_abac("job", "create")
CanReadAnalytics = require_abac("analytics", "read")
