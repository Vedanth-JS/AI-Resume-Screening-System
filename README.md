# 🤖 AI Applicant Tracking System (ATS)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Distributed-37814A?style=for-the-badge&logo=celery&logoColor=white)

**A production-grade AI-powered recruitment platform with semantic resume screening, bias detection, RAG-based candidate chat, and a premium glassmorphism dashboard.**

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **AI Resume Screening** | Multi-agent pipeline: NLP parsing → semantic matching → LLM scoring |
| 📊 **Analytics Dashboard** | Live score distribution charts, top candidate rankings, system health |
| 🔍 **Semantic Search** | Sentence-transformer embeddings + ChromaDB vector retrieval |
| 💬 **RAG Candidate Chat** | Ask natural language questions about your entire candidate pool |
| ⚖️ **Bias Detection** | Neural audit of job descriptions for gendered language & hidden bias |
| 📦 **Bulk Upload** | ZIP-based batch resume processing via Celery async workers |
| 🔒 **JWT Auth** | Role-based access control (Admin / Recruiter / Interviewer) |
| 🎨 **Premium UI** | Glassmorphism dark mode, Chart.js analytics, animated micro-interactions |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                         │
│           React 18 + Vite + Tailwind CSS + Chart.js             │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/REST  (JWT Bearer)
┌─────────────────────▼───────────────────────────────────────────┐
│                    FastAPI Gateway  :8000                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Auth (JWT) │  │  ATS Routes  │  │  Notifications/Status │  │
│  └─────────────┘  └──────┬───────┘  └───────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────▼────────────────────────────────────┐ │
│  │                  ATS Pipeline (Core)                        │ │
│  │  PDF Parser → spaCy NER → SentenceTransformer → LLM Score  │ │
│  └───────────┬───────────────────────────┬─────────────────────┘ │
└──────────────┼───────────────────────────┼─────────────────────-─┘
               │                           │
  ┌────────────▼──────────┐   ┌────────────▼──────────┐
  │  PostgreSQL :5432     │   │  ChromaDB  :8001       │
  │  Users, Jobs,         │   │  Candidate Embeddings  │
  │  Candidates, Scores   │   │  (RAG Vector Store)    │
  └───────────────────────┘   └───────────────────────┘
               │
  ┌────────────▼──────────┐   ┌───────────────────────┐
  │  Redis  :6379         │   │  Celery Worker         │
  │  Task Queue / Cache   │◄──│  Async Resume Processing│
  └───────────────────────┘   └───────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A Google Gemini API key (free at [ai.google.dev](https://ai.google.dev))

### 1. Clone the repo

```bash
git clone https://github.com/your-username/ai-ats-platform.git
cd ai-ats-platform
```

### 2. Configure environment variables

```bash
cp .env.template .env
```

Edit `.env`:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=optional_openai_key
SECRET_KEY=your_random_jwt_secret_here
```

### 3. Launch all services

```bash
docker-compose up --build -d
```

This starts **7 containers** automatically:

| Container | Service | URL |
|---|---|---|
| `pemp-api-1` | FastAPI Backend | http://localhost:8000 |
| `pemp-frontend-1` | React UI | http://localhost:5173 |
| `pemp-db-1` | PostgreSQL | localhost:5432 |
| `pemp-redis-1` | Redis | localhost:6379 |
| `pemp-chromadb-1` | ChromaDB | http://localhost:8001 |
| `pemp-worker-1` | Celery Worker | (background) |
| `pemp-dashboard-1` | Streamlit | http://localhost:8501 |

### 4. Create admin account

```bash
curl -X POST "http://localhost:8000/api/auth/register?email=admin@company.com&password=admin123"
```

### 5. Open the app

Navigate to **http://localhost:5173** and log in with your credentials.

---

## 📋 API Reference

Full interactive docs at **http://localhost:8000/docs**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/token` | Login (JWT) |
| `GET` | `/api/jobs` | List all job postings |
| `POST` | `/api/jobs` | Create new job |
| `GET` | `/api/candidates` | All candidates with scores |
| `POST` | `/api/resume/upload` | Screen a single resume |
| `POST` | `/api/bulk-upload` | Bulk ZIP upload (async) |
| `GET` | `/api/history/{job_id}` | Candidate history for a job |
| `GET` | `/api/metrics` | Score analytics |
| `GET` | `/api/bias-report` | Bias analysis for a job |
| `POST` | `/api/chat` | RAG candidate search |
| `GET` | `/api/status` | System health |

---

## 🛠️ Tech Stack

### Backend
| Technology | Use |
|---|---|
| **FastAPI** | REST API framework |
| **SQLAlchemy** | ORM for PostgreSQL |
| **PyJWT + bcrypt** | Auth & password hashing |
| **spaCy** | NLP entity extraction |
| **SentenceTransformers** | Semantic embeddings (`all-MiniLM-L6-v2`) |
| **ChromaDB** | Vector store for RAG |
| **Celery + Redis** | Async task queue |
| **PyMuPDF** | PDF text extraction |
| **Google Generative AI** | LLM scoring & feedback |
| **LangGraph** | Multi-agent pipeline orchestration |

### Frontend
| Technology | Use |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build tool |
| **Tailwind CSS** | Utility-first styling |
| **Chart.js** | Analytics charts |
| **Framer Motion** | Animations |
| **Lucide React** | Icons |
| **React Router v7** | Client-side routing |
| **Axios** | HTTP client |

---

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (routes, auth, notifications, status)
│   │   ├── core/         # Pipeline, scorer, bias detector, chatbot
│   │   ├── db/           # Database config + CRUD operations
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # LLM service, job fetcher
│   │   ├── tasks/        # Celery async tasks
│   │   └── main.py       # FastAPI app entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/   # React components (Dashboard, Jobs, Candidates, etc.)
│   │   ├── services/     # API client (Axios + JWT interceptors)
│   │   ├── App.jsx       # Router + auth guard
│   │   └── index.css     # Global styles + animations
│   └── Dockerfile
│
├── docker-compose.yml    # Full stack orchestration
└── .env.template         # Environment variable template
```

---

## 🎓 How It Works — Resume Screening Pipeline

```
1. PDF Upload
       ↓
2. Text Extraction (PyMuPDF)
       ↓
3. NLP Parsing (spaCy) — Extract name, email, entities
       ↓
4. Skill Matching — Compare resume skills vs job requirements
       ↓
5. Semantic Scoring (SentenceTransformer) — Cosine similarity
       ↓
6. Experience Analysis — NLP-extracted years vs requirement
       ↓
7. LLM Evaluation (Gemini) — Natural language verdict + feedback
       ↓
8. Final Score = 0.4×skill + 0.35×semantic + 0.15×exp + 0.1×edu
       ↓
9. Store to PostgreSQL + Index in ChromaDB
```

---

## 🔮 Roadmap

- [ ] Email automation (automated rejection/shortlist emails)
- [ ] Calendar integration (interview scheduling)
- [ ] Multi-tenant support
- [ ] Export candidates to CSV/PDF
- [ ] Webhook integrations (Slack, Greenhouse, Lever)
- [ ] Mobile PWA

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">
Built with ❤️ — powered by FastAPI, React, and Google Gemini
</div>
