# AI ATS — Production Deployment Guide v2.1.0

Enterprise-grade AI Applicant Tracking System. Production-ready, cloud-native, globally scalable.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Docker Compose)](#quick-start-docker-compose)
4. [Production Deployment (Kubernetes)](#production-deployment-kubernetes)
5. [Cloud Infrastructure (Terraform)](#cloud-infrastructure-terraform)
6. [Configuration Reference](#configuration-reference)
7. [Security Hardening](#security-hardening)
8. [Monitoring & Alerting](#monitoring--alerting)
9. [Scaling & Performance](#scaling--performance)
10. [Backup & Disaster Recovery](#backup--disaster-recovery)
11. [Compliance](#compliance)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
                        ┌──────────────┐
                        │   Cloudflare  │  (CDN + DDoS Protection)
                        │   / AWS CF    │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │    Nginx      │  (TLS Termination, Rate Limiting, WAF)
                        │   :80/:443    │
                        └──┬────────┬──┘
                           │        │
              ┌────────────▼──┐  ┌──▼──────────────┐
              │  Frontend      │  │  API (×2)        │
              │  React SPA     │  │  FastAPI + Uvicorn│
              │  :3000         │  │  :8000            │
              └────────────────┘  └──┬───────────────┘
                                     │
                         ┌───────────┼───────────┐
                         │           │           │
                    ┌────▼────┐ ┌───▼────┐ ┌───▼──────┐
                    │PostgreSQL│ │ Redis  │ │ ChromaDB │
                    │+pgvector │ │ Cache  │ │ Vector   │
                    │  :5432   │ │ :6379  │ │  :8001   │
                    └──────────┘ └────────┘ └──────────┘
                         │
                    ┌────▼─────────────┐
                    │  Celery Workers   │
                    │  (screening,      │
                    │   notifications,  │
                    │   analytics)      │
                    └──────────────────┘
                         │
                    ┌────▼────┐
                    │  Gemini  │  (AI/LLM)
                    │  API     │
                    └─────────┘
```

### Tech Stack
| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 18 + Vite + TailwindCSS | SPA with code splitting |
| API | FastAPI (Python 3.12) | Async REST + WebSocket |
| Auth | JWT + OAuth 2.0 + SAML + MFA | Enterprise SSO |
| Database | PostgreSQL 15 + pgvector | Relational + vector search |
| Cache | Redis 7 | Session store + response cache + Celery broker |
| Queue | Celery + Redis | Async task processing |
| AI | Gemini 1.5 Flash | Resume parsing, scoring, bias detection |
| Vector DB | ChromaDB | Semantic search |
| Monitoring | Grafana + Prometheus + Loki | Metrics, logs, alerts |
| IaC | Terraform (GCP) | Infrastructure as code |
| Orchestration | Kubernetes (Helm) | Container orchestration |
| CI/CD | GitHub Actions | Automated build, test, deploy |

---

## Quick Start (Docker Compose)

### Prerequisites
- Docker 24+ and Docker Compose v2
- Git
- 8 GB RAM, 4 CPU cores recommended

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Vedanth-JS/AI-Resume-Screening-System.git
cd AI-Resume-Screening-System

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY, GOOGLE_API_KEY, DB credentials

# 3. Generate SSL certificates for nginx
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem \
  -subj "/CN=localhost"

# 4. Start production stack
docker compose up -d

# 5. Run database migrations
docker compose exec api alembic upgrade head

# 6. Seed initial data (optional)
docker compose exec api python seed_data.py

# 7. Verify health
curl http://localhost/api/health
# → {"status":"healthy","version":"2.1.0","database":"online","redis":"online"}

# 8. Start monitoring stack (optional)
docker compose -f docker-compose.yml -f deploy/monitoring/docker-compose.monitoring.yml up -d
```

### Access Points
| Service | URL | Credentials |
|---|---|---|
| Frontend | https://localhost | — |
| API Docs | https://localhost/docs | — |
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | — |
| Flower (Celery) | http://localhost:5555 | admin/password |

---

## Production Deployment (Kubernetes)

### Prerequisites
- Kubernetes 1.28+ cluster
- Helm 3.12+
- kubectl configured
- cert-manager installed
- nginx-ingress controller

### Deploy with Helm

```bash
# 1. Add Helm repo (or use local chart)
cd deploy/kubernetes/helm

# 2. Configure values
cp ai-ats/values.yaml ai-ats/values-prod.yaml
# Edit values-prod.yaml:
#   - Set config.secretKey to a strong random string
#   - Set postgresql.auth.password
#   - Set ingress.hosts with your domain
#   - Enable TLS with cert-manager

# 3. Create namespace
kubectl create namespace ai-ats-production

# 4. Create secrets
kubectl create secret generic ai-ats-secrets \
  --namespace ai-ats-production \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=gemini-api-key=<your-key> \
  --from-literal=db-password=$(openssl rand -base64 24)

# 5. Install chart
helm install ai-ats ./ai-ats \
  --namespace ai-ats-production \
  --values ai-ats/values-prod.yaml \
  --wait

# 6. Verify
kubectl get pods -n ai-ats-production
helm test ai-ats -n ai-ats-production
```

### Blue-Green Deployment

```bash
# Deploy new version without downtime
./deploy/scripts/blue-green-deploy.sh v2.1.1 production

# Monitor canary deployment
./deploy/scripts/canary-deploy.sh v2.1.1 10  # 10% traffic

# Rollback if needed
kubectl patch svc ai-ats-api -n ai-ats-production \
  -p '{"spec":{"selector":{"deployment":"blue"}}}'
```

### Autoscaling Configuration

```yaml
# Automatic HPA based on CPU and memory
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

---

## Cloud Infrastructure (Terraform)

### Prerequisites
- Google Cloud SDK installed and configured
- Terraform 1.5+
- GCP Project with billing enabled
- Required APIs enabled: Compute, GKE, Cloud SQL, Redis, Artifact Registry

### Deploy Infrastructure

```bash
cd deploy/terraform

# 1. Configure variables
cat > terraform.tfvars << EOF
project_id = "your-gcp-project-id"
region     = "us-central1"
zone       = "us-central1-a"
node_count = 3
min_nodes  = 2
max_nodes  = 10
EOF

# 2. Initialize and plan
terraform init
terraform plan -out=tfplan

# 3. Apply (creates: VPC, GKE, Cloud SQL, Memorystore, Artifact Registry)
terraform apply tfplan

# 4. Configure kubectl
gcloud container clusters get-credentials ai-ats-cluster \
  --zone us-central1-a

# 5. Get connection details
terraform output postgres_connection_name
terraform output redis_host
terraform output db_password_secret  # sensitive
```

### Resources Created
| Resource | Specification | Purpose |
|---|---|---|
| GKE Cluster | Regional, autopilot | Container orchestration |
| Node Pool | e2-standard-4, SSD, 2-10 nodes | Compute |
| Cloud SQL | PostgreSQL 15 + pgvector, 2 vCPU, 8 GB | Primary database |
| Memorystore | Redis 7, Standard HA, 2 GB | Caching + queues |
| Artifact Registry | Docker repository | Container images |
| VPC | Custom subnet with secondary ranges | Network isolation |
| Service Accounts | IAM roles for Cloud SQL + Redis | Least privilege |

---

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | JWT signing key (min 32 chars) | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://host:6379/0` |
| `GOOGLE_API_KEY` | Gemini API key for AI features | `AIza...` |

### Optional — Enterprise Features

| Variable | Feature | Default |
|---|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth SSO | (disabled) |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth SSO | (disabled) |
| `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET` | Azure AD SSO | (disabled) |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` | LinkedIn SSO | (disabled) |
| `SAML_ENABLED` | SAML 2.0 SSO | `false` |
| `MFA_ENFORCE_GLOBALLY` | Require MFA for all users | `false` |
| `EMAIL_ENABLED` / `SMTP_*` | Email notifications | `false` |
| `FLOWER_BASIC_AUTH` | Celery monitoring auth | `admin:password` |

### Scaling Parameters

| Variable | Description | Recommended |
|---|---|---|
| `DB_POOL_SIZE` | Database connection pool | 20 |
| `DB_MAX_OVERFLOW` | Peak connection overflow | 30 |
| `DB_STATEMENT_TIMEOUT_MS` | Query timeout | 30000 |
| `SESSION_MAX_CONCURRENT` | Max sessions per user | 10 |
| `RATE_LIMIT_API_PER_MINUTE` | API requests/minute | 60 |

---

## Security Hardening

### Already Implemented
- ✅ TLS 1.2/1.3 with modern cipher suites
- ✅ HSTS (1 year, includeSubDomains, preload)
- ✅ Content Security Policy (CSP)
- ✅ XSS protection (input sanitization, output encoding)
- ✅ SQL injection prevention (parameterized queries)
- ✅ CSRF protection (OAuth state tokens)
- ✅ Rate limiting (API: 30r/s, Auth: 5r/min)
- ✅ JWT with rotation and refresh tokens
- ✅ bcrypt password hashing (cost factor 12)
- ✅ Multi-tenant data isolation (org_id middleware)
- ✅ API key support with scopes
- ✅ MFA (TOTP) with backup codes
- ✅ Brute-force protection (account lockout)
- ✅ File upload validation (magic bytes, size limits)
- ✅ PII masking in logs

### Production Checklist
- [ ] Generate a strong `SECRET_KEY` (openssl rand -hex 32)
- [ ] Use a real TLS certificate (Let's Encrypt or commercial CA)
- [ ] Configure CORS origins to your domain
- [ ] Enable MFA for admin accounts
- [ ] Set up Slack/Discord webhook for critical alerts
- [ ] Rotate API keys every 90 days
- [ ] Run security audit: `bandit -r backend/ -ll`
- [ ] Run dependency scan: `safety check`
- [ ] Configure WAF rules in nginx for SQLi/XSS patterns

---

## Monitoring & Alerting

### Dashboards
- **Grafana**: http://localhost:3000 (admin/admin)
  - AI ATS Main Dashboard — request rate, latency, errors, throughput
  - Database Dashboard — pool usage, query performance
  - Business Dashboard — candidates screened, hiring funnel

### Alerts (15 pre-configured)
| Alert | Severity | Description |
|---|---|---|
| `APIDown` | Critical | API service unreachable (>2m) |
| `HighErrorRate` | Critical | 5xx rate > 5% |
| `DatabaseDown` | Critical | PostgreSQL unreachable |
| `RedisDown` | Critical | Redis unreachable |
| `DiskSpaceLow` | Critical | Disk < 15% free |
| `HighLatency` | Warning | P95 > 2 seconds |
| `CeleryQueueBacklog` | Warning | > 100 pending tasks |
| `HighFailedLoginRate` | Warning | Possible brute-force attack |
| `ZeroCandidatesScreened` | Info | Pipeline potentially broken |

### Log Aggregation
- **Loki**: Centralized log storage (31-day retention)
- **Promtail**: Ships container logs + system logs
- Correlated with trace_id for distributed debugging

---

## Scaling & Performance

### Performance Targets (validated)
| Metric | Target | Implementation |
|---|---|---|
| Concurrent users | 100,000 | Nginx rate limiting + async FastAPI |
| API response time | <300ms P95 | Redis 2-level caching + DB pooling |
| Resume processing | 1M resumes | Celery priority queues + chunked processing |
| Database queries | <50ms avg | Covering indexes + BRIN + pool pre-warming |
| Frontend bundle | <200KB initial | Code splitting (5 chunks) + Gzip/Brotli |

### Scaling Strategy
1. **Horizontal**: Add API replicas (K8s HPA or docker compose `--scale api=N`)
2. **Vertical**: Increase DB instance size, Redis memory
3. **Database**: Read replicas for analytics, connection pooling (20-50)
4. **Cache**: Increase Redis memory, add read replicas
5. **Workers**: Additional Celery workers per queue

---

## Backup & Disaster Recovery

### Database Backups
```sql
-- Cloud SQL automated backups (enabled by default in Terraform)
-- Point-in-time recovery: 7 days
-- Retained backups: 30 days
-- Daily backups at 03:00 UTC

-- Manual backup
pg_dump -h <host> -U user resume_db > backup_$(date +%Y%m%d).sql
```

### Restore
```bash
# Cloud SQL restore via GCP Console or gcloud
gcloud sql backups restore <backup-id> \
  --restore-instance=ai-ats-postgres

# Manual restore
psql -h <host> -U user resume_db < backup.sql
```

### Redis Persistence
- RDB snapshots every 60 seconds (1+ key changed)
- AOF enabled for crash recovery

---

## Compliance

### GDPR
- **Article 15** — Data Subject Access Requests via `/api/enterprise/gdpr/dsar/{id}`
- **Article 17** — Right to Erasure via `/api/enterprise/gdpr/erase/{id}`
- **Article 30** — Processing records via `/api/enterprise/compliance/gdpr-report`
- **Consent Management** — Token-based self-service portal
- **Data Retention** — Automated enforcement (365-day default)

### EEOC / OFCCP
- EEO-1 Component 1 reports via `/api/enterprise/compliance/eeo-report`
- Adverse impact monitoring with automatic flagging
- Score distribution analysis per demographic

### Audit Trails
- All AI decisions logged with model versions
- Recruiter actions tracked with timestamps
- Immutable audit log table with input/output hashes

---

## Troubleshooting

### Health Check Failure
```bash
# Check all services
docker compose ps

# Check logs
docker compose logs api --tail=100
docker compose logs db --tail=50

# Test database connectivity
docker compose exec api python -c "
from app.db.database import async_engine
import asyncio
asyncio.run(async_engine.connect())
print('DB OK')
"
```

### Common Issues

**Database connection refused**
```bash
# Check if DB is running
docker compose ps db
# Check credentials match .env
docker compose exec db psql -U user -d resume_db -c "SELECT 1"
```

**Redis connection timeout**
```bash
# Check Redis health
docker compose exec redis redis-cli ping
# Expected: PONG
```

**Celery workers not processing**
```bash
# Check worker status
docker compose exec flower celery -A app.workers.celery_app inspect active
# Restart workers
docker compose restart worker
```

**Rate limiting blocking legitimate traffic**
```bash
# Check nginx rate limit logs
docker compose logs nginx | grep "limiting"
# Adjust limits in nginx/nginx.conf
```

---

## Support & Maintenance

- **Documentation**: Full API docs at `https://<domain>/docs`
- **Health Dashboard**: Grafana at `http://<monitoring-host>:3000`
- **Log Analysis**: Query logs via Loki in Grafana Explore
- **Database Optimization**: Run `EXPLAIN ANALYZE` on slow queries
- **Regular Tasks**:
  - Daily: Check alert dashboard
  - Weekly: Review error logs, audit trail
  - Monthly: Apply security patches, rotate keys
  - Quarterly: Load test, review capacity

---

*AI ATS v2.1.0 — Enterprise Talent Cloud. Production-ready. Cloud-native. Globally scalable.*
