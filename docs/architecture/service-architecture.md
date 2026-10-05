# Service Architecture

## 1. Microservice Boundaries

The system is decoupled using Celery as the message broker (via Redis), allowing high scalability and fault tolerance.

### 1.1 API Gateway (FastAPI)
- Handles authentication and REST endpoints.
- Manages the Next.js frontend requests.
- Dispatches tasks to Celery.
- Streams real-time updates via WebSockets.

### 1.2 Agent Orchestrator Worker
- Runs the LangGraph state machine.
- Manages LLM context windows and prompts.
- Does NOT execute browser commands; instead, it puts browser action requests onto the `browser_queue`.

### 1.3 Browser Worker (Playwright)
- Consumes from the `browser_queue`.
- Runs headless (or remote) Playwright instances.
- Validates actions through the Policy Engine.
- Extracts DOM snapshots and sends them back to the Orchestrator via Redis.

### 1.4 Document Intelligence Worker
- Parses PDFs, DOCX, and images.
- Extracts text and structural metadata.
- Passes extracted text to the Orchestrator for Fact extraction.

### 1.5 Matching & Discovery Worker
- Periodically scrapes or consumes APIs from supported job boards.
- Normalizes listings and deduplicates them.
- Runs initial vector similarity matches against the candidate profile.
