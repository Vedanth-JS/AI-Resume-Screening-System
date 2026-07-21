"""
Centralised application settings loaded from environment variables.
Standardized for production-grade security and Pydantic v2 validation.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@db:5432/resume_db"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "pass"
    POSTGRES_DB: str = "resume_db"

    # ─── Redis / Celery ─────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ─── Auth ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── LLM / AI ──────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-1.5-flash"

    # ─── App Runtime ───────────────────────────────────────────────────────
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False

    # ─── Scoring weights (must sum to 1.0) ─────────────────────────────────
    WEIGHT_KEYWORD: float = 0.30
    WEIGHT_SEMANTIC: float = 0.40
    WEIGHT_FORMAT: float = 0.15
    WEIGHT_SECTION: float = 0.15

    # ─── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]

    # ─── File Upload ───────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10

    # ─── Email / SMTP (optional) ───────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    FROM_EMAIL: str = "noreply@ai-ats.local"
    EMAIL_ENABLED: bool = False

    # ─── Monitoring ────────────────────────────────────────────────────────
    FLOWER_BASIC_AUTH: str = "admin:password"
    METRICS_PORT: int = 8080

    # ─── Rate Limiting ─────────────────────────────────────────────────────
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 60

    # ─── OAuth Provider Credentials ────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_BASE: str = "http://localhost:3000/auth/callback"

    # ─── SAML Single Sign-On ───────────────────────────────────────────────
    SAML_ENABLED: bool = False
    SAML_IDP_ENTITY_ID: str = ""
    SAML_IDP_SSO_URL: str = ""
    SAML_IDP_SLO_URL: str = ""
    SAML_IDP_X509_CERT: str = ""
    SAML_SP_ENTITY_ID: str = "ai-ats"
    SAML_SP_ACS_URL: str = "http://localhost:8080/api/auth/saml/acs"
    SAML_SP_SLS_URL: str = "http://localhost:8080/api/auth/saml/sls"

    # ─── Password Policy ───────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPER: bool = True
    PASSWORD_REQUIRE_LOWER: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_MAX_HISTORY: int = 5
    PASSWORD_EXPIRY_DAYS: int = 0  # 0 = never expires

    # ─── MFA Settings ──────────────────────────────────────────────────────
    MFA_ENFORCE_FOR_ADMINS: bool = False
    MFA_ENFORCE_GLOBALLY: bool = False
    MFA_TOTP_ISSUER: str = "AI-ATS"
    MFA_BACKUP_CODES_COUNT: int = 8

    # ─── Session Security ──────────────────────────────────────────────────
    SESSION_MAX_CONCURRENT: int = 10
    SESSION_INACTIVE_TIMEOUT_MINUTES: int = 480
    SESSION_ABSOLUTE_TIMEOUT_DAYS: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
