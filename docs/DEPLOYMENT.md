# AI Job Application Agent — Production Deployment Guide

## 1. Overview
*Diagram Reference: [Production Deployment Architecture](diagrams/deployment.md)*

This document specifies the production deployment architecture, prerequisites, configuration, and execution procedures for the **AI Job Application Agent (v1.0.0)**.

The production environment runs on containerized services orchestrated via Docker Compose, fronted by an NGINX reverse proxy supporting zero-downtime Blue/Green deployments.

---

## 2. Infrastructure Topology

```
[ Internet Traffic ]
        |
        v
+-------------------+
|    NGINX Edge     | (Port 80 / 443)
+---------+---------+
          |
          | Upstream Proxy Switch
          v
+-------------------+-------------------+
| Blue Upstream     | Green Upstream    |
| (Active Slot)     | (Standby Slot)    |
| - API: 8001       | - API: 8002       |
| - Web: 3001       | - Web: 3002       |
+---------+---------+---------+---------+
          |                   |
          +---------+---------+
                    |
                    v
+---------------------------------------+
| Shared Infrastructure Services        |
| - PostgreSQL 16 (pgvector): 5432      |
| - Redis 7.0: 6379                     |
| - MinIO S3 Object Storage: 9000/9001  |
| - Celery Browser Worker Pool          |
+---------------------------------------+
```

---

## 3. Container Images & Pinned Dependencies

All production images must be pinned to explicit release tags or immutable digests:

| Service | Image Reference | Purpose |
| :--- | :--- | :--- |
| **API** | Local multi-stage build (`deployment/Dockerfile.api`) | FastAPI application server |
| **Frontend** | Local Next.js build (`deployment/Dockerfile.frontend`) | Web user interface |
| **Browser Worker** | Local Playwright build (`deployment/Dockerfile.browser`) | Isolated automation runner |
| **Celery Tasks** | Local worker build (`deployment/Dockerfile.celery`) | Asynchronous task dispatcher |
| **PostgreSQL** | `pgvector/pgvector:pg16` | Relational & vector database |
| **Redis** | `redis:7-alpine` | Message queue and session cache |
| **Object Storage** | `cgr.dev/chainguard/minio@sha256:4cf4831a2bbcf13ddca09c1cbcc9faff716dd3c4247e0babc32864b8ee8e0034` | S3-compatible resume/artifact store |
| **Reverse Proxy** | `nginx:alpine` | Blue/Green ingress routing |

---

## 4. Environment Configuration Checklist

Create `/etc/ai-job-agent/.env.prod` (or pass via secure secret manager):

```ini
# Production Environment
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-strong-64-character-secret>

# Database Credentials
DATABASE_URL=postgresql+psycopg://app_user:<secure-db-password>@postgres:5432/ai_job_agent_prod

# Redis Broker
REDIS_URL=redis://:<secure-redis-password>@redis:6379/0

# Object Storage (MinIO / AWS S3)
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=<secure-s3-access-key>
S3_SECRET_KEY=<secure-s3-secret-key>
S3_BUCKET_NAME=resumes
S3_USE_SSL=false

# LLM Providers
GEMINI_API_KEY=<production-gemini-key>
OPENAI_API_KEY=<production-openai-key>

# Browser Concurrency Limits
MAX_CONCURRENT_BROWSERS=4
BROWSER_TIMEOUT_MS=30000
HEADLESS=true
```

---

## 5. Deployment Step-by-Step

### 5.1 Initialize Shared Storage & Volumes
```bash
docker volume create ai_job_agent_pgdata
docker volume create ai_job_agent_miniodata
docker volume create ai_job_agent_redisdata
```

### 5.2 Validate Compose Configuration
```bash
docker compose -f deployment/docker-compose.prod.yml config
```

### 5.3 Apply Database Migrations
Always run migrations before triggering service cutovers:
```bash
uv run alembic upgrade head
```

### 5.4 Execute Zero-Downtime Blue/Green Deploy
The automated deployment script handles image building, container staging, health probe checks, and NGINX upstream switching:
```bash
python deployment/scripts/deploy.py
```

### 5.5 Verify Health Probes
```bash
# Verify API probe
curl -f http://localhost/api/v1/health

# Verify S3 object storage probe
curl -f http://localhost:9000/minio/health/live
```

---

## 6. Rollback Protocol

If the newly deployed slot fails health probes or reports elevated error rates, execute immediate rollback:
```bash
python deployment/scripts/rollback.py
```
This immediately shifts the NGINX upstream back to the previous known-healthy slot without data loss.
