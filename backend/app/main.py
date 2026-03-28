from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.database import engine
from .models.models import Base
from .api import routes, auth

app = FastAPI(title="AI Applicant Tracking System (ATS)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Automatically create tables for the upgraded ATS
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"status": "online", "service": "AI ATS Backend"}

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(routes.router, prefix="/api", tags=["ATS"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
