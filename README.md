# 🚀 AI Resume Screening & Matching System (Enterprise ATS)

An intelligent, enterprise-grade AI Applicant Tracking & Resume Screening System. The platform parses resumes (PDF, DOCX, DOC, TXT), extracts skills and candidate experience, matches candidate profiles against job requisitions using semantic embeddings (Google Gemini LLM & cosine similarity), computes multidimensional match scores, and provides recruiter-centric dashboards with analytics, candidate rankings, and role-based access control.

---

## 📋 Table of Contents
- [Architecture & Tech Stack](#-architecture--tech-stack)
- [Prerequisites](#-prerequisites)
- [Quickstart (Single Command)](#-quickstart-single-command)
- [Default Endpoints & Credentials](#-default-endpoints--credentials)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## 🛠 Architecture & Tech Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, Axios. Runs at `http://localhost:8081`.
- **Backend**: FastAPI (Python 3.10–3.12), Uvicorn, SQLAlchemy (Async), Alembic, Pydantic v2. Runs at `http://localhost:8000`.
- **AI & NLP Pipeline**:
  - **Google Gemini API** (`gemini-1.5-flash` / `text-embedding-004`): Deep resume entity extraction, semantic embedding calculation, and structured candidate evaluation.
  - **Resume Parsers**: `pypdf`, `pdfplumber`, `python-docx` for robust document parsing with regex and NLP fallback parsing.
  - **Scoring Engine**: Hybrid score combining Cosine Semantic Similarity (40%), Required Skill Coverage (30%), Experience Match (20%), and Education Alignment (10%).
- **Database**:
  - SQLite (`backend/ai_ats.db`) for immediate out-of-the-box local development with automated migrations and seed data.
  - PostgreSQL / Supabase with `pgvector` supported for production enterprise deployments.

---

## 💻 Prerequisites

Ensure you have the following installed on your machine:

1. **Node.js**: `v18.0.0` or higher ([Download Node.js](https://nodejs.org/))
2. **Python**: `3.10`, `3.11`, or `3.12` ([Download Python](https://www.python.org/))
   - *Windows users*: Ensure **"Add Python to PATH"** is checked during installation.
3. **Git**: ([Download Git](https://git-scm.com/))

---

## ⚡ Quickstart (Single Command)

You can run the entire full-stack application with just two standard commands:

```bash
# 1. Clone the repository
git clone https://github.com/Vedanth-JS/AI-Resume-Screening-System.git
cd AI-Resume-Screening-System

# 2. Install root and frontend dependencies
npm install

# 3. Start the entire application (Backend + Frontend)
npm run dev
```

### What `npm run dev` Does Automatically:
1. **Detects Python**: Locates `python`, `py`, or `python3` on your system.
2. **Virtual Environment**: Automatically creates a Python virtual environment (`.venv`) if one does not exist.
3. **Dependency Management**: Installs dependencies from `backend/requirements.txt` and caches the state in `.venv/.requirements_hash` to avoid slow re-installs on subsequent launches.
4. **Database Auto-Initialization**: Initializes the local database schema and seeds initial roles, organizations, recruiter profiles, and sample job listings.
5. **Concurrent Execution**: Launches both the FastAPI backend and Vite frontend concurrently.
6. **Clean Termination**: Gracefully stops all child processes (FastAPI and Vite) when pressing `Ctrl + C`.

---

## 🌐 Default Endpoints & Credentials

| Service | URL | Description |
| :--- | :--- | :--- |
| **Frontend Web App** | [http://localhost:8081](http://localhost:8081) | Interactive ATS recruiter & candidate dashboard |
| **Backend REST API** | [http://localhost:8000](http://localhost:8000) | FastAPI application root & API routes |
| **Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI for exploring and testing API endpoints |
| **Alternative API Docs** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc API documentation |

### Default Recruiter / Admin Login
- **Email**: `admin@ai-ats.com`
- **Password**: `admin123`
- **Role**: `super_admin` / `recruiter`

---

## ⚙️ Configuration & Environment Variables

The repository includes a root [.env.example](file:///.env.example) template. When running in local development, the system automatically defaults to an embedded SQLite database (`backend/ai_ats.db`), meaning **no external database setup is required**.

### Backend Configuration (`backend/.env` or root `.env`)

```env
# Environment Mode
APP_ENV=development
DEBUG=true

# Database Configuration
# Default: Local SQLite (no installation needed)
DATABASE_URL=sqlite+aiosqlite:///backend/ai_ats.db

# Optional: PostgreSQL with pgvector for production
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/ai_ats

# Security & Authentication
SECRET_KEY=dev-insecure-secret-key-change-in-production-min-32-chars-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MFA_ENFORCE_FOR_ADMINS=false

# Google Gemini API Key (Required for AI Parsing & Semantic Embeddings)
# Get your free key at: https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here

# CORS Allowed Origins
CORS_ORIGINS=["http://localhost:8081","http://127.0.0.1:8081","http://localhost:5173","http://127.0.0.1:5173","http://localhost:8000"]
```

### Frontend Configuration (`frontend/.env`)

```env
VITE_API_URL=/api
```

---

## 📂 Project Structure

```text
AI-Resume-Screening-System/
│
├── backend/                        # FastAPI Backend Application
│   ├── alembic/                    # Database migrations
│   ├── app/
│   │   ├── api/                    # API route controllers (auth, resume, jobs, enterprise)
│   │   ├── core/                   # Security, config, parser, scoring, pipeline
│   │   ├── db/                     # Database connection & base classes
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic validation schemas
│   │   └── services/               # Gemini AI service, job fetcher, analytics
│   ├── ai_ats.db                   # Local SQLite database (auto-generated)
│   ├── init_db.py                  # Database bootstrap & schema migration script
│   ├── seed_data.py                # Database seeder (roles, jobs, admin user)
│   ├── main.py                     # Entry point proxy
│   └── requirements.txt            # Python dependencies
│
├── frontend/                       # React 18 + Vite Frontend Application
│   ├── src/
│   │   ├── components/             # UI widgets, layout, navigation, charts
│   │   ├── context/                # Auth and notification React contexts
│   │   ├── pages/                  # Dashboard, resume screening, jobs, analytics
│   │   └── services/               # API client (Axios)
│   ├── package.json                # Frontend npm configuration
│   └── vite.config.ts              # Vite configuration & backend proxying
│
├── scripts/
│   └── setup-and-run.js            # Cross-platform full-stack launcher
│
├── .env.example                    # Environment variables template
├── package.json                    # Root orchestrator npm package.json
└── README.md                       # Project documentation
```

---

## 📖 API Documentation & Core Endpoints

Visit [http://localhost:8000/docs](http://localhost:8000/docs) when the application is running for interactive endpoint testing.

### Authentication
- `POST /api/auth/token` - OAuth2 password bearer token exchange.
- `POST /api/auth/register` - Create recruiter / candidate account.
- `GET /api/auth/me` - Fetch authenticated user profile.

### Resume Screening & Parsing
- `POST /api/resume/upload` - Upload resume (`.pdf`, `.docx`, `.doc`, `.txt`), trigger automated text extraction, AI parsing, and database indexing.
- `POST /api/resume/analyze-jd` - Match an uploaded resume against a target job description and calculate match score with gap analysis.
- `GET /api/resume/{resume_id}` - Retrieve extracted resume profile, skills, and work history.

### Job Management
- `GET /api/jobs` - List open job postings.
- `POST /api/jobs` - Create new job posting with required skills, experience, and department.
- `GET /api/jobs/{job_id}/candidates` - Retrieve ranked candidates scored against a job.

---

## 🔧 Troubleshooting & FAQ

### 1. `python: command not found` or virtual environment not created
- Ensure Python is installed (version 3.10 to 3.12).
- On Windows, verify that Python is added to your environment `PATH`. Run `python --version` or `py --version` in terminal.

### 2. Port Conflicts (Port 8000 or 8081 already in use)
- **Port 8000**: Check if an existing FastAPI or Uvicorn process is running:
  - Windows: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`
  - Linux/Mac: `lsof -i :8000` then `kill -9 <PID>`
- **Port 8081**: Vite will prompt or fallback if port 8081 is occupied, or terminate the blocking process similarly.

### 3. Gemini API Rate Limiting or Invalid Key
- If `GEMINI_API_KEY` is omitted or invalid, the backend's built-in fallback parser will automatically take over using heuristic and rule-based extraction for candidate name, email, phone, and skills.
- To utilize advanced AI scoring and semantic embeddings, create a free API key at [Google AI Studio](https://aistudio.google.com/) and place it in `backend/.env`.

### 4. Admin Login Returns 403 Forbidden
- Ensure `MFA_ENFORCE_FOR_ADMINS=false` is set in `backend/.env` for local development. Default seeded admin accounts do not have TOTP hardware tokens configured out-of-the-box.

### 5. Database Reset / Clean State
If you want to completely reset the local database:
```bash
# Delete the local SQLite database
rm backend/ai_ats.db

# Re-run setup
npm run dev
```
The startup orchestrator will automatically recreate the database tables and re-seed the admin user and sample job descriptions.

---

## 📄 License
This project is licensed under the MIT License.
