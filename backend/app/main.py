"""
FastAPI Application Entry Point — AI ATS v2.1.0
Multi-tenant RBAC, async processing, SSE progress tracking.
"""
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from .core.config import settings
from .core.logger import configure_logging, log
from .core.middleware import multi_tenant_middleware
from .core.security import SecurityHeadersMiddleware, CSPMiddleware, get_cors_config
from .core.api_middleware import RequestIDMiddleware, RequestLoggingMiddleware, register_exception_handlers
from .db.database import async_engine, get_db
from .core.auth_dependencies import get_current_user_hybrid
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from .db.database import AsyncSessionLocal
from .models.models import User

# ─── Bootstrap ────────────────────────────────────────────────────────────────
configure_logging()

app = FastAPI(
    title="AI ATS — Enterprise Talent Cloud",
    description="Multi-tenant AI Applicant Tracking System.",
    version=settings.APP_VERSION,
    docs_url="/docs",
)

# Register global exception handlers
register_exception_handlers(app)

# ─── Middleware ────────────────────────────────────────────────────────────────
# CORS: restrict in production, allow all in dev
if settings.APP_ENV == "production":
    cors_origins = getattr(settings, "CORS_ORIGINS", ["*"])
else:
    cors_origins = ["*"]

# Security headers MUST be first (outermost)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSPMiddleware)

# CORS with production-safe configuration
cors_config = get_cors_config() if settings.APP_ENV == "production" else {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
    "allow_headers": ["Authorization", "Content-Type", "X-API-Key", "X-Device-Name"],
}
app.add_middleware(CORSMiddleware, **cors_config)

app.add_middleware(GZipMiddleware, minimum_size=1000)
# API observability middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(BaseHTTPMiddleware, dispatch=multi_tenant_middleware)

# ─── File upload size limit (10 MB) ──────────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > 10 * 1024 * 1024:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={"detail": "File too large. Maximum 10 MB allowed."},
                )
        return await call_next(request)

app.add_middleware(MaxBodySizeMiddleware)

# ─── Instrumentation ─────────────────────────────────────────────────────────
Instrumentator().instrument(app).expose(app)

# ─── Startup / Shutdown ──────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log.info("ats_startup", version=settings.APP_VERSION, env=settings.APP_ENV)
    log.info("database_engine", url=str(async_engine.url))

@app.on_event("shutdown")
async def shutdown():
    log.info("ats_shutdown")
    await async_engine.dispose()

# ─── Health Check ────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health(db: AsyncSession = Depends(get_db)):
    health_status = {
        "status": "ok",
        "version": settings.APP_VERSION,
        "database": "offline",
        "redis": "offline",
        "workers": "offline",
    }

    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        health_status["database"] = "online"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {e}"

    if "sqlite" in str(async_engine.url):
        return health_status

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        if await r.ping():
            health_status["redis"] = "online"
            from .workers.celery_app import celery_app
            i = celery_app.control.inspect()
            stats = i.stats()
            if stats:
                health_status["workers"] = f"online ({len(stats)} active)"
            else:
                health_status["workers"] = "no workers"
                health_status["status"] = "degraded"
        await r.close()
    except Exception as e:
        health_status["redis"] = f"error: {e}"
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/me")
async def me(current_user = Depends(get_current_user_hybrid)):
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


# ─── Routers ──────────────────────────────────────────────────────────────────
from .api import routes, auth, status, notifications, analytics, audit, bulk, tasks, interviews, enterprise, saved_searches
from .core.websocket import manager

app.include_router(auth.router,          prefix="/api",      tags=["Auth"])
app.include_router(status.router,        prefix="/api",      tags=["Status"])
app.include_router(notifications.router, prefix="/api",      tags=["Notifications"])
app.include_router(routes.router,        prefix="/api",      tags=["ATS Core"])
app.include_router(analytics.router,     prefix="/api",      tags=["Analytics"])
app.include_router(audit.router,         prefix="/api/v1",   tags=["Audit"])
app.include_router(bulk.router,          prefix="/api/v1",   tags=["Bulk & Batches"])
app.include_router(tasks.router,         prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(interviews.router,    prefix="/api/v1/interviews", tags=["Interviews"])
app.include_router(enterprise.router,    prefix="",          tags=["Enterprise"])
app.include_router(saved_searches.router, prefix="/api",     tags=["Saved Searches"])


# ─── ATS v2 Routes ────────────────────────────────────────────────────────────
from .api.ats import router as ats_router
app.include_router(ats_router, tags=["ATS v2"])

# ─── WebSocket with JWT Auth ──────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Authenticate WebSocket via JWT Bearer token in query param."""
    from .services.auth_service import EnterpriseAuthService
    from sqlalchemy import select
    from .models.auth_models import UserSession, SessionStatus

    # Validate JWT
    svc = EnterpriseAuthService.__new__(EnterpriseAuthService)
    payload = svc._safe_decode(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Verify user exists and session is active
    async with AsyncSessionLocal() as db:
        user = await db.get(User, payload.get("user_id"))
        if not user or not user.is_active:
            await websocket.close(code=4001, reason="User not found")
            return

        stmt = select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.session_token == token,
            UserSession.status == SessionStatus.ACTIVE,
        )
        session = (await db.execute(stmt)).scalars().first()
        if not session:
            await websocket.close(code=4001, reason="Session expired")
            return

        await manager.connect(user.id, websocket)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(user.id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
