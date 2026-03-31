@echo off
echo Starting AI ATS Services (Docker Compose) in separate Windows terminal windows...

:: 1. Database (Postgres)
echo [1/7] Database...
start "AI ATS - Database" cmd /k "docker-compose up db"
timeout /t 5

:: 2. Redis
echo [2/7] Redis...
start "AI ATS - Redis" cmd /k "docker-compose up redis"

:: 3. ChromaDB
echo [3/7] ChromaDB...
start "AI ATS - ChromaDB" cmd /k "docker-compose up chromadb"
timeout /t 5

:: 4. Backend API
echo [4/7] Backend API...
start "AI ATS - API" cmd /k "docker-compose up api"

:: 5. Celery Worker (Asynchronous Tasks)
echo [5/7] Celery Worker...
start "AI ATS - Worker" cmd /k "docker-compose up worker"

:: 6. Streamlit Dashboard
echo [6/7] Dashboard...
start "AI ATS - Dashboard" cmd /k "docker-compose up dashboard"

:: 7. Frontend (Vite/React)
echo [7/7] Frontend...
start "AI ATS - Frontend" cmd /k "docker-compose up frontend"

echo.
echo All 7 services have been launched in separate terminal windows.
echo Keep those windows open to see the logs and maintain the services.
echo.
pause
