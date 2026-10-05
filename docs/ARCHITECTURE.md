# AI Job Application Agent — Technical Architecture

## 1. System Overview

*Diagram References: [System Architecture & AI Decision Pipeline](diagrams/architecture.md) | [Golden Application Workflow](diagrams/workflow.md)*

The **AI Job Application Agent** is an asynchronous, event-driven distributed system designed for human-supervised job discovery, candidate matching, and automated form completion.

```
                           +------------------------+
                           |    Next.js Frontend    |
                           +-----------+------------+
                                       |
                                       v
                           +------------------------+
                           |   NGINX Reverse Proxy  |
                           |   (Blue/Green Routing) |
                           +-----------+------------+
                                       |
                                       v
                           +------------------------+
                           |     FastAPI Backend    |
                           +-----+------------+-----+
                                 |            |
                    +------------+            +------------+
                    |                                      |
                    v                                      v
         +---------------------+                +---------------------+
         | PostgreSQL+pgvector |                |     Redis 7.0       |
         | (Relational/Vectors)|                |  (Broker & Cache)   |
         +---------------------+                +----------+----------+
                    |                                      |
                    v                                      v
         +---------------------+                +---------------------+
         | MinIO Object Storage|                |    Celery Worker    |
         | (Resumes & Files)   |                |  (Browser Worker)   |
         +---------------------+                +----------+----------+
                                                           |
                                                           v
                                                +---------------------+
                                                |     Playwright      |
                                                |  Isolated Contexts  |
                                                +---------------------+
```

---

## 2. Core Components

### 2.1 Web Frontend (`apps/web`)
- **Technology**: Next.js 14, React 18, TypeScript, Tailwind CSS.
- **Role**: Presents the user interface for candidate profile management, job discovery feeds, interactive form review, real-time intervention resolution (HITL), and audit analytics.

### 2.2 API Server (`apps/api`)
- **Technology**: FastAPI, Python 3.12, SQLAlchemy 2.0 (async), Pydantic v2.
- **Role**: Exposes REST endpoints for authentication, profile management, ATS job feeds, application dispatching, challenge approval, and analytics.

### 2.3 PostgreSQL & `pgvector`
- **Role**: Primary relational database and high-performance vector store.
- **Relational Tables**: `candidates`, `jobs`, `applications`, `application_steps`, `hitl_challenges`, `user_accounts`.
- **Vector Extensions**: `pgvector` stores 768-dimensional and 1536-dimensional embeddings for candidate experience segments, skill ontologies, and job description requirements.

### 2.4 Redis
- **Role**: Message broker for Celery task queuing and distributed caching for short-lived challenge tokens, rate limiters, and session locks.

### 2.5 Celery & Browser Worker (`packages/browser/worker.py`)
- **Technology**: Celery, Playwright 1.44.0.
- **Role**: Runs asynchronous, long-running browser navigation tasks in isolated worker pods. Manages browser lifecycles, DOM snapshotting, action execution, and error handling.

### 2.6 MinIO Object Storage
- **Role**: S3-compatible blob storage for raw resume documents (PDF, DOCX), generated cover letters, and application trace screenshots.
- **Container Reference**: `cgr.dev/chainguard/minio@sha256:4cf4831a2bbcf13ddca09c1cbcc9faff716dd3c4247e0babc32864b8ee8e0034`.

### 2.7 NGINX & Zero-Downtime Blue/Green Deployment
- **Role**: Edge reverse proxy routing HTTP traffic to active application upstreams (`blue` or `green`).
- **Cutover Mechanism**: Controlled by `deployment/scripts/deploy.py` and `deployment/scripts/rollback.py`. Health check probes ensure the standby slot is responsive before switching NGINX upstream pointers.

---

## 3. Decision & Execution Pipeline

The browser interaction pipeline decouples LLM reasoning from browser execution to ensure strict containment:

```
[ LLM Provider (Gemini / OpenAI) ]
               |
               | Returns Structured JSON Intent
               v
[ DecisionEngine / Validator ]
               |
               | Generates Typed Action (FILL, SELECT, CLICK, UPLOAD)
               v
[ BrowserSecurityPolicy ]
               | Checks:
               | - Origin URL whitelist
               | - Forbidden JS/eval patterns
               | - Submission boundary protection
               v
[ Browser Worker (Playwright) ]
               |
               | Executes safe native Playwright API calls
               v
[ Target ATS Web Page ]
```

### Key Safety Invariant:
**No `page.evaluate()` with untrusted code**: LLM outputs are parsed as structured declarative schema objects (`BrowserActionIntent`), never executable scripts.

---

## 4. End-to-End Application Lifecycle

The progression of a job application follows a deterministic state machine:

```
+----------------------------------------------------+
| Job Ingestion (Connectors & Portals)               |
+-------------------------+--------------------------+
                          |
                          v
+----------------------------------------------------+
| Semantic Matching (Profile Vector Cosine Match)    |
+-------------------------+--------------------------+
                          |
                          v
+----------------------------------------------------+
| Application Creation (Status: PENDING)             |
+-------------------------+--------------------------+
                          |
                          v
+----------------------------------------------------+
| Form Intelligence (DOM Inspection & Mapping)       |
+-------------------------+--------------------------+
                          |
                          v
+----------------------------------------------------+
| Candidate Memory Check (Verified Facts Retrieval)  |
+-------------------------+--------------------------+
                          |
           +--------------+---------------+
           |                              |
    [All Fields Verified]      [Unmapped Required Field]
           |                              |
           v                              v
+-----------------------+      +-----------------------+
| Execute Browser Action|      | HITL Challenge Trigger|
+-----------+-----------+      | (Status: WAITING)     |
            |                  +-----------+-----------+
            |                              |
            |                     User Provides Answer
            |                              |
            |<-----------------------------+
            |
            v
+----------------------------------------------------+
| Multi-Page Navigation / Document Uploads           |
+-------------------------+--------------------------+
                          |
                          v
+----------------------------------------------------+
| Reached Final Page -> DecisionEngine Intercepts     |
| (Status: READY_FOR_REVIEW)                         |
+-------------------------+--------------------------+
                          |
                          v
+----------------------------------------------------+
| Explicit Human Review & Cryptographic Authorization|
+-------------------------+--------------------------+
                          |
                          v
+----------------------------------------------------+
| Submission Dispatched -> Status: APPLIED           |
+----------------------------------------------------+
```

---

## 5. Security & Isolation Invariants

1. **Ephemeral Context Isolation**: Each browser session runs in a fresh, isolated `BrowserContext` that is immediately closed and purged upon task completion or failure.
2. **SSRF Guard**: All outbound navigation requests are filtered by `BrowserSecurityPolicy` to reject private networks, localhost, link-local addresses, and non-standard schemes.
3. **Submission Boundary (Phase 3C)**: Autonomous submission is architecturally impossible. Submission action buttons trigger an interrupt condition in the state machine, requiring an explicit user-authenticated HTTP endpoint call (`/applications/{id}/approve`).
