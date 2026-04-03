"""
FastAPI Application Entry Point - Version 2.1.0
Production-grade AI ATS with multi-tenant RBAC and Async Processing
"""
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from .core.config import settings
from .core.logger import configure_logging, log
from .core.middleware import multi_tenant_middleware
from .db.database import async_engine, get_db
from prometheus_fastapi_instrumentator import Instrumentator

# ─── Bootstrap ────────────────────────────────────────────────────────────────
configure_logging()

app = FastAPI(
    title="AI ATS - Enterprise Talent Cloud",
    description="Multi-tenant AI Applicant Tracking System.",
    version=settings.APP_VERSION,
    docs_url="/docs",
)

# ─── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=multi_tenant_middleware)

# ─── Instrumentation ─────────────────────────────────────────────────────────
Instrumentator().instrument(app).expose(app)

# ─── Startup/Shutdown ──────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log.info("ats_startup", version=settings.APP_VERSION, env=settings.APP_ENV)
    log.info("database_connected", engine=str(async_engine.url))

@app.on_event("shutdown")
async def shutdown():
    log.info("ats_shutdown")
    await async_engine.dispose()

# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check for API, Database, Redis, and Workers.
    """
    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "database": "offline",
        "redis": "offline",
        "workers": "offline",
        "uptime_seconds": 0, # Calculated in next turn
    }
    
    # 1. Check Database
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        health_status["database"] = "online"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"err: {str(e)}"

    # 2. Check Redis & Celery Workers
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        if await r.ping():
            health_status["redis"] = "online"
            
            # Use celery inspect to check active workers
            from .workers.celery_app import celery_app
            i = celery_app.control.inspect()
            stats = i.stats()
            if stats:
                health_status["workers"] = f"online: {len(stats)} active"
            else:
                health_status["workers"] = "error: no workers registered"
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["redis"] = f"err: {str(e)}"
        
    return health_status
# ─── Legacy Alias ─────────────────────────────────────────────────────────────
@app.get("/api/metrics", tags=["Analytics"])
async def metrics_alias(request: Request, db: AsyncSession = Depends(get_db)):
    from .api import analytics
    return await analytics.analytics_overview(request, db, current_user=await analytics.ViewerOnly(request, db))

# ─── Routers ──────────────────────────────────────────────────────────────────
from .api import routes, auth, status, notifications, analytics, audit, bulk, tasks, interviews
from .core.websocket import manager
from fastapi import WebSocket, WebSocketDisconnect

app.include_router(auth.router,          prefix="/api",      tags=["Auth"])
app.include_router(status.router,        prefix="/api",      tags=["Status"])
app.include_router(notifications.router, prefix="/api",      tags=["Notifications"])
app.include_router(routes.router,        prefix="/api",      tags=["ATS Core"])
app.include_router(analytics.router,     prefix="/api",      tags=["Analytics"])
app.include_router(audit.router,         prefix="/api",      tags=["Audit"])
app.include_router(bulk.router,          prefix="/api/v1",   tags=["Bulk & Batches"])
app.include_router(tasks.router,         prefix="/api/v1/tasks", tags=["Task Progress"])
app.include_router(interviews.router,    prefix="/api/v1/interviews", tags=["Interview Assistant"])

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
