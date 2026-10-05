# AI Job Application Agent — Release Baseline v1.0.0

## 1. Verified Architecture & Locked Phases
The system represents the completion of 17 locked engineering and validation phases:
- **Phase 0–14**: Core Foundations, State Machine, Form Intelligence, HITL, Security Policy, Connectors [LOCKED]
- **Phase 15A–15D**: Next.js Web Frontend, Job Discovery UI, Application Lifecycle & Review Dashboard [LOCKED]
- **Phase 16**: Release Candidate Validation, Browser Worker Lifecycle Remediation, Object Storage Clean-Environment Remediation [LOCKED]

### Critical Architectural Boundaries:
1. **Explicit Submission Authorization Boundary (Phase 3C)**: Final submission buttons ("Submit Application", "Apply Now", "Complete Application", etc.) are intercepted and blocked by the `DecisionEngine`. The workflow halts unconditionally at `ApplicationStatus.READY_FOR_REVIEW`.
2. **Deterministic Browser Security Policy**: Dedicated per-application Playwright browser contexts with strict domain matching, zero arbitrary script execution (`page.evaluate` with LLM code is forbidden), and origin-level containment.
3. **Evidence-Based Candidate Memory**: Fact storage in PostgreSQL with `pgvector`. The state machine halts and requests human intervention (`WAITING_FOR_USER`) if a required field lacks a verified candidate answer.
4. **Deterministic Object Storage**: Verified against S3-compatible MinIO using pinned image `cgr.dev/chainguard/minio@sha256:4cf4831a2bbcf13ddca09c1cbcc9faff716dd3c4247e0babc32864b8ee8e0034`.

---

## 2. Test Baseline & Comprehensive Evidence

| Test Suite | Files | Tests Executed | Passed | Failed | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Full Regression Suite** | Unit, API, Database, Memory, Services, Pipeline | 568 | 568 | 0 | **PASS** |
| **Adversarial Red-Team Suite** | `tests/redteam/` | 81 | 81 | 0 | **PASS** |
| **Golden ATS & Integration** | `tests/workflow/`, `tests/e2e/` | 159 | 159 | 0 | **PASS** |
| **Clean Object Storage Smoke** | `test_minio_smoke.py` | 1 | 1 | 0 | **PASS** |

### Verification Details:
- **Golden ATS Happy Path**: Verified multi-page traversal, document upload, dynamic field parsing, and safe halt at `READY_FOR_REVIEW`.
- **HITL Interruption**: Verified that unmapped custom questions (`office_snack`) trigger `WAITING_FOR_USER` without hallucination.
- **Fail-Closed Real Site Validation (GlobalLogic)**: When confronted with an Imperva/Incapsula Web Application Firewall (WAF) challenge page, the agent successfully detected the security barrier, failed closed, and paused for human intervention without attempting bypasses.

---

## 3. Toolchain & Runtime Baseline
- **Python**: 3.12.14
- **Node.js**: v20+
- **Database Engine**: PostgreSQL 16 with `pgvector`
- **Queue/Cache**: Redis 7
- **Browser Automation**: Playwright 1.44.0 (Chromium)
- **Object Storage**: MinIO (S3-compatible)
- **Package Management**: uv (Python), npm (Frontend)
- **Alembic Head Revision**: `36f87c317d34`
- **Linting & Quality**: Ruff check verified (non-blocking test formatting warnings documented); Mypy type-checking passing on core packages.

---

## 4. Release Status
**V1.0.0 RELEASE READY — ALL GATES LOCKED AND PASSING**
