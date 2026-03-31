"""
FastAPI Application Entry Point
Version 2.0.0 — Production-grade AI ATS
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from .core.config import settings
from .core.logger import configure_logging, log
from .db.database import engine
from .models.models import Base

# Bootstrap structured logging first
configure_logging()

app = FastAPI(
    title="AI Applicant Tracking System",
    description=(
        "Production-grade AI ATS with multi-agent LangGraph pipeline, "
        "4-component ATS scoring, RAG candidate search, and bias detection."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
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

# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log.info("ats_startup", version=settings.APP_VERSION, env=settings.APP_ENV)
    # Create all tables (Alembic handles migrations in production;
    # create_all is safe as a fallback for dev/first-run)
    Base.metadata.create_all(bind=engine)
    log.info("database_ready")

@app.on_event("shutdown")
async def shutdown():
    log.info("ats_shutdown")

# ─── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def read_root():
    return {
        "status":  "online",
        "service": "AI ATS Backend",
        "version": settings.APP_VERSION,
        "docs":    "/docs",
    }

# ─── Routers ──────────────────────────────────────────────────────────────────
from .api import routes, auth, status, notifications, analytics

app.include_router(auth.router,          prefix="/api/auth",      tags=["Auth"])
app.include_router(status.router,        prefix="/api",           tags=["Status"])
app.include_router(notifications.router, prefix="/api",           tags=["Notifications"])
app.include_router(routes.router,        prefix="/api",           tags=["ATS"])
app.include_router(analytics.router,     prefix="/api",           tags=["Analytics"])

log.info("routers_registered")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
