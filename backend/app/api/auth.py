"""
Enterprise Auth API v3 — OAuth2, SAML, MFA, RBAC, Sessions, API Keys, Device Tracking.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Body, Query, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import pyotp

from ..db.database import get_db
from ..models.models import User, RoleEnum
from ..models.auth_models import (
    OAuthProvider, MFAProvider, DeviceType, SessionStatus,
    OAuthAccount, UserSession, APIKey, AuthAuditLog, LoginAttempt,
)
from ..services.auth_service import EnterpriseAuthService, AuthError
from ..core.logger import log

router = APIRouter(prefix="/auth", tags=["Auth v3"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


# ─── Request Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    organization_name: str
    organization_slug: str

class OAuthInitiateRequest(BaseModel):
    provider: str  # google, github, microsoft, linkedin
    redirect_uri: str

class OAuthCallbackRequest(BaseModel):
    provider: str
    code: str
    state: str
    redirect_uri: str
    org_name: Optional[str] = None
    org_slug: Optional[str] = None

class MFASetupRequest(BaseModel):
    device_id: int = None

class MFAVerifyRequest(BaseModel):
    code: str

class APIKeyCreateRequest(BaseModel):
    name: str
    scopes: List[str] = []
    allowed_ips: List[str] = []
    expiry_days: Optional[int] = 365

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_request_info(request: Request) -> dict:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "device_type": _detect_device(request.headers.get("user-agent", "")),
        "device_name": request.headers.get("x-device-name"),
    }

def _detect_device(user_agent: str) -> str:
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    if "curl" in ua or "python" in ua or "node" in ua or "axios" in ua:
        return "api"
    return "browser"


async def _get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> User:
    if not token:
        raise HTTPException(401, "Not authenticated")
    svc = EnterpriseAuthService(db)
    payload = svc._safe_decode(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")

    user = await svc._get_user(payload.get("user_id"))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    # Validate session exists and is active
    from sqlalchemy import select
    from ..models.auth_models import UserSession, SessionStatus
    from datetime import datetime, timezone

    stmt = select(UserSession).where(
        UserSession.user_id == user.id,
        UserSession.session_token == token,
        UserSession.status == SessionStatus.ACTIVE,
    )
    session = (await db.execute(stmt)).scalars().first()
    if not session:
        raise HTTPException(401, "Session revoked or expired")

    # Update last activity
    session.last_activity = datetime.now(timezone.utc)
    await db.commit()

    return user


def get_current_user_with_role(required_role: RoleEnum):
    async def dependency(current_user: User = Depends(_get_current_user)):
        roles = [r.name.value if hasattr(r.name, "value") else str(r.name) for r in current_user.roles]
        hierarchy = {"ADMIN": 3, "RECRUITER": 2, "VIEWER": 1}
        user_max = max((hierarchy.get(r, 0) for r in roles), default=0)
        required = hierarchy.get(required_role.value, 0)
        if user_max < required:
            raise HTTPException(403, "Insufficient permissions")
        return current_user
    return dependency


# ═══════════════════════════════════════════════════════════════════════════════
# Registration & Login
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/register")
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    try:
        user = await svc.register(req.email, req.password, req.organization_name, req.organization_slug)
        return {"status": "success", "user_id": user.id, "org_id": user.org_id, "email_verified": user.email_verified}
    except AuthError as e:
        raise HTTPException(e.status_code, str(e), **({"headers": e.extra} if e.extra else {}))


@router.post("/token")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    mfa_code: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    try:
        tokens, session = await svc.login(form_data.username, form_data.password, mfa_code)
        return {
            **tokens,
            "user_id": session.user_id,
            "session_id": session.id,
            "mfa_verified": session.mfa_verified,
        }
    except AuthError as e:
        status = e.status_code or 401
        raise HTTPException(status, str(e), **({"headers": e.extra} if e.extra else {}))


@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    try:
        tokens, session = await svc.refresh_session(refresh_token)
        return {**tokens, "session_id": session.id}
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


@router.post("/logout")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    await svc.logout(current_user.id, token)
    return {"status": "logged_out"}


@router.post("/logout-all")
async def logout_all_devices(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    await svc.logout_all_devices(current_user.id)
    return {"status": "all_sessions_revoked"}


# ═══════════════════════════════════════════════════════════════════════════════
# OAuth / Social Login (with CSRF state protection)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/oauth/providers")
async def list_oauth_providers():
    """Return available OAuth providers and their authorize URLs."""
    return {
        "providers": [
            {"provider": "google", "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth", "scope": "openid email profile"},
            {"provider": "github", "authorize_url": "https://github.com/login/oauth/authorize", "scope": "user:email"},
            {"provider": "microsoft", "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize", "scope": "openid email profile"},
            {"provider": "linkedin", "authorize_url": "https://www.linkedin.com/oauth/v2/authorization", "scope": "openid email profile"},
        ]
    }


@router.post("/oauth/initiate")
async def oauth_initiate(req: OAuthInitiateRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Generate OAuth authorize URL with CSRF state token."""
    svc = EnterpriseAuthService(db, _get_request_info(request))
    state = await svc.create_oauth_state(req.provider, req.redirect_uri)

    from ..core.config import settings as app_settings
    provider_configs = {
        "google": {
            "client_id": app_settings.GOOGLE_CLIENT_ID,
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "scope": "openid email profile",
        },
        "github": {
            "client_id": app_settings.GITHUB_CLIENT_ID,
            "auth_url": "https://github.com/login/oauth/authorize",
            "scope": "user:email",
        },
        "microsoft": {
            "client_id": app_settings.MICROSOFT_CLIENT_ID,
            "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "scope": "openid email profile",
        },
        "linkedin": {
            "client_id": app_settings.LINKEDIN_CLIENT_ID,
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
            "scope": "openid email profile",
        },
    }

    config = provider_configs.get(req.provider)
    if not config:
        raise HTTPException(400, f"Unsupported provider: {req.provider}")

    if not config["client_id"]:
        raise HTTPException(501, f"{req.provider} OAuth not configured")

    authorize_url = (
        f"{config['auth_url']}?"
        f"client_id={config['client_id']}&"
        f"redirect_uri={req.redirect_uri}&"
        f"response_type=code&"
        f"scope={config['scope']}&"
        f"state={state}"
    )
    return {"authorize_url": authorize_url, "state": state}


@router.post("/oauth/callback")
async def oauth_callback(req: OAuthCallbackRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Exchange OAuth code for tokens with CSRF state validation."""
    svc = EnterpriseAuthService(db, _get_request_info(request))

    # Verify CSRF state
    if not await svc.verify_oauth_state(req.state, req.provider):
        raise HTTPException(400, "Invalid or expired OAuth state parameter")

    import httpx
    from ..core.config import settings as app_settings

    provider_config = {
        "google": {
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
            "client_id": app_settings.GOOGLE_CLIENT_ID,
            "client_secret": app_settings.GOOGLE_CLIENT_SECRET,
        },
        "github": {
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "client_id": app_settings.GITHUB_CLIENT_ID,
            "client_secret": app_settings.GITHUB_CLIENT_SECRET,
            "token_in_header": True,
        },
        "microsoft": {
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/v1.0/me",
            "client_id": app_settings.MICROSOFT_CLIENT_ID,
            "client_secret": app_settings.MICROSOFT_CLIENT_SECRET,
        },
        "linkedin": {
            "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
            "userinfo_url": "https://api.linkedin.com/v2/userinfo",
            "client_id": app_settings.LINKEDIN_CLIENT_ID,
            "client_secret": app_settings.LINKEDIN_CLIENT_SECRET,
        },
    }

    config = provider_config.get(req.provider)
    if not config or not config["client_id"] or not config["client_secret"]:
        raise HTTPException(501, f"{req.provider} OAuth not configured")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": req.code,
                "redirect_uri": req.redirect_uri,
                "grant_type": "authorization_code",
            }
            token_headers = {"Accept": "application/json"}

            token_resp = await client.post(config["token_url"], data=token_data, headers=token_headers)
            token_json = token_resp.json()
            access_token = token_json.get("access_token")
            if not access_token:
                log.error("oauth_token_exchange_failed", provider=req.provider, response=str(token_json)[:200])
                raise HTTPException(400, "Failed to exchange OAuth code")

            userinfo_headers = {"Authorization": f"Bearer {access_token}"}
            primary_email = None

            if req.provider == "github":
                userinfo_headers["Accept"] = "application/vnd.github.v3+json"
                emails_resp = await client.get("https://api.github.com/user/emails", headers=userinfo_headers)
                emails = emails_resp.json()
                primary_email = next((e["email"] for e in emails if e.get("primary")), emails[0]["email"] if emails else None)

            userinfo_resp = await client.get(config["userinfo_url"], headers=userinfo_headers)
            userinfo = userinfo_resp.json()
            email = userinfo.get("email") or primary_email
            if not email:
                raise HTTPException(400, "Could not retrieve email from OAuth provider")

            provider_user_id = str(userinfo.get("sub") or userinfo.get("id") or email)
    except httpx.HTTPError as e:
        log.error("oauth_http_error", provider=req.provider, error=str(e))
        raise HTTPException(502, f"OAuth provider communication error: {e}")

    try:
        tokens, session = await svc.oauth_login(
            provider=OAuthProvider(req.provider),
            provider_user_id=provider_user_id,
            email=email,
            provider_data=userinfo,
            org_name=req.org_name,
            org_slug=req.org_slug,
        )
        return {
            **tokens,
            "user_id": session.user_id,
            "session_id": session.id,
            "provider": req.provider,
            "email": email,
        }
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SAML 2.0 SSO
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/saml/login")
async def saml_login(relay_state: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    """Initiate SAML SSO login. Redirects user to IdP."""
    svc = EnterpriseAuthService(db)
    try:
        sso_url, saml_request = await svc.saml_initiate(relay_state)
        # In browser: redirect. For API: return the URL and SAMLRequest.
        return {
            "sso_url": sso_url,
            "saml_request": saml_request,
            "relay_state": relay_state,
        }
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


@router.post("/saml/acs")
async def saml_acs(
    saml_response: str = Form(..., alias="SAMLResponse"),
    relay_state: Optional[str] = Form(None, alias="RelayState"),
    db: AsyncSession = Depends(get_db),
):
    """SAML Assertion Consumer Service — processes IdP response."""
    svc = EnterpriseAuthService(db)
    try:
        tokens, session = await svc.saml_consume(saml_response, relay_state)
        return {**tokens, "user_id": session.user_id, "session_id": session.id}
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


@router.get("/saml/metadata")
async def saml_metadata():
    """Return SP metadata XML for IdP configuration."""
    from ..core.config import settings as app_settings

    metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor entityID="{app_settings.SAML_SP_ENTITY_ID}"
                  xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
    <SPSSODescriptor AuthnRequestsSigned="false"
                     WantAssertionsSigned="true"
                     protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                  Location="{app_settings.SAML_SP_ACS_URL}"
                                  index="0" isDefault="true"/>
        <SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                             Location="{app_settings.SAML_SP_SLS_URL}"/>
    </SPSSODescriptor>
</EntityDescriptor>"""
    from fastapi.responses import Response
    return Response(content=metadata, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════════════════
# MFA
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/mfa/setup")
async def setup_mfa(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    result = await svc.setup_totp_mfa(current_user.id)
    return result


@router.post("/mfa/verify-setup")
async def verify_mfa_setup(
    request: Request,
    code: str = Body(..., embed=True),
    device_id: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    if await svc.verify_totp_setup(current_user.id, device_id, code):
        backup_codes = await svc.generate_backup_codes(current_user.id)
        return {"status": "verified", "backup_codes": backup_codes}
    raise HTTPException(400, "Invalid verification code")


@router.post("/mfa/disable")
async def disable_mfa(
    request: Request,
    code: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    if await svc.disable_mfa(current_user.id, code):
        return {"status": "disabled"}
    raise HTTPException(400, "Invalid MFA code")


# ═══════════════════════════════════════════════════════════════════════════════
# Password Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    result = await svc.forgot_password(req.email)
    # Always return success to prevent email enumeration
    return {"status": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    try:
        await svc.reset_password(req.token, req.new_password)
        return {"status": "Password reset successfully"}
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest, request: Request, db: AsyncSession = Depends(get_db)):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    try:
        await svc.verify_email(req.token)
        return {"status": "Email verified successfully"}
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


@router.post("/resend-verification")
async def resend_verification(req: ResendVerificationRequest, request: Request, db: AsyncSession = Depends(get_db)):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    await svc.resend_verification_email(req.email)
    return {"status": "If your email is registered and unverified, a new email has been sent"}


# ═══════════════════════════════════════════════════════════════════════════════
# Session Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/sessions")
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    sessions = await svc.list_active_sessions(current_user.id)
    return [
        {
            "id": s.id,
            "device_type": s.device_type.value if s.device_type else "browser",
            "device_name": s.device_name,
            "ip_address": s.ip_address,
            "location": s.location,
            "last_activity": s.last_activity.isoformat() if s.last_activity else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    await svc.revoke_session(current_user.id, session_id)
    return {"status": "revoked"}


# ═══════════════════════════════════════════════════════════════════════════════
# API Keys
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/api-keys")
async def create_api_key(
    req: APIKeyCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    result = await svc.create_api_key(
        current_user.id, current_user.org_id,
        req.name, req.scopes, req.allowed_ips, req.expiry_days,
    )
    return result


@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    keys = await svc.list_api_keys(current_user.id)
    return [
        {
            "id": k.id, "name": k.name, "prefix": k.key_prefix,
            "scopes": k.scopes, "last_used_at": k.last_used_at,
            "expires_at": k.expires_at, "use_count": k.use_count,
        }
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    await svc.revoke_api_key(current_user.id, key_id)
    return {"status": "revoked"}


# ═══════════════════════════════════════════════════════════════════════════════
# User Profile
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/me")
async def get_profile(
    current_user: User = Depends(_get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "org_id": current_user.org_id,
        "roles": [r.name.value if hasattr(r.name, "value") else str(r.name) for r in current_user.roles],
        "email_verified": current_user.email_verified,
        "is_active": current_user.is_active,
        "oauth_accounts": [a.provider.value for a in current_user.oauth_accounts] if current_user.oauth_accounts else [],
        "has_mfa": bool(current_user.mfa_devices),
    }


@router.put("/me/password")
async def change_password(
    req: PasswordChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    svc = EnterpriseAuthService(db, _get_request_info(request))
    try:
        await svc.change_password(current_user.id, req.current_password, req.new_password)
        return {"status": "Password changed successfully"}
    except AuthError as e:
        raise HTTPException(e.status_code, str(e))


# ─── Legacy compatibility ──────────────────────────────────────────────────────

ViewerOnly = get_current_user_with_role(RoleEnum.VIEWER)
RecruiterOnly = get_current_user_with_role(RoleEnum.RECRUITER)
AdminOnly = get_current_user_with_role(RoleEnum.ADMIN)
