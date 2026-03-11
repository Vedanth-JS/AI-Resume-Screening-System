# RecruitAI - AI-Powered Resume Screening System

A premium resume screening platform for HR teams that evaluates candidates using Claude AI.

## Features
- **Job Creation**: Define roles with specific skills and experience levels.
- **AI Screening**: Seamlessly evaluate PDF resumes against job requirements.
- **Ranked Pipeline**: View candidates sorted by AI-generated match scores.
- **HR Analytics**: Visualize your hiring funnel and candidate distribution.
- **Re-screening**: Update job criteria and re-evaluate existing candidates without re-uploading.

## Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL**
- **Anthropic API Key**

## Setup Instructions

### 1. Database Setup
Create a PostgreSQL database named `resume_screener`.
```sql
CREATE DATABASE resume_screener;
```

### 2. Backend Configuration
1. Navigate to the `backend` folder.
2. Create a `.env` file from the template:
   ```powershell
   cd backend
   cp .env.example .env
   ```
3. Edit `.env` and provide your:
   - `DATABASE_URL` (e.g., `postgresql://user:pass@localhost:5432/resume_screener`)
   - `ANTHROPIC_API_KEY` (Your Claude API key)

### 3. Run the Backend
```powershell
cd backend
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.

### 4. Run the Frontend
```powershell
cd frontend
npm install
npm run dev
```
The dashboard will be available at `http://localhost:5173`.

## Architecture
- **Frontend**: React + Tailwind CSS + Recharts
- **Backend**: FastAPI + SQLAlchemy + pdfplumber
- **Database**: PostgreSQL
