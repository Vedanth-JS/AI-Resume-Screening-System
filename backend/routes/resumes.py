import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Candidate
from schemas import CandidateOut
from pdf_service import extract_text, extract_name_email
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload", response_model=CandidateOut)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()

    try:
        resume_text = extract_text(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract text from PDF: {str(e)}")

    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="PDF appears to be empty or unreadable")

    name, email = extract_name_email(resume_text)

    # Save file
    safe_filename = f"{db.query(Candidate).count()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    candidate = Candidate(
        name=name,
        email=email,
        resume_text=resume_text,
        file_path=file_path,
        original_filename=file.filename,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate
