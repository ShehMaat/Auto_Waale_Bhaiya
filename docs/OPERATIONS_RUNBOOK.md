# AI Job Application Agent — Operations Runbook

## 1. Operational Overview
This runbook provides system administrators, SREs, and on-call engineers with procedures for operating, monitoring, diagnosing, and maintaining the **AI Job Application Agent (v1.0.0)** in production.

---

## 2. Health Probes & Monitoring

### 2.1 Critical Health Endpoints
| Service | Endpoint / Probe | Expected Status |
| :--- | :--- | :---: |
| **API Server** | `GET /api/v1/health` | `HTTP 200 {"status": "ok"}` |
| **Database** | Verified internally by `/api/v1/health` | Connected / Responsive |
| **Redis** | `redis-cli ping` | `PONG` |
| **MinIO Storage** | `GET /minio/health/live` | `HTTP 200` |
| **Frontend** | `GET /api/health` or `GET /` | `HTTP 200` |

### 2.2 Key Performance Indicators (KPIs)
- **API Latency (p95)**: < 150ms for standard requests, < 2.5s for embedding calculations.
- **Browser Worker Concurrency**: Ensure active Chromium processes do not exceed `MAX_CONCURRENT_BROWSERS` (default: 4 per worker pod).
- **Queue Lag**: Redis Celery queue length should remain < 20 pending tasks under steady state.
- **Worker Memory Consumption**: Browser worker containers should remain < 2.5GB RAM; recycling triggers automatically on task termination.

---

## 3. Routine Maintenance & Backups

### 3.1 PostgreSQL Backup
```bash
# Automated Daily Logical Dump
docker exec -t ai_job_agent_postgres pg_dumpall -U postgres | gzip > /backups/postgres_$(date +%F).sql.gz

# Verify Backup Integrity
gzip -t /backups/postgres_$(date +%F).sql.gz
```

### 3.2 MinIO Object Storage Backup
```bash
# Sync S3 buckets to cold backup destination
mc mirror local/resumes /backups/s3_resumes_$(date +%F)/
```

### 3.3 Database Migrations
Always verify pending migrations before maintenance:
```bash
uv run alembic current
uv run alembic heads
uv run alembic upgrade head
```

---

## 4. Incident Response & Troubleshooting

### Scenario A: Unresponsive Browser Workers / Orphaned Chromium
- **Symptoms**: Celery tasks timing out, high RAM usage on worker pods, tasks stuck in `IN_PROGRESS`.
- **Diagnosis**:
  ```bash
  docker top ai_job_agent_browser
  ps aux | grep chromium
  ```
- **Remediation**:
  1. Restart Celery browser worker container:
     ```bash
     docker compose -f deployment/docker-compose.prod.yml restart celery browser
     ```
  2. The state machine's timeout supervisor will transition stuck applications to `FAILED` or `PAUSED` without database corruption.

### Scenario B: LLM Rate Limit / API Exhaustion
- **Symptoms**: Applications halting at `WAITING_FOR_USER` or error logs showing `429 Too Many Requests` from Gemini/OpenAI.
- **Diagnosis**: Inspect API logs:
  ```bash
  docker logs -n 100 ai_job_agent_api | grep -i "rate limit"
  ```
- **Remediation**:
  1. Ensure fallback model configurations are active in `.env`.
  2. System automatically backs off with exponential jitter; applications safely pause without losing state.

### Scenario C: PostgreSQL Connection Pool Saturation
- **Symptoms**: API returning `500 Internal Server Error`, logs reporting `QueuePool limit exceeded`.
- **Remediation**:
  1. Check active connections:
     ```bash
     docker exec -it ai_job_agent_postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
     ```
  2. Adjust pool size in `packages/config/settings.py` or scale database connection limit.

---

## 5. Emergency Rollback Protocol
If a bad deployment is detected:
```bash
python deployment/scripts/rollback.py
```
This command automatically points NGINX back to the previously active slot and gracefully stops the failing deployment.
