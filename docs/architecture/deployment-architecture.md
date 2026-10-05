# Deployment Architecture

## 1. Infrastructure Overview
The application is containerized using Docker and defined via `docker-compose.yml`.

## 2. Components
- **api**: FastAPI application server (Uvicorn).
- **worker_agent**: Celery worker consuming the `agent` queue.
- **worker_browser**: Celery worker consuming the `browser` queue. Requires Playwright dependencies (e.g., `mcr.microsoft.com/playwright/python`).
- **postgres**: Database containing relational data and pgvector extension.
- **redis**: Acts as both Celery broker and result backend. Also provides caching.
- **minio**: S3-compatible object storage for resumes, screenshots, and raw HTML dumps (for auditability).
- **frontend**: Next.js Node application.

## 3. Security Considerations
- The `worker_browser` container should be heavily isolated from the rest of the network, as it interacts with potentially hostile external DOMs.
- It should have no direct access to the `postgres` database; it must communicate solely via the message broker.
