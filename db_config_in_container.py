"""
Production-Grade Database Configuration — Connection pooling, statement timeouts,
idle transaction termination, prepared statement caching, and query optimization.

Override settings via environment variables:
  DB_POOL_SIZE=20
  DB_MAX_OVERFLOW=30
  DB_POOL_TIMEOUT=30
  DB_STATEMENT_TIMEOUT_MS=30000
  DB_IDLE_IN_TRANSACTION_TIMEOUT_MS=60000
"""
import os
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from ..core.config import settings
from ..core.logger import log


# ─── Pool Settings (production-tuned) ─────────────────────────────────────────

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))
IDLE_IN_TRANSACTION_TIMEOUT_MS = int(os.getenv("DB_IDLE_IN_TRANSACTION_TIMEOUT_MS", "60000"))


def get_database_url() -> str:
    """Build the database URL from settings or env vars."""
    url = os.getenv("DATABASE_URL", settings.DATABASE_URL)

    # Ensure asyncpg driver
    if "postgresql://" in url and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "postgres://" in url and "+asyncpg" not in url:
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    return url


def create_production_engine() -> AsyncEngine:
    """Create an async engine tuned for production workloads.

    Pool sizing rules of thumb for PostgreSQL:
      pool_size = 20 (2 * CPU cores for typical 8-core server)
      max_overflow = 30 (handles spikes without overwhelming DB)
      pool_pre_ping = True (validates connections before use)
      pool_recycle = 3600 (prevents stale connections after 1 hour)

    100K concurrent users scenario:
      - Nginx → 2 Uvicorn workers → each shares the 20-50 connection pool
      - Connections are short-lived (async queries complete in <50ms)
      - 20 connections × 2 workers × 50 req/s per connection ≈ 2000 req/s sustained
    """
    database_url = get_database_url()
    is_sqlite = database_url.startswith("sqlite:")

    if is_sqlite:
        engine_kwargs = {
            "connect_args": {"check_same_thread": False},
            "poolclass": NullPool,
        }
    else:
        engine_kwargs = {
            # Async engines use SQLAlchemy's async-adapted pool by default.
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "pool_timeout": POOL_TIMEOUT,
            "pool_recycle": POOL_RECYCLE,
            "pool_pre_ping": True,
            "connect_args": {
                "timeout": 10,  # connection timeout
                "command_timeout": STATEMENT_TIMEOUT_MS / 1000,  # per-query timeout
                "server_settings": {
                    "application_name": "ai-ats-api",
                    "statement_timeout": str(STATEMENT_TIMEOUT_MS),
                    "idle_in_transaction_session_timeout": str(IDLE_IN_TRANSACTION_TIMEOUT_MS),
                    "jit": "off",  # JIT compilation overhead for OLTP — disable
                },
            },
        }

    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        **engine_kwargs,
    )

    # Post-connection initialization
    if not is_sqlite:
        @event.listens_for(engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Set session-level parameters on every new connection."""
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SET application_name = 'ai-ats-api';")
                cursor.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS};")
                cursor.execute(f"SET idle_in_transaction_session_timeout = {IDLE_IN_TRANSACTION_TIMEOUT_MS};")
            finally:
                cursor.close()

    log.info(
        "database_engine_created",
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        statement_timeout_ms=STATEMENT_TIMEOUT_MS,
        idle_in_transaction_timeout_ms=IDLE_IN_TRANSACTION_TIMEOUT_MS,
    )

    return engine


# ─── Query Performance Helpers ────────────────────────────────────────────────

async def check_query_plan(engine: AsyncEngine, query: str) -> str:
    """Run EXPLAIN ANALYZE on a query for optimization."""
    async with engine.connect() as conn:
        result = await conn.execute(text(f"EXPLAIN ANALYZE {query}"))
        return "\n".join(str(row[0]) for row in result.fetchall())


async def get_pool_stats(engine: AsyncEngine) -> dict:
    """Get current connection pool statistics."""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow(),
        "usage_percent": round(pool.checkedout() / max(pool.size(), 1) * 100, 1),
    }
