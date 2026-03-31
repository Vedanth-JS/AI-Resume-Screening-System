# Project Specification: AI Applicant Tracking System (ATS)

## Project Overview
This is a full-stack AI-powered Applicant Tracking System that uses microservices to parse resumes, analyze skills, evaluate experience, and detect bias in job descriptions.

## Goals
1. Finalize Docker deployment and orchestration.
2. Ensure consistent dependency management for AI/ML libraries.
3. Provide a unified frontend/dashboard for candidate screening.

## Technical Stack
- **Backend**: FastAPI, Celery, Redis, PostgreSQL, SQLAlchemy.
- **AI**: Gemini API, OpenAI API, LangChain, ChromaDB.
- **Libraries**: PyMuPDF, NLTK, Spacy, Sentence-Transformers.
- **Frontend**: Streamlit (Dashboard) and Vite-based React application.
- **Ops**: Docker, Docker Compose.

## Constraints
- Must handle standard PDF/Docx resumes.
- Must operate securely with JWT authentication.
- Must detect bias in JOB descriptions.
