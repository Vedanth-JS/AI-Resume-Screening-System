# ─── Stage 1: Build Base Dependencies ──────────────────────────────────────────
FROM python:3.11-slim as builder

WORKDIR /app

# Upgrade pip and install common build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Split Requirements to optimize layer caching
COPY requirements.txt .

# 1. Install Heavy AI Dependencies first (Less frequent changes)
RUN grep -a -E "torch|spacy|sentence-transformers" requirements.txt > req_ai.txt && \
    pip install --no-cache-dir --prefix=/install --extra-index-url https://download.pytorch.org/whl/cpu -r req_ai.txt

# 2. Install Remaining Core Dependencies
RUN grep -a -vE "torch|spacy|sentence-transformers" requirements.txt > req_core.txt && \
    pip install --no-cache-dir --prefix=/install -r req_core.txt

# 3. Download Spacy Model
RUN pip install --no-cache-dir --prefix=/install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# ─── Stage 2: Production Runtime ───────────────────────────────────────────────
FROM python:3.11-slim as runtime

WORKDIR /app

# Setup non-root user for production security
RUN useradd -m -u 1000 appuser && \
    apt-get update && apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local
COPY . .

# Ensure appuser owns the application directory
RUN chown -R appuser:appuser /app

USER appuser

# Expose FastAPI port
EXPOSE 8080

# Health check using curl (installed in runtime)
# Detailed check for API health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
