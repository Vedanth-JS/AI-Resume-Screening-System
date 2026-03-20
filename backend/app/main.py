from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from .api import routes
from .db.database import Base, engine
# from prometheus_fastapi_instrumentator import Instrumentator

# Create database tables is now handled in the startup event or manually
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Screening System")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Only create tables if we are not in a test environment or if we want auto-migration
    Base.metadata.create_all(bind=engine)

# Include Routes
app.include_router(routes.router, prefix="/api")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    print(f"\nVALIDATION ERROR DETAILS: {errors}\n")
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Resume Screener API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
