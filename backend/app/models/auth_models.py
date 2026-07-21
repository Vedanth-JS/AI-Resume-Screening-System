"""
Authentication Models — OAuth accounts, MFA devices, sessions, API keys, devices.
"""
from sqlalchemy import (
    String, Text, ForeignKey, DateTime, Boolean, Integer, Column, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from typing import List, Optional
from ..db.database import Base
from .models import TimestampMixin, SafeJSONB
import enum
import uuid


class MFAProvider(str, enum.Enum):
    TOTP = "TOTP"
    SMS = "SMS"
    EMAIL = "EMAIL"
    WEBAUTHN = "WEBAUTHN"


class OAuthProvider(str, enum.Enum):
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    LINKEDIN = "linkedin"
    SAML = "saml"


class DeviceType(str, enum.Enum):
    BROWSER = "browser"
    MOBILE = "mobile"
    API = "api"
    DESKTOP = "desktop"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


# ─── Models ────────────────────────────────────────────────────────────────────


class OAuthAccount(Base, TimestampMixin):
    """Link between a User and an OAuth provider identity."""
    __tablename__ = "oauth_accounts"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[OAuthProvider] = mapped_column(SAEnum(OAuthProvider))
    provider_user_id: Mapped[str] = mapped_column(String(255), index=True)
    provider_email: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_data: Mapped[dict] = mapped_column(SafeJSONB, default=dict)

    __table_args__ = (
        Index("ix_oauth_provider_user", "provider", "provider_user_id", unique=True),
    )

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")


class MFADevice(Base, TimestampMixin):
    """MFA device or method registered for a user."""
    __tablename__ = "mfa_devices"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[MFAProvider] = mapped_column(SAEnum(MFAProvider))
    name: Mapped[str] = mapped_column(String(100))  # e.g., "Authy", "SMS +1-555-0199"
    secret: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # TOTP secret
    is_primary: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    backup_codes: Mapped[dict] = mapped_column(SafeJSONB, default=list)  # hashed

    user: Mapped["User"] = relationship(back_populates="mfa_devices")


class UserSession(Base, TimestampMixin):
    """Track user sessions for security monitoring."""
    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus), default=SessionStatus.ACTIVE)
    device_type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType))
    device_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[dict]] = mapped_column(SafeJSONB, nullable=True)  # {city, region, country}
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    mfa_verified: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
        Index("ix_sessions_expiry", "expires_at"),
    )

    user: Mapped["User"] = relationship(back_populates="sessions")


class APIKey(Base, TimestampMixin):
    """API keys for programmatic access with fine-grained permissions."""
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12))  # First 8 chars for display
    scopes: Mapped[dict] = mapped_column(SafeJSONB, default=list)  # ["read:candidates", "write:jobs"]
    allowed_ips: Mapped[dict] = mapped_column(SafeJSONB, default=list)  # CIDR whitelist
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    use_count: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "is_active"),
    )


class AuthAuditLog(Base, TimestampMixin):
    """Security-specific audit log for authentication events."""
    __tablename__ = "auth_audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    org_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(100))  # login, logout, mfa_challenge, mfa_success, token_refresh, oauth_link, sso_login
    status: Mapped[str] = mapped_column(String(20))  # success, failure, blocked
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    details: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    risk_score: Mapped[float] = mapped_column(default=0.0)

    __table_args__ = (
        Index("ix_auth_audit_user_time", "user_id", "created_at"),
        Index("ix_auth_audit_org_time", "org_id", "created_at"),
    )


class LoginAttempt(Base, TimestampMixin):
    """Track failed/successful login attempts for rate limiting."""
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    identifier: Mapped[str] = mapped_column(String(255), index=True)  # email or IP
    ip_address: Mapped[str] = mapped_column(String(45))
    success: Mapped[bool] = mapped_column(default=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_login_attempts_identifier_time", "identifier", "created_at"),
    )


class PasswordResetToken(Base, TimestampMixin):
    """One-time password reset token."""
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)


class EmailVerificationToken(Base, TimestampMixin):
    """Email verification token."""
    __tablename__ = "email_verification_tokens"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)


class OAuthState(Base, TimestampMixin):
    """OAuth state parameter for CSRF protection."""
    __tablename__ = "oauth_states"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    state: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(20))
    redirect_uri: Mapped[str] = mapped_column(String(512))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
