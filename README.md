# Auto Wale Bhaiya: Advanced AI Job Application Agent

[![CI/CD Pipeline](https://github.com/ShehMaat/Auto_Waale_Bhaiya/actions/workflows/ci.yml/badge.svg)](https://github.com/ShehMaat/Auto_Waale_Bhaiya/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-1.44.0-2EAD33.svg)](https://playwright.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

An enterprise-grade, human-in-the-loop autonomous job application platform. Built with deterministic security boundaries, strict browser execution isolation, verifiable candidate memory, and zero-autonomous-submission guarantees.

---

## 1. Project Overview

The **AI Job Application Agent** ("Auto Wale Bhaiya") is designed to streamline and automate high-friction job application workflows across diverse applicant tracking systems (ATS). Instead of acting as an unconstrained, speculative bot, the platform functions under strict supervisory control: it automates repetitive profile matching, form field identification, document uploads, and navigation, while mandating human approval for unknown fields, sensitive credentials, and final application submission.

---

## 2. What the Agent Does

- **Discovers and Ingests Jobs**: Ingests job requisitions across standard ATS connectors (Lever, Greenhouse, Ashby) and public job portals.
- **Understands Candidate Profiles**: Parses resumes (PDF/DOCX) into high-fidelity structured intelligence and skills vectors.
- **Performs Semantic Matching**: Computes transparent match scores, missing skills analyses, and role alignment matrices.
- **Drives Secure Browser Automation**: Controls dedicated Playwright worker sessions to navigate complex multi-page applications.
- **Fills Forms Intelligently**: Maps form fields dynamically against confirmed candidate facts stored in vector memory.
- **Intervenes on Uncertainty (HITL)**: Immediately pauses execution when encountering unknown required fields, sensitive inputs, or interactive challenges.
- **Enforces Submission Boundaries**: Categorically halts before final submission, requiring explicit human cryptographic authorization.
- **Tracks Metrics & Analytics**: Captures complete timeline auditing, funnels, and performance records.

---

## 3. Core Capabilities

| Capability | Description |
| :--- | :--- |
| **Zero-Guessing Memory** | Employs an evidence-based vector store (`pgvector`); unknown fields trigger HITL rather than hallucination. |
| **Deterministic Browser Isolation** | Dedicated per-application browser context with strict origin checking, CSP enforcement, and zero `page.evaluate()` LLM code execution. |
| **Multi-Stage Decision Engine** | Evaluates form inputs and actions through a defense-in-depth safety and validation pipeline. |
| **Safe Resume Handling** | S3-compatible document storage (MinIO) with pre-signed access and MIME-type validation. |
| **State Machine Orchestration** | LangGraph-driven deterministic state machine preventing invalid backward transitions or loops. |
| **Auditable Red-Team Suite** | 81/81 automated adversarial security tests verifying resistance against injection, SSRF, and bypasses. |

---

## 4. High-Level Architecture

*See the [System Architecture & AI Decision Pipeline Diagrams](docs/diagrams/architecture.md) for detailed visual representations.*

The system utilizes a distributed microservices and worker topology:

```
                  +-----------------------------------+
                  |         Next.js Frontend          |
                  |     (Review & Approval UI)        |
                  +-----------------+-----------------+
                                    | HTTP / REST API
                                    v
+-----------------------------------+-----------------------------------+
|                           FastAPI Backend                             |
|                                                                       |
|  +---------------------+  +--------------------+  +----------------+  |
|  |  Candidate Engine   |  |   Matching Engine  |  | State Machine  |  |
|  | (PyMuPDF / Parsing) |  | (Semantic/Embeds)  |  |  (LangGraph)   |  |
|  +---------------------+  +--------------------+  +----------------+  |
|                                                                       |
|  +---------------------+  +--------------------+  +----------------+  |
|  |   Decision Engine   |  |     HITL Manager   |  | Storage Client |  |
|  | (Safety & Semantic) |  | (Challenges/Tokens)|  |  (MinIO / S3)  |  |
|  +---------------------+  +--------------------+  +----------------+  |
+---------+--------------------+---------------------+------------------+
          |                    |                     |
          v                    v                     v
   +--------------+     +-------------+       +--------------+
   |  PostgreSQL  |     | Redis Queue |       | MinIO Object |
   |  (pgvector)  |     |  & PubSub   |       |   Storage    |
   +--------------+     +------+------+       +--------------+
                               |
                               v
                     +-------------------+
                     |   Celery Worker   |
                     | (Browser Actions) |
                     +---------+---------+
                               |
                               v
                     +-------------------+
                     |    Playwright     |
                     |  Isolated Context |
                     +---------+---------+
                               |
                               v
                     +-------------------+
                     |    Target ATS     |
                     |  (Web Application)|
                     +-------------------+
```

---

## 5. End-to-End Workflow

*See the [Golden Application Workflow Diagram](docs/diagrams/workflow.md) for a detailed state transition visualization.*

```
Job Discovery & Ingestion
         |
         v
Candidate Profile Matching
         |
         v
Candidate Authorizes Application Run
         |
         v
Browser Worker Bootstraps Isolated Session
         |
         v
Form Inspector Extracts DOM & Elements
         |
         v
Decision Engine Maps Fields & Confirmed Facts
         |
         +--> [Unknown/Sensitive Field Detected?] --YES--> Pause (WAITING_FOR_USER)
         |                                                        |
         |                                                 User Submits Value
         |                                                        |
         |<-------------------------------------------------------+
         |
         v
Browser Worker Executes Safe Actions (Fill, Select, Upload)
         |
         v
Form Inspector Evaluates Next Page / Completion Status
         |
         v
Reached Final Submission Page?
         |
        YES
         v
[EXPLICIT SUBMISSION BOUNDARY] --> Halts at READY_FOR_REVIEW
         |
   User Reviews All Form Data
         |
   User Clicks "Approve & Submit" (Explicit Human Authorization)
         |
         v
Final Submission Dispatched & Analytics Logged
```

---

## 6. Demonstration

*For the complete step-by-step presentation, see the [V1.0 Demo Script](docs/V1_DEMO_SCRIPT.md) and [Demo Guide](docs/DEMO_GUIDE.md).*
*See the [Golden Application Workflow Diagram](docs/diagrams/workflow.md) for the state transition overview.*

> **Real-World GlobalLogic Validation:**
> Real-world validation against GlobalLogic encountered an external anti-bot challenge. The agent failed closed and did not attempt to bypass the protection or submit an application.

---

## 8. Candidate Intelligence

Candidate intelligence extracts, normalizes, and indexes candidate profiles from raw PDF and DOCX files.
- **Deep Extraction**: Contact details, work experience, education, certifications, and project narratives are parsed into structured models using PyMuPDF and python-docx.
- **Skill Normalization**: Aliases (e.g., "JS", "ECMAScript", "React.js") are mapped to canonical ontology tokens.
- **Vector Embedding**: Text segments and candidate summaries are embedded using semantic models and persisted with `pgvector`.

---

## 8. Job Discovery

The discovery layer provides normalized ingestion across multiple talent acquisition protocols:
- **Direct Connectors**: Ashby, Greenhouse, and Lever API adapters.
- **Deduplication Engine**: Hash-based and semantic deduplication prevents re-processing identical jobs across multiple boards.
- **Requisition Validation**: Inactive, expired, or malformed job listings are pruned prior to matching.

---

## 9. Semantic Matching

- **Hybrid Relevance Scoring**: Combines vector cosine similarity with deterministic requirement filters (e.g., minimum years of experience, mandatory credentials, work authorization).
- **Match Breakdown**: Produces human-readable match percentages, highlighting matched strengths, partial overlaps, and missing requirements.
- **Threshold Gating**: Jobs falling below candidate-configured relevance thresholds are rejected automatically before application initiation.

---

## 10. Browser Automation

- **Headless Worker Pods**: Powered by Playwright under dedicated Celery tasks.
- **Strict Context Isolation**: Each application run operates inside an ephemeral, dedicated `BrowserContext` with cleared storage, cookies, and cache.
- **Safe Action Translation**: The LLM never controls browser code execution. High-level action intents (`CLICK`, `FILL`, `SELECT`, `UPLOAD`) are mapped directly to native Playwright primitives.
- **Artifact Management**: Traces, full-page screenshots, and network logs are captured for full debugging and auditability.

---

## 11. Form Intelligence

- **Semantic Field Mapping**: Identifies standard input fields (e.g., First Name, Email, Phone, LinkedIn URL) through combined heuristic and semantic analysis.
- **Custom Question Resolution**: Synthesizes responses to open-ended job questions strictly from verified candidate memory.
- **Multi-Page Navigation**: Handles paginated ATS wizards, tracking state transitions and preventing looping.
- **File Upload Engine**: Downloads resumes securely from MinIO and injects them via Playwright's file chooser without exposing local host paths.

---

## 12. Decision Engine

The `DecisionEngine` governs all automated actions through a rigid pipeline:
1. **Security Policy Inspection**: Validates selector safety, URL origin matching, and target element attributes.
2. **Intent Determination**: Classifies the required action (`FILL`, `CLICK_NEXT`, `ASK_USER`, `REVIEW`).
3. **Hallucination Prevention**: If a required field lacks an exact or high-confidence match in the candidate's confirmed vector memory, the engine yields `ASK_USER`.
4. **Boundary Detection**: Explicitly catches submission triggers ("Submit", "Apply", "Finish") and forces a transition to `READY_FOR_REVIEW`.

---

## 13. Persistent Memory

Candidate knowledge is segmented into distinct trust tiers:
- **Verified Facts**: Facts explicitly provided or confirmed by the candidate (High Trust).
- **Inferred Context**: Synthesized insights from previous applications (Subject to candidate approval).
- **Memory Poisoning Defense**: Adversarial prompts discovered on web pages cannot modify, write to, or overwrite candidate memory facts.

---

## 14. Human-in-the-Loop (HITL)

Human intervention is a first-class architectural primitive, not an edge-case handler:
- **Trigger Conditions**:
  - Unmapped required form fields.
  - Ambiguous multiple-choice or dropdown options.
  - Sensitive data requests (government ID, salary expectations, demographic disclosures).
  - Anti-bot / interactive challenges.
- **Lifecycle**: Execution suspends immediately (`WAITING_FOR_USER`). The user responds via the dashboard; input is stored into verified memory, and execution safely resumes.

---

## 15. Submission Authorization Boundary

> ### Zero Autonomous Submission Guarantee
> Under **no circumstances** does the agent autonomously press final application submission buttons.

- **Phase 3C Boundary**: When a form reaches the final submission stage, the `DecisionEngine` blocks the click event and returns `READY_FOR_REVIEW`.
- **Pre-Submission Review**: The user is presented with a complete summary of all filled inputs, uploaded documents, and generated responses.
- **Cryptographic Token Exchange**: The final submission is only executed after the user provides explicit, intentional authorization through the dashboard.

---

## 16. Security Architecture

- **Authentication & Authorization**: JWT-based authentication with bcrypt password hashing and strict tenant/user ownership verification.
- **Network Boundaries & SSRF Defense**: URL schemes are strictly validated (`http`/`https` only). Requests to RFC 1918 private subnets, localhost (`127.0.0.1`), metadata endpoints (`169.254.169.254`), and DNS rebinding vectors are blocked.
- **Browser Execution Isolation**:
  - No `page.evaluate()` or arbitrary script execution permitted from model outputs.
  - Download restrictions and cross-origin navigation guards.
- **Prompt Injection Defense**: Dual-layer input sanitation ensures malicious instructions embedded inside job postings cannot compromise agent instructions or exfiltrate private candidate data.
- **Audit Logging**: Every state transition, user approval, browser interaction, and network request is preserved in an immutable audit ledger.

---

## 17. Deployment Architecture

The platform supports high-availability containerized deployments:
- **Docker Compose Topology**: Modular containers for API, Web Frontend, Celery Worker, PostgreSQL (with pgvector), Redis, and MinIO.
- **Production Setup**: `deployment/docker-compose.prod.yml` with NGINX reverse proxy supporting automated zero-downtime Blue/Green deployments.
- **Health Checks & Monitoring**: Fully integrated health check probes (`/api/v1/health`), resource monitoring, and automated rollback scripts.

---

## 18. Testing Evidence

The platform enforces strict release gates validated through comprehensive test suites:

| Suite | Scope | Result | Status |
| :--- | :--- | :---: | :---: |
| **Full Regression Suite** | Unit, API, Database, Memory, Services, Pipeline | **568 / 568** | **PASS** |
| **Adversarial Red-Team Suite** | SSRF, Injections, Replays, Isolation, Memory Poisoning | **81 / 81** | **PASS** |
| **Golden ATS & E2E Suite** | Multi-page browser flow, uploads, HITL, submission boundary | **159 / 159** | **PASS** |
| **Object Storage Smoke Test** | MinIO clean container pull, bucket lifecycle, object put/get | **Verified** | **PASS** |
| **Browser Isolation Suite** | Concurrency, crash recovery, memory leak remediation | **Verified** | **PASS** |

---

## 19. Golden Workflow

The **Golden ATS** is a reference multi-page ATS testbed designed to validate end-to-end orchestration under controlled conditions:
1. **Authentication**: Candidate logs in to the dashboard.
2. **Profile & Job Selection**: Selects a target position requiring custom questions and resume upload.
3. **Automated Navigation**: Browser worker launches, navigates to the ATS form, and enters known candidate details.
4. **HITL Interruption**: Reaches an unmapped custom field (`office_snack`); safely pauses in `WAITING_FOR_USER`.
5. **Human Resolution**: Candidate submits the preference via the UI; execution resumes.
6. **Document Upload**: Automatically attaches candidate's resume from S3 storage.
7. **Submission Boundary**: Reaches final review; `DecisionEngine` stops at `READY_FOR_REVIEW`.
8. **Explicit Authorization**: Candidate reviews details, confirms submission, and views final status in analytics.

---

## 20. Real-World GlobalLogic Validation

As part of Phase 16 validation, the agent was tested against a live enterprise ATS requisition (GlobalLogic).

> **Important Operational Finding**:
> The GlobalLogic validation encountered an external anti-bot challenge (Imperva/Incapsula Web Application Firewall). The agent **failed closed** and did not attempt to bypass the protection or submit an application.

This behavior proves that safety policies correctly take precedence over aggressive automation.

---

## 21. Installation

### Prerequisites
- **Python**: 3.12+
- **Node.js**: 20+ (for Next.js frontend)
- **uv**: Modern Python package manager (`pip install uv` or via curl/winget)
- **Docker & Docker Compose**: For containerized dependencies

### Clone Repository
```bash
git clone https://github.com/ShehMaat/Auto_Waale_Bhaiya.git
cd Auto_Waale_Bhaiya
```

---

## 22. Configuration

Copy the example environment configuration:
```bash
cp .env.example .env
```

Key environment variables:
```ini
# Core Configuration
ENVIRONMENT=development
SECRET_KEY=change-this-in-production-use-a-strong-random-key

# Database & Cache
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_job_agent
REDIS_URL=redis://localhost:6379/0

# Object Storage (MinIO / S3)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=resumes
S3_USE_SSL=false

# LLM Providers
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Browser Automation
HEADLESS=true
BROWSER_TIMEOUT_MS=30000
```

---

## 23. Development Setup

1. **Start Core Infrastructure**:
   ```bash
   docker compose up -d postgres redis minio
   ```

2. **Install Python Dependencies & Tools**:
   ```bash
   uv sync
   uv run playwright install chromium
   ```

3. **Run Database Migrations**:
   ```bash
   uv run alembic upgrade head
   ```

4. **Start the API Server**:
   ```bash
   uv run uvicorn apps.api.app.main:app --reload --port 8000
   ```

5. **Start Celery Worker**:
   ```bash
   uv run celery -A apps.api.app.worker.celery_app worker --loglevel=info
   ```

6. **Start Web Frontend**:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

---

## 24. Production Deployment

Production deployments are automated via Docker Compose and zero-downtime Blue/Green scripts:

```bash
# Validate production compose syntax
docker compose -f deployment/docker-compose.prod.yml config

# Deploy production stack
python deployment/scripts/deploy.py

# Roll back in case of deployment health failure
python deployment/scripts/rollback.py
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md) for full runbooks.

---

## 25. Known Limitations

- **Arbitrary ATS Compatibility is Not Guaranteed**: Enterprise portals with proprietary shadow-DOM elements or non-standard dynamic canvases may fail closed.
- **External Anti-Bot Systems**: Bot-mitigation solutions (e.g., Cloudflare Turnstile, Imperva WAF, DataDome) prevent automation and trigger fail-closed transitions.
- **No CAPTCHA / 2FA Bypasses**: The platform will not attempt to solve CAPTCHAs or automate SMS/email OTP challenges. Human intervention is required.
- **Manual Submission Required**: Autonomous final submissions are disabled by design.
- **HR Outcome Ingestion**: Application outcome tracking is constrained by the telemetry available from target ATS notifications.

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for the comprehensive disclosure.

---

## 26. Roadmap & Future Work

- [ ] **Phase 17**: Expanded ATS connector coverage for Greenhouse Harvest API and Workday integration.
- [ ] **Phase 18**: Enhanced multi-modal resume formatting analysis and visual parsing.
- [ ] **Phase 19**: Candidate interview scheduling assistance via Calendar API integrations.
- [ ] **Phase 20**: Local LLM execution options (e.g., Ollama / vLLM) for complete air-gapped on-premises deployments.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
