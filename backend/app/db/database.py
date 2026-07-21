import inspect
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
from ..core.database_config import create_production_engine, get_database_url


class _SQLiteEngineShim:
    def __init__(self, url: str, engine):
        self.url = url
        self.sync_engine = engine

    async def dispose(self):
        self.sync_engine.dispose()


class _SQLiteSessionAdapter:
    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def commit(self):
        self._session.commit()

    async def flush(self):
        self._session.flush()

    async def rollback(self):
        self._session.rollback()

    async def close(self):
        self._session.close()


class _SQLiteAsyncSessionFactory:
    def __init__(self, maker):
        self._maker = maker

    def __call__(self):
        session = self._maker()

        class _Context:
            async def __aenter__(self_inner):
                return _SQLiteSessionAdapter(session)

            async def __aexit__(self_inner, exc_type, exc, tb):
                if exc_type is not None:
                    session.rollback()
                session.close()

        return _Context()

# ─── Production-Grade Engine ───────────────────────────────────────────────────
# Uses tuned connection pool (20 base + 30 overflow), statement timeouts,
# idle-in-transaction timeouts, JIT disabled for OLTP workloads.
database_url = get_database_url()

if database_url.startswith("sqlite"):
    sync_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_engine = _SQLiteEngineShim(database_url, sync_engine)
    AsyncSessionLocal = _SQLiteAsyncSessionFactory(
        sessionmaker(bind=sync_engine, expire_on_commit=False, autocommit=False, autoflush=False)
    )
else:
    async_engine = create_production_engine()

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
