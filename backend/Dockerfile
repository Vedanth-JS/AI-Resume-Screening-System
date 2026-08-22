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

# Install Core Dependencies (skipping heavy AI/ML libraries to fit Render Free Tier 512MB RAM)
RUN grep -a -vE "torch|spacy|sentence-transformers" requirements.txt > req_core.txt && \
    pip install --default-timeout=1000 --no-cache-dir --prefix=/install -r req_core.txt

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

# Give execution permission to start script
RUN chmod +x start.sh

# Ensure appuser owns the application directory
RUN chown -R appuser:appuser /app

USER appuser

# Expose FastAPI port
EXPOSE 8080

# Health check using curl (installed in runtime)
# Detailed check for API health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["./start.sh"]
