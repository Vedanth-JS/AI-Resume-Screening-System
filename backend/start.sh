#!/bin/sh

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A app.workers.celery_app worker --loglevel=info -Q screening,notifications,analytics --concurrency=1 &

# Start Uvicorn API in foreground (keeps the container alive)
echo "Starting FastAPI Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1
