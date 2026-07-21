# Production Launch Script - AI ATS Enterprise

$ErrorActionPreference = "Stop"

Write-Host "🚀 Preparing Antigravity AI ATS Production Suite..." -ForegroundColor Cyan

# 1. Check for Docker Daemon
try {
    docker info > $null 2>&1
} catch {
    Write-Host "❌ Error: Docker Desktop is not running." -ForegroundColor Red
    Write-Host "Please start Docker Desktop and run this script again." -ForegroundColor Yellow
    exit 1
}

# 2. Synchronize Environment
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ Warning: .env not found. Copying .env.example..." -ForegroundColor Yellow
    Copy-Item "backend/.env.example" ".env"
}

# 3. Launch Orchestration
Write-Host "🏗️  Building and Launching Containers (8 Microservices)..." -ForegroundColor Green
docker compose up -d --build

# 4. Wait for Health Checks
Write-Host "⏳ Waiting for Database & API Health Checks..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# 5. Open Monitoring Tabs
Write-Host "🌐 Opening Dashboards..." -ForegroundColor Cyan
Start-Process "http://localhost:80"        # React Frontend (via Nginx)
Start-Process "http://localhost:8501"    # Streamlit Analytics
Start-Process "http://localhost:5555"    # Celery Flower Monitor
Start-Process "http://localhost:8080/docs" # API Documentation (OpenAPI)

Write-Host "✅ System is Active!" -ForegroundColor Green
Write-Host "Check http://localhost:8080/health for live status." -ForegroundColor Gray
