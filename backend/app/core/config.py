"""
Centralised application settings loaded from environment variables.
All components import from here — no more scattered os.getenv() calls.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://user:pass@db:5432/resume_db"

    # ─── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ─── Auth ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── LLM / AI ─────────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ─── ChromaDB ─────────────────────────────────────────────────────────────
    CHROMA_DB_URL: str = "http://chromadb:8000"
    CHROMA_DATA_PATH: str = "vector_db"

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"         # development | production
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "2.0.0"

    # ─── Scoring weights (must sum to 1.0) ────────────────────────────────────
    WEIGHT_KEYWORD: float = 0.30
    WEIGHT_SEMANTIC: float = 0.40
    WEIGHT_FORMAT: float = 0.15
    WEIGHT_SECTION: float = 0.15


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Module-level singleton for easy import
settings = get_settings()
