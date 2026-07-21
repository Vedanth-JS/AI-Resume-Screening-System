<div align="center">
  <h1>🤖 AI Resume Screening System</h1>
  <p><strong>Enterprise-Grade Applicant Tracking System powered by Google Gemini & LangGraph</strong></p>

  [![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
  <br />
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-screenshots">Screenshots</a>
</div>

---

## 🚀 Overview

An intelligent AI-powered Applicant Tracking System that revolutionizes recruitment workflows. Built with **FastAPI**, **React**, and **Google Gemini AI**, it automates resume parsing, skill matching, bias detection, and candidate scoring with enterprise-grade reliability.

### ✨ Key Features

- **🧠 AI-Powered Screening**: Multi-agent pipeline using Gemini-1.5-Flash for intelligent resume parsing and analysis
- **⚡ Bulk Processing**: Screen 100+ resumes in parallel with real-time progress tracking
- **🎯 Smart Matching**: Vector-based semantic search using pgvector embeddings for skill matching
- **🛡️ Bias Detection**: Automated bias detection in job descriptions and candidate evaluations
- **📊 Real-Time Analytics**: Live dashboards with candidate funnel metrics and score distributions
- **🔍 Natural Language Search**: AI chat interface for querying candidates using natural language
- **👮 Enterprise RBAC**: Multi-tenant isolation with Admin, Recruiter, and Viewer roles
- **🎨 Modern UI**: Premium glassmorphism dashboard with responsive design

## � Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | FastAPI (Python 3.11) | High-concurrency async API |
| **Frontend** | React 18 + Vite + TailwindCSS | Modern dashboard UI |
| **AI Models** | Google Gemini 1.5 Flash | Resume parsing & reasoning |
| **Database** | PostgreSQL + pgvector | Relational data & vector embeddings |
| **Task Queue** | Celery + Redis | Asynchronous background processing |
| **Vector Search** | pgvector | Semantic candidate matching |
| **Monitoring** | Flower | Celery task monitoring |

## 🕹 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis
- Google API Key (Gemini)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/vedanth-js/ai-ats.git
   cd ai-ats
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Add your GOOGLE_API_KEY to .env
   python init_db.py
   uvicorn app.main:app --reload --port 8080
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Start Redis (for Celery)**
   ```bash
   redis-server
   ```

5. **Start Celery Worker**
   ```bash
   cd backend
   celery -A app.workers.celery_app worker --loglevel=info
   ```

### Docker Deployment

```bash
docker compose up -d --build
```

Access the application at:
- **Frontend**: http://localhost:4173
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Celery Monitor**: http://localhost:5555

## 📋 Core Features

### Resume Upload & Screening
- **Drag & Drop Upload**: Upload multiple PDF resumes with validation
- **Real-time Progress**: Track parsing, screening, and scoring status
- **Error Handling**: Robust error recovery with retry functionality
- **File Validation**: PDF-only uploads with 10MB size limit

### AI-Powered Analysis
- **Resume Parsing**: Extract candidate details, skills, and experience
- **Skill Matching**: Keyword and semantic-based skill evaluation
- **Experience Scoring**: Compare candidate experience against job requirements
- **Bias Detection**: Identify and flag biased language in job descriptions

### Candidate Management
- **Vector Search**: Natural language search across candidate pool
- **AI Chat**: Query candidates using conversational interface
- **Score Filtering**: Filter candidates by match scores
- **Application Tracking**: Track candidates through hiring pipeline

### Analytics Dashboard
- **Funnel Metrics**: Visualize candidate pipeline stages
- **Score Distribution**: Analyze candidate score distributions
- **Time-to-Hire**: Track recruitment efficiency metrics
- **Skill Trends**: Monitor in-demand skills over time

---

## ✨ Platform Walkthrough

Below are the major modules of the AI Resume Screening System.

## 📸 Application Screenshots

### 🔐 Authentication & Dashboard

<div align="center">

<img src="screenshots/README_01_Login_Dashboard.png" width="100%"/>

</div>

> Secure authentication and a modern recruitment dashboard with real-time ATS metrics.

---

### 🤖 AI Interview & Candidate Management

<div align="center">

<img src="screenshots/README_02_Interview_Candidates.png" width="100%"/>

</div>

> AI-generated interview kits, candidate scoring, smart shortlisting, and recruiter workflow.

---

### 📊 Analytics Dashboard

<div align="center">

<img src="screenshots/README_03_Analytics.png" width="100%"/>

</div>

> Recruitment analytics, hiring funnel, score distribution, hiring trends, and bias monitoring.

---

### 📄 Bulk Resume Screening & AI Chat

<div align="center">

<img src="screenshots/README_04_Upload_AIChat.png" width="100%"/>

</div>

> Upload hundreds of resumes, process them in parallel, and search candidates using natural language.

---

## 🔧 Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/resume_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
GOOGLE_API_KEY=your_google_api_key_here
LLM_MODEL=gemini-1.5-flash

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📄 API Documentation

Interactive API documentation available at `/docs` when running the backend.

### Key Endpoints

- `POST /api/resume/upload` - Upload and screen resume
- `GET /api/jobs` - List job postings
- `POST /api/chat` - AI-powered candidate search
- `GET /api/analytics/overview` - Dashboard metrics

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini AI for powerful language models
- FastAPI for the amazing async framework
- The open-source community for excellent tools

---

<div align="center">
  <sub>Built with ❤️ for modern recruitment teams</sub>
</div>
