"""
Centralised application settings loaded from environment variables.
Standardized for production-grade security and Pydantic v2 validation.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Database ─────────────────────────────────────────────────────────────
    # Default is the docker-compose service name. Override in .env for prod.
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@db:5432/resume_db"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "pass"
    POSTGRES_DB: str = "resume_db"

    # ─── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ─── Auth ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "REPLACE_WITH_SECURE_64_CHAR_STRING_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── LLM / AI ─────────────────────────────────────────────────────────────
    # Required for the system to function
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-1.5-flash"

    # ─── App Runtime ──────────────────────────────────────────────────────────
    APP_ENV: str = "production"         # development | production
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False

    # ─── Scoring weights (must sum to 1.0) ────────────────────────────────────
    WEIGHT_KEYWORD: float = 0.30
    WEIGHT_SEMANTIC: float = 0.40
    WEIGHT_FORMAT: float = 0.15
    WEIGHT_SECTION: float = 0.15

    # ─── Security & Monitoring ────────────────────────────────────────────────
    FLOWER_BASIC_AUTH: str = "admin:password"
    METRICS_PORT: int = 8000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Module-level singleton
settings = get_settings()
