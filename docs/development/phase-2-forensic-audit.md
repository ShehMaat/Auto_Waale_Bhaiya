# Phase 2 Forensic Audit

## 1. Executive Summary
This document provides a rigorous, forensic audit of the Phase 2 implementation. The objective is to verify every claim against the actual source code, tests, and configuration without trusting previous implementation reports. 

**Conclusion:** The implementation is **NOT READY**. While substantial architectural scaffolds and proof-of-concept components exist, several critical production requirements—such as raw job storage, 5-layer deduplication, robust requirement extraction logic, SSRF redirect protections, Celery idempotency, and comprehensive test coverage—are either missing, incomplete, or implemented merely as stubs.

## 2. PASS/PARTIAL/FAIL Matrix

| Feature | Requirement | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Document Pipeline** | PDF/DOCX Parsing | PARTIAL | Basic parsing exists. OCR fallback is a placeholder method returning a static string. |
| **Fact Extraction** | Structured LLM output | PASS | Validated via Pydantic to `ExtractedFact` and mapped to `MemoryFact`. |
| **Provenance** | Verification States | PASS | Facts are correctly tagged `RESUME_EXTRACTED` and default to `SUGGESTED`. |
| **Memory** | ADR-006 Compliance | PASS | Uses existing `MemoryFact` structure without redundant tables. |
| **Embeddings** | Generation & Storage | PARTIAL | Generation exists, but no robust logic for regenerating when sources change or handling API failures gracefully. |
| **Connectors** | Greenhouse/Lever/Ashby | PASS | Core integrations work. |
| **SSRF Security** | Internal IP Blocking | PARTIAL | String-based filters block direct localhost/private IPs, but `httpx` redirects are not explicitly bounded, opening a DNS rebinding/redirect SSRF vector. |
| **Raw Job Data** | Raw Payload Preservation | FAIL | Raw job data is not preserved in a dedicated schema. Only normalized `Job` entries exist. |
| **Deduplication** | 5-Layer deduplication | FAIL | The 5-layer logic was not fully implemented in `job_discovery.py` beyond basic list comprehensions. |
| **Requirement Ext** | REQUIRED/PREFERRED/UNKNOWN | FAIL | The extraction pipeline lacks the detailed Pydantic boundaries needed for UNKNOWN vs FALSE separation. |
| **Prompt Injection** | LLM Safety | PASS | `test_job_prompt_injection.py` confirms that untrusted wrappers protect system prompts. |
| **Matching Engine** | Layered Matching | PARTIAL | `pgvector` semantic matching (`<=>` dot product) is implemented in-memory, but hard constraint checks are a `pass` stub. |
| **Score Versioning** | Configurable weights | FAIL | Weights (0.4, 0.3) are hardcoded into the business logic. No `matching_version` field exists on the database model. |
| **Celery** | Idempotency & Retries | FAIL | Tasks lack explicit duplicate-execution safeguards. Running `process_document_task` twice inserts duplicate `MemoryFact` rows. |
| **Frontend** | Functional UI | PARTIAL | HTML/JS scaffolded and hits API, but lacks actual token-based auth flow. |

## 3. Detailed Audits

### Security Audit
- **SSRF:** The custom `_safe_fetch` blocks explicit local IPs, but does not configure `httpx` to disable redirects or resolve IPs before fetching, making it vulnerable to DNS rebinding or 302 redirects to internal endpoints.
- **LLM Safety:** Verified passing via adversarial tests. Untrusted job data is successfully contained.

### Database Audit
- **Integrity:** The schema lacks `job_source_payloads` or equivalent for raw data preservation. 
- **Migrations:** `alembic upgrade head` runs cleanly, but the schema is missing required tables for the full Phase 2 scope.

### Test Coverage Audit
- **Current Tests:** 15 passing tests primarily cover Phase 1 logic and prompt injection. 
- **Missing Coverage:** There are zero tests for: Celery idempotency, deduplication logic, document parsing edge cases, SSRF redirect attempts, and connector health checks. `pytest --cov` is not configured to run.

### Static Quality Audit
- `ruff check .` found 95 remaining `E501` (Line too long) errors across older test files.
- `mypy .` reported 112 errors, largely due to missing return types and untyped Celery decorators/LLM provider returns. 

## 4. Identified Defects
1. **No Raw Job Storage:** Violates the requirement to keep raw source data separate from normalized data.
2. **Missing Deduplication Engine:** The 5-layer strategy is completely unwritten.
3. **Hard Constraint Stub:** `evaluate_hard_constraints` contains a `pass` statement.
4. **Celery Idempotency:** Background tasks are not safe against duplicate execution.
5. **SSRF Redirect Flaw:** `httpx` will follow redirects to internal network addresses.

## 5. Phase 3 Entry Decision

**PHASE 2 NOT VERIFIED — PHASE 3 BLOCKED**

Phase 2 requires immediate remediation of the identified defects before the system can be considered production-ready for Phase 3.
