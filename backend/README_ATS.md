# AI Applicant Tracking System (ATS) - API Documentation

## Overview
This is a production-grade ATS backend featuring LLM evaluation, multi-agent AI pipeline, and RAG-based candidate retrieval.

## Core Features
1. **Multi-Agent Pipeline**: Specialized agents for parsing, skill evaluation, experience analysis, and scoring.
2. **LLM Evaluation**: Gemini-powered candidate feedback and interview preparation.
3. **RAG Chatbot**: Semantic candidate search using ChromaDB.
4. **Bias Detection**: Identifies gendered language and prestige bias in job descriptions.
5. **JWT Authentication**: Secure role-based access control.

## API Endpoints

### Authentication
- `POST /api/auth/register`: Register a new user.
- `POST /api/auth/token`: Login and receive JWT.

### Resume & Matching
- `POST /api/resume/upload`: Upload and parse a resume.
- `POST /api/match`: Match a candidate against a job description.
- `POST /api/bulk-upload`: Process multiple resumes asynchronously (Celery).

### AI & Analytics
- `POST /api/chat`: Query the candidate vector store (RAG).
- `GET /api/bias-report`: Analyze JD for bias.
- `GET /api/metrics`: Retrieve system screening performance.

## Setup
1. **Docker**: `docker-compose up --build`
2. **Local**: 
   - Backend: `uvicorn app.main:app`
   - Requirements: `pip install -r requirements.txt`
   - ENV: Set `GOOGLE_API_KEY` and `OPENAI_API_KEY`.
