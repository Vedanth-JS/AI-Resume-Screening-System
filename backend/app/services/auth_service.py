"""
Enterprise Authentication Service v3 — OAuth2, JWT, MFA, RBAC, ABAC, SAML, Sessions, API Keys.
"""
import os, re, uuid, hashlib, asyncio, secrets
import inspect
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any

import bcrypt
import jwt
from sqlalchemy import select, func, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import settings
from ..core.logger import log
from ..models.models import User, Role, Organization, user_roles, RoleEnum
from ..models.auth_models import (
    OAuthAccount, OAuthProvider,
    MFADevice, MFAProvider,
    UserSession, SessionStatus, DeviceType,
    APIKey,
    AuthAuditLog,
    LoginAttempt,
    PasswordResetToken,
    EmailVerificationToken,
    OAuthState,
)

# ─── Token helpers ─────────────────────────────────────────────────────────────

JWT_ALGORITHM = settings.ALGORITHM


class _SessionAdapter:
    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    async def execute(self, *args, **kwargs):
        result = self._session.execute(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def commit(self):
        result = self._session.commit()
        if inspect.isawaitable(result):
            return await result
        return result

    async def flush(self):
        result = self._session.flush()
        if inspect.isawaitable(result):
            return await result
        return result

    async def rollback(self):
        result = self._session.rollback()
        if inspect.isawaitable(result):
            return await result
        return result

    async def close(self):
        result = self._session.close()
        if inspect.isawaitable(result):
            return await result
        return result

    async def delete(self, *args, **kwargs):
        result = self._session.delete(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

def _create_jwt(claims: dict, expires_delta: timedelta) -> str:
    claims["exp"] = datetime.now(timezone.utc) + expires_delta
    claims.setdefault("jti", uuid.uuid4().hex)
    claims.setdefault("iat", datetime.now(timezone.utc))
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)

def _decode_jwt(token: str, verify_exp: bool = True) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM],
                          options={"verify_exp": verify_exp})
    except Exception:
        return None

# ─── Crypto helpers ────────────────────────────────────────────────────────────

async def _hash_password(password: str) -> str:
    return (await asyncio.to_thread(bcrypt.hashpw, password.encode(), bcrypt.gensalt())).decode()

async def _verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(bcrypt.checkpw, plain.encode(), hashed.encode())

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# ─── Password Policy Validation ────────────────────────────────────────────────

def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Returns (is_valid, error_message)."""
    min_len = settings.PASSWORD_MIN_LENGTH
    if len(password) < min_len:
        return False, f"Password must be at least {min_len} characters"
    if settings.PASSWORD_REQUIRE_UPPER and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if settings.PASSWORD_REQUIRE_LOWER and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character"
    return True, None

# ═══════════════════════════════════════════════════════════════════════════════
# Enterprise Auth Service
# ═══════════════════════════════════════════════════════════════════════════════

class EnterpriseAuthService:
    def __init__(self, db: AsyncSession, request_info: dict = None):
        self.db = _SessionAdapter(db)
        self.request_info = request_info or {}

    # ─── Registration ──────────────────────────────────────────────────────────

    async def register(self, email: str, password: str, org_name: str, org_slug: str,
                       send_verification: bool = True) -> User:
        await self._check_auth_rate_limit(email, action="register")

        # Validate password
        valid, err = validate_password_strength(password)
        if not valid:
            raise AuthError(err, 400)

        # Check email uniqueness
        existing = await self._get_user_by_email(email)
        if existing:
            raise AuthError("An account with this email already exists", 409)

        org = Organization(name=org_name, slug=org_slug)
        self.db.add(org)
        await self.db.flush()

        role = await self._get_role(RoleEnum.RECRUITER)

        user = User(
            email=email,
            password_hash=await _hash_password(password),
            org_id=org.id,
            is_active=True,
            email_verified=False,
        )
        if role:
            user.roles = [role]

        self.db.add(user)
        await self.db.flush()

        await self.db.commit()

        # Send verification email
        if send_verification:
            try:
                token = await self._create_email_verification_token(user.id)
                # In production, this would send an email via SMTP
                log.info("email_verification_token_created", user_id=user.id, token_preview=token[:12])
            except Exception as e:
                log.error("email_verification_token_failed", user_id=user.id, error=str(e))

        await self._log_auth_event("register", "success", user.id, user.org_id)
        return user

    # ─── Login ─────────────────────────────────────────────────────────────────

    async def login(self, email: str, password: str, mfa_code: str = None) -> Tuple[dict, UserSession]:
        await self._check_auth_rate_limit(email, action="login")

        stmt = select(User).where(User.email == email).options(
            selectinload(User.roles), selectinload(User.mfa_devices), selectinload(User.oauth_accounts)
        )
        user = (await self.db.execute(stmt)).scalars().first()

        if not user or not user.is_active:
            await self._log_login_attempt(email, False, "not_found")
            raise AuthError("Invalid credentials", 401)

        if user.password_hash:
            if not await _verify_password(password, user.password_hash):
                await self._log_login_attempt(email, False, "bad_password")
                raise AuthError("Invalid credentials", 401)
        else:
            await self._log_login_attempt(email, False, "no_password_set")
            raise AuthError("This account uses social login. Please sign in with Google, GitHub, Microsoft, or LinkedIn.", 401)

        # Check MFA enforcement for admins
        if settings.MFA_ENFORCE_FOR_ADMINS:
            roles = [r.name.value if hasattr(r.name, "value") else str(r.name) for r in user.roles]
            if "ADMIN" in roles:
                mfa_devices = await self._get_user_mfa_devices(user.id)
                if not mfa_devices:
                    await self._log_auth_event("mfa_required_admin", "blocked", user.id, user.org_id)
                    raise AuthError("Administrators must enable MFA. Please contact support.", 403)

        # MFA check
        mfa_devices = await self._get_user_mfa_devices(user.id)
        if mfa_devices:
            if not mfa_code:
                await self._log_auth_event("mfa_challenge", "pending", user.id, user.org_id)
                raise AuthError("MFA required", 403, {"mfa_required": True, "providers": [d.provider.value for d in mfa_devices]})
            if not await self._verify_mfa(user.id, mfa_code):
                await self._log_auth_event("mfa_failed", "failure", user.id, user.org_id)
                raise AuthError("Invalid MFA code", 401)

        tokens, session = await self._create_session(user)
        await self._log_login_attempt(email, True, None)
        await self._log_auth_event("login", "success", user.id, user.org_id)
        return tokens, session

    # ─── OAuth / Social Login ───────────────────────────────────────────────────

    async def oauth_login(self, provider: OAuthProvider, provider_user_id: str,
                          email: str, provider_data: dict = None,
                          org_name: str = None, org_slug: str = None) -> Tuple[dict, UserSession]:
        stmt = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
        oauth = (await self.db.execute(stmt)).scalars().first()

        if oauth:
            user = await self._get_user(oauth.user_id)
            if not user or not user.is_active:
                raise AuthError("Account disabled", 401)
        else:
            user = await self._get_user_by_email(email)
            if not user:
                org = Organization(name=org_name or f"{provider.value.capitalize()} User",
                                   slug=org_slug or f"{email.split('@')[0]}-{secrets.token_hex(4)}")
                self.db.add(org)
                await self.db.flush()
                user = User(email=email, org_id=org.id, email_verified=True, is_active=True)
                self.db.add(user)
                await self.db.flush()
                role = await self._get_role(RoleEnum.RECRUITER)
                if role:
                    user.roles.append(role)

            oauth = OAuthAccount(
                user_id=user.id, provider=provider, provider_user_id=provider_user_id,
                provider_email=email, provider_data=provider_data or {},
            )
            self.db.add(oauth)
            await self.db.flush()

        tokens, session = await self._create_session(user)
        await self._log_auth_event(f"oauth_login_{provider.value}", "success", user.id, user.org_id)
        return tokens, session

    # ─── OAuth State (CSRF Protection) ──────────────────────────────────────────

    async def create_oauth_state(self, provider: str, redirect_uri: str) -> str:
        """Generate a CSRF state token and store it."""
        state = secrets.token_urlsafe(32)
        oauth_state = OAuthState(
            state=state,
            provider=provider,
            redirect_uri=redirect_uri,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        self.db.add(oauth_state)
        await self.db.commit()
        return state

    async def verify_oauth_state(self, state: str, provider: str) -> bool:
        """Verify and consume a CSRF state token."""
        stmt = select(OAuthState).where(
            OAuthState.state == state,
            OAuthState.provider == provider,
            OAuthState.expires_at > datetime.now(timezone.utc),
        )
        record = (await self.db.execute(stmt)).scalars().first()
        if not record:
            return False
        await self.db.delete(record)
        await self.db.commit()
        return True

    # ─── SAML SSO ───────────────────────────────────────────────────────────────

    async def saml_initiate(self, relay_state: str = None) -> Tuple[str, str]:
        """Generate SAML AuthnRequest. Returns (sso_url, saml_request_xml)."""
        if not settings.SAML_ENABLED:
            raise AuthError("SAML is not configured", 501)

        # Build a simple SAML 2.0 AuthnRequest
        request_id = f"_{uuid.uuid4().hex}"
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        acs_url = settings.SAML_SP_ACS_URL
        entity_id = settings.SAML_SP_ENTITY_ID

        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<saml2p:AuthnRequest xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"
                     AssertionConsumerServiceURL="{acs_url}"
                     Destination="{settings.SAML_IDP_SSO_URL}"
                     ForceAuthn="false"
                     ID="{request_id}"
                     IssueInstant="{issue_instant}"
                     ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                     Version="2.0">
    <saml2:Issuer xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">{entity_id}</saml2:Issuer>
    <saml2p:NameIDPolicy AllowCreate="true"
                         Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"/>
</saml2p:AuthnRequest>"""

        # In production: base64-encode and sign with SP's private key
        import base64
        encoded = base64.b64encode(saml_request.encode()).decode()

        return settings.SAML_IDP_SSO_URL, encoded

    async def saml_consume(self, saml_response: str, relay_state: str = None) -> Tuple[dict, UserSession]:
        """
        Consume SAML Response from IdP.
        In production: verify XML signature against IdP's X.509 cert, decrypt assertions.
        For now: parse the base64-decoded XML and extract email/nameid.
        """
        if not settings.SAML_ENABLED:
            raise AuthError("SAML is not configured", 501)

        import base64
        from xml.etree import ElementTree as ET

        try:
            decoded = base64.b64decode(saml_response).decode("utf-8")
            root = ET.fromstring(decoded)

            ns = {
                "saml2": "urn:oasis:names:tc:SAML:2.0:assertion",
                "saml2p": "urn:oasis:names:tc:SAML:2.0:protocol",
            }

            # Extract NameID (email)
            name_id_el = root.find(".//saml2:NameID", ns)
            if name_id_el is None:
                raise AuthError("Invalid SAML response: missing NameID", 400)

            email = name_id_el.text.strip()

            # Extract attributes
            attrs = {}
            attr_stmt = root.find(".//saml2:AttributeStatement", ns)
            if attr_stmt is not None:
                for attr in attr_stmt.findall("saml2:Attribute", ns):
                    attr_name = attr.get("Name", "")
                    attr_val_el = attr.find("saml2:AttributeValue", ns)
                    if attr_val_el is not None and attr_val_el.text:
                        attrs[attr_name] = attr_val_el.text

            # Extract Subject Confirmation (verify timing)
            subj_conf = root.find(".//saml2:SubjectConfirmationData", ns)
            if subj_conf is not None:
                not_on_or_after = subj_conf.get("NotOnOrAfter")
                if not_on_or_after:
                    expiry = datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > expiry:
                        raise AuthError("SAML response has expired", 400)

        except ET.ParseError as e:
            raise AuthError(f"Invalid SAML XML: {e}", 400)

        # Authenticate or create user
        return await self._saml_authenticate_user(email, attrs)

    async def _saml_authenticate_user(self, email: str, attributes: dict) -> Tuple[dict, UserSession]:
        user = await self._get_user_by_email(email)
        if not user:
            org_name = attributes.get("organization", f"SAML User")
            org_slug = attributes.get("org_slug", email.split("@")[0])
            org = Organization(name=org_name, slug=org_slug)
            self.db.add(org)
            await self.db.flush()
            user = User(email=email, org_id=org.id, email_verified=True, is_active=True)
            self.db.add(user)
            await self.db.flush()
            role = await self._get_role(RoleEnum.RECRUITER)
            if role:
                user.roles.append(role)

        tokens, session = await self._create_session(user)
        await self._log_auth_event("saml_login", "success", user.id, user.org_id)
        return tokens, session

    # ─── MFA ────────────────────────────────────────────────────────────────────

    async def setup_totp_mfa(self, user_id: int) -> dict:
        import pyotp
        secret = pyotp.random_base32()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=str(user_id), issuer_name=settings.MFA_TOTP_ISSUER
        )
        device = MFADevice(
            user_id=user_id, provider=MFAProvider.TOTP, name="Authenticator App",
            secret=secret, is_primary=True, is_verified=False,
        )
        self.db.add(device)
        await self.db.commit()
        return {"secret": secret, "uri": uri, "device_id": device.id}

    async def verify_totp_setup(self, user_id: int, device_id: int, code: str) -> bool:
        device = await self.db.get(MFADevice, device_id)
        if not device or device.user_id != user_id:
            return False
        import pyotp
        totp = pyotp.TOTP(device.secret)
        if totp.verify(code):
            device.is_verified = True
            await self.db.commit()
            return True
        return False

    async def generate_backup_codes(self, user_id: int, count: int = None) -> List[str]:
        count = count or settings.MFA_BACKUP_CODES_COUNT
        codes = [f"{secrets.randbelow(10000):04d}-{secrets.randbelow(10000):04d}" for _ in range(count)]
        hashed = [await _hash_password(c) for c in codes]
        device = await self._get_primary_mfa_device(user_id)
        if device:
            device.backup_codes = hashed
            await self.db.commit()
        return codes

    async def _verify_mfa(self, user_id: int, code: str) -> bool:
        device = await self._get_primary_mfa_device(user_id)
        if not device:
            return False
        if device.secret:
            try:
                import pyotp
                totp = pyotp.TOTP(device.secret)
                if totp.verify(code):
                    device.last_used_at = datetime.now(timezone.utc)
                    await self.db.commit()
                    return True
            except Exception:
                pass
        for i, hashed in enumerate(device.backup_codes or []):
            if await _verify_password(code, hashed):
                device.backup_codes = device.backup_codes[:i] + device.backup_codes[i+1:] or []
                await self.db.commit()
                return True
        return False

    async def disable_mfa(self, user_id: int, code: str) -> bool:
        if not await self._verify_mfa(user_id, code):
            return False
        stmt = update(MFADevice).where(
            MFADevice.user_id == user_id
        ).values(is_verified=False)
        await self.db.execute(stmt)
        await self.db.commit()
        await self._log_auth_event("mfa_disabled", "success", user_id)
        return True

    async def _get_primary_mfa_device(self, user_id: int) -> Optional[MFADevice]:
        stmt = select(MFADevice).where(
            MFADevice.user_id == user_id, MFADevice.is_verified == True, MFADevice.is_primary == True,
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _get_user_mfa_devices(self, user_id: int) -> List[MFADevice]:
        stmt = select(MFADevice).where(
            MFADevice.user_id == user_id, MFADevice.is_verified == True,
        )
        return (await self.db.execute(stmt)).scalars().all()

    # ─── Session Management ─────────────────────────────────────────────────────

    async def _create_session(self, user: User) -> Tuple[dict, UserSession]:
        access_expiry = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expiry = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session_expiry = datetime.now(timezone.utc) + timedelta(days=settings.SESSION_ABSOLUTE_TIMEOUT_DAYS)

        roles = [r.name.value for r in user.roles] if user.roles else []

        access_token = _create_jwt({
            "sub": user.email, "org_id": user.org_id, "roles": roles,
            "user_id": user.id, "type": "access",
        }, access_expiry)

        refresh_token = _create_jwt({
            "sub": user.email, "type": "refresh", "user_id": user.id,
        }, refresh_expiry)

        refresh_hash = await _hash_password(refresh_token)

        # Check concurrent session limit
        active_sessions = await self.list_active_sessions(user.id)
        if len(active_sessions) >= settings.SESSION_MAX_CONCURRENT:
            # Revoke oldest session
            oldest = active_sessions[0]
            oldest.status = SessionStatus.REVOKED
            oldest.revoked_reason = "concurrent_limit_exceeded"

        session = UserSession(
            user_id=user.id, session_token=access_token, refresh_token_hash=refresh_hash,
            status=SessionStatus.ACTIVE,
            device_type=DeviceType(self.request_info.get("device_type", "browser")),
            device_name=self.request_info.get("device_name"),
            ip_address=self.request_info.get("ip_address"),
            user_agent=self.request_info.get("user_agent"),
            location=self.request_info.get("location"),
            expires_at=session_expiry,
            mfa_verified=bool(await self._get_user_mfa_devices(user.id)),
        )
        self.db.add(session)
        await self.db.commit()

        return {
            "access_token": access_token, "refresh_token": refresh_token,
            "token_type": "bearer", "expires_in": int(access_expiry.total_seconds()),
        }, session

    async def refresh_session(self, refresh_token: str) -> Tuple[dict, UserSession]:
        payload = _decode_jwt(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthError("Invalid refresh token", 401)

        user = await self._get_user(payload.get("user_id"))
        if not user or not user.is_active:
            raise AuthError("User not found", 401)

        refresh_hash = await _hash_password(refresh_token)
        stmt = select(UserSession).where(UserSession.refresh_token_hash == refresh_hash,
                                          UserSession.status == SessionStatus.ACTIVE)
        old_session = (await self.db.execute(stmt)).scalars().first()
        if old_session:
            old_session.status = SessionStatus.EXPIRED

        return await self._create_session(user)

    async def logout(self, user_id: int, session_token: str = None):
        if session_token:
            stmt = select(UserSession).where(
                UserSession.user_id == user_id, UserSession.session_token == session_token,
            )
            session = (await self.db.execute(stmt)).scalars().first()
            if session:
                session.status = SessionStatus.REVOKED
                session.revoked_reason = "user_logout"
        else:
            stmt = select(UserSession).where(
                UserSession.user_id == user_id, UserSession.status == SessionStatus.ACTIVE,
            )
            sessions = (await self.db.execute(stmt)).scalars().all()
            for s in sessions:
                s.status = SessionStatus.REVOKED
        await self._log_auth_event("logout", "success", user_id)
        await self.db.commit()

    async def logout_all_devices(self, user_id: int):
        stmt = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.status == SessionStatus.ACTIVE,
        )
        sessions = (await self.db.execute(stmt)).scalars().all()
        for s in sessions:
            s.status = SessionStatus.REVOKED
            s.revoked_reason = "user_logout_all"
        await self._log_auth_event("logout_all", "success", user_id)
        await self.db.commit()

    async def list_active_sessions(self, user_id: int) -> List[UserSession]:
        stmt = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.status == SessionStatus.ACTIVE,
        ).order_by(UserSession.last_activity.desc())
        return (await self.db.execute(stmt)).scalars().all()

    async def revoke_session(self, user_id: int, session_id: int):
        session = await self.db.get(UserSession, session_id)
        if session and session.user_id == user_id:
            session.status = SessionStatus.REVOKED
            session.revoked_reason = "user_revoked"
            await self._log_auth_event("session_revoked", "success", user_id)
            await self.db.commit()

    # ─── API Keys ───────────────────────────────────────────────────────────────

    async def create_api_key(self, user_id: int, org_id: int, name: str,
                             scopes: List[str] = None, allowed_ips: List[str] = None,
                             expiry_days: int = 365) -> dict:
        raw_key = f"ats_{secrets.token_hex(32)}"
        key_hash = _hash_token(raw_key)
        key_prefix = raw_key[:12]

        key = APIKey(
            org_id=org_id, user_id=user_id, name=name,
            key_hash=key_hash, key_prefix=key_prefix,
            scopes=scopes or [], allowed_ips=allowed_ips or [],
            expires_at=datetime.now(timezone.utc) + timedelta(days=expiry_days) if expiry_days else None,
        )
        self.db.add(key)
        await self.db.commit()
        await self._log_auth_event("api_key_created", "success", user_id, org_id)
        return {"id": key.id, "name": name, "key": raw_key, "prefix": key_prefix}

    async def list_api_keys(self, user_id: int) -> List[APIKey]:
        stmt = select(APIKey).where(APIKey.user_id == user_id, APIKey.is_active == True)
        return (await self.db.execute(stmt)).scalars().all()

    async def revoke_api_key(self, user_id: int, key_id: int):
        key = await self.db.get(APIKey, key_id)
        if key and key.user_id == user_id:
            key.is_active = False
            await self._log_auth_event("api_key_revoked", "success", user_id)
            await self.db.commit()

    async def verify_api_key(self, raw_key: str) -> Optional[dict]:
        """Validate an API key and return user/org context."""
        key_hash = _hash_token(raw_key)
        stmt = select(APIKey).where(
            APIKey.key_hash == key_hash, APIKey.is_active == True,
        )
        key = (await self.db.execute(stmt)).scalars().first()
        if not key:
            return None
        if key.expires_at and key.expires_at < datetime.now(timezone.utc):
            return None
        if key.allowed_ips and self.request_info.get("ip_address") not in key.allowed_ips:
            return None
        key.last_used_at = datetime.now(timezone.utc)
        key.use_count += 1
        await self.db.commit()
        return {"user_id": key.user_id, "org_id": key.org_id, "scopes": key.scopes}

    # ─── Password Reset ─────────────────────────────────────────────────────────

    async def forgot_password(self, email: str) -> bool:
        """Generate a password reset token. Returns True if user exists (to prevent email enumeration, always return True)."""
        user = await self._get_user_by_email(email)
        if not user:
            # Still return True to prevent user enumeration
            await asyncio.sleep(0.2)  # Timing attack mitigation
            return True

        # Invalidate old tokens
        stmt = update(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used == False,
        ).values(used=True)
        await self.db.execute(stmt)

        # Create new token
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        token = PasswordResetToken(
            user_id=user.id, token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.db.add(token)
        await self.db.commit()

        # In production: send email with raw_token
        log.info("password_reset_token_created", user_id=user.id, token_preview=raw_token[:12])
        await self._log_auth_event("password_reset_requested", "success", user.id, user.org_id)
        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Verify reset token and set new password."""
        valid, err = validate_password_strength(new_password)
        if not valid:
            raise AuthError(err, 400)

        token_hash = _hash_token(token)
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
        reset_token = (await self.db.execute(stmt)).scalars().first()
        if not reset_token:
            raise AuthError("Invalid or expired reset token", 400)

        user = await self._get_user(reset_token.user_id)
        if not user:
            raise AuthError("User not found", 400)

        # Check password history (simple check: not the same as current)
        if user.password_hash and await _verify_password(new_password, user.password_hash):
            raise AuthError("New password cannot be the same as the current password", 400)

        user.password_hash = await _hash_password(new_password)
        reset_token.used = True

        # Revoke all sessions (force re-login)
        await self.logout_all_devices(user.id)

        await self.db.commit()
        await self._log_auth_event("password_reset", "success", user.id, user.org_id)
        return True

    # ─── Email Verification ─────────────────────────────────────────────────────

    async def _create_email_verification_token(self, user_id: int) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        token = EmailVerificationToken(
            user_id=user_id, token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        self.db.add(token)
        await self.db.commit()
        return raw_token

    async def verify_email(self, token: str) -> bool:
        token_hash = _hash_token(token)
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used == False,
            EmailVerificationToken.expires_at > datetime.now(timezone.utc),
        )
        verif_token = (await self.db.execute(stmt)).scalars().first()
        if not verif_token:
            raise AuthError("Invalid or expired verification token", 400)

        user = await self._get_user(verif_token.user_id)
        if not user:
            raise AuthError("User not found", 400)

        user.email_verified = True
        verif_token.used = True
        await self.db.commit()
        await self._log_auth_event("email_verified", "success", user.id, user.org_id)
        return True

    async def resend_verification_email(self, email: str) -> bool:
        user = await self._get_user_by_email(email)
        if not user or user.email_verified:
            return True
        token = await self._create_email_verification_token(user.id)
        log.info("email_verification_resent", user_id=user.id, token_preview=token[:12])
        return True

    # ─── Change Password (authenticated) ────────────────────────────────────────

    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        valid, err = validate_password_strength(new_password)
        if not valid:
            raise AuthError(err, 400)

        user = await self._get_user(user_id)
        if not user or not user.password_hash:
            raise AuthError("User not found", 400)

        if not await _verify_password(current_password, user.password_hash):
            raise AuthError("Current password is incorrect", 400)

        if await _verify_password(new_password, user.password_hash):
            raise AuthError("New password cannot be the same as the current password", 400)

        user.password_hash = await _hash_password(new_password)

        # Revoke all other sessions
        stmt = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.status == SessionStatus.ACTIVE,
        )
        sessions = (await self.db.execute(stmt)).scalars().all()
        for s in sessions:
            s.status = SessionStatus.REVOKED
            s.revoked_reason = "password_changed"

        await self.db.commit()
        await self._log_auth_event("password_changed", "success", user_id, user.org_id)
        return True

    # ─── Rate Limiting ───────────────────────────────────────────────────────────

    async def _check_auth_rate_limit(self, identifier: str, action: str):
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        stmt = select(func.count(LoginAttempt.id)).where(
            LoginAttempt.identifier == identifier,
            LoginAttempt.success == False,
            LoginAttempt.created_at >= cutoff,
        )
        count = (await self.db.execute(stmt)).scalar() or 0
        max_attempts = settings.RATE_LIMIT_AUTH_PER_MINUTE
        if count >= max_attempts:
            await self._log_auth_event(f"rate_limit_blocked_{action}", "blocked", None, None,
                                       details={"identifier": identifier, "failed_attempts": count})
            raise AuthError(f"Too many attempts. Try again in 5 minutes.", 429)

    async def _log_login_attempt(self, identifier: str, success: bool, reason: str = None):
        attempt = LoginAttempt(
            identifier=identifier, ip_address=self.request_info.get("ip_address", "unknown"),
            success=success, failure_reason=reason, user_agent=self.request_info.get("user_agent"),
        )
        self.db.add(attempt)
        await self.db.commit()

    async def _log_auth_event(self, event: str, status: str, user_id: int = None,
                              org_id: int = None, details: dict = None):
        log_entry = AuthAuditLog(
            user_id=user_id, org_id=org_id, event=event, status=status,
            ip_address=self.request_info.get("ip_address"),
            user_agent=self.request_info.get("user_agent"),
            device_type=self.request_info.get("device_type"),
            details=details or {},
        )
        self.db.add(log_entry)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()

    # ─── Internal helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _safe_decode(token: str) -> Optional[dict]:
        return _decode_jwt(token, verify_exp=True)

    async def _get_user(self, user_id: int) -> Optional[User]:
        from sqlalchemy.orm import selectinload
        stmt = select(User).where(User.id == user_id).options(
            selectinload(User.roles),
            selectinload(User.mfa_devices),
            selectinload(User.oauth_accounts)
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email).options(selectinload(User.roles))
        return (await self.db.execute(stmt)).scalars().first()

    async def _get_role(self, role_enum: RoleEnum) -> Optional[Role]:
        stmt = select(Role).where(Role.name == role_enum)
        return (await self.db.execute(stmt)).scalars().first()


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401, extra: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.extra = extra or {}
