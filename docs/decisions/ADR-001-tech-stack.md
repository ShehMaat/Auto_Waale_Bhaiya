# ADR-001: Tech Stack

## Context
The AI Job Application Agent requires a highly concurrent, scalable, and safe environment to orchestrate LLMs, manage browser automation, and interface with users.

## Decision
We have chosen the following tech stack:
- **Backend:** Python + FastAPI (Strong typing, excellent AI ecosystem).
- **Background Workers:** Celery + Redis (Decouples long-running browser tasks).
- **Database:** PostgreSQL + pgvector (Relational integrity + semantic search in one datastore).
- **Frontend:** Next.js (Modern React framework).
- **Browser Automation:** Playwright (Robust headless browser control).
- **Orchestration:** LangGraph (State machine control over LLM flows).

## Consequences
- Requires operational knowledge of Celery and Redis.
- Python is ideal for AI but requires strict typing (mypy) to maintain safety in large codebases.
