# Resume Screening System

This project is a full-stack, production-ready system for automated resume screening using advanced natural language matching and semantic analysis.

## Features
- **Resume Parsing**: Extract text from PDF/DOCX resumes.
- **Weighted Scoring**: Multi-factor scoring (Skills, Experience, Education, Profile Match).
- **Recruitment Integrity**: Detect exclusionary language in JDs and anonymize candidate data.
- **Hiring Analytics**: Funnel visualization and skill gap analysis.
- **Async Processing**: Handles bulk uploads using Celery and Redis.

## Tech Stack
- **Backend**: FastAPI, Python, Semantic Analysis Logic, Celery, Redis, PostgreSQL.
- **Frontend**: React, Vite, Tailwind CSS, Chart.js.
- **Infrastructure**: Docker, Nginx.

## Getting Started

### Prerequisites
- Docker & Docker Compose

### Fast Start
1. Clone the repository.
2. Run the following command:
   ```bash
   docker-compose up --build
   ```
3. Access the application:
   - Frontend: [http://localhost](http://localhost) (via Nginx)
   - API Docs: [http://localhost/api/docs](http://localhost/api/docs)
   - Monitoring: [http://localhost/metrics](http://localhost/metrics)

## Usage
1. **Upload**: Enter a job title and description, then upload one or more resumes.
2. **Review**: Check the bias detection flags for your job description.
3. **Screen**: Run the screening process.
4. **Results**: View the ranked list of candidates with detailed score breakdowns.
5. **Analytics**: Inspect the hiring funnel and skill proficiency trends.

## Folder Structure
- `backend/`: FastAPI application and core NLP modules.
- `frontend/`: React application and dashboard components.
- `docker-compose.yml`: Multi-service orchestration.
- `nginx.conf`: Reverse proxy configuration.
- `test_data/`: Sample resumes for testing.

## Author
Developed by Antigravity
