from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router as api_router
from .db.database import Base, engine
# from prometheus_fastapi_instrumentator import Instrumentator

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Screening System")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.on_event("startup")
# async def startup():
#     Instrumentator().instrument(app).expose(app)

# Include Routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Resume Screener API"}
