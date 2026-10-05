# Phase 2 Implementation Report

## Overview
Phase 2 completed the Candidate Intelligence and Job Discovery Engine, adhering to all specifications and boundary constraints. The application now fully supports parsing resumes to structured facts, extracting canonical job requirements via safe LLM invocation, and scoring candidate-job matches via hybrid constraint and semantic vectors.

## Key Additions
1. **Connectors:** Greenhouse, Lever, and Ashby connectors utilizing `httpx` with SSRF and rate-limit guardrails.
2. **Ingestion:** Document parsing via PyMuPDF and python-docx, with MIME validation and extraction limits.
3. **Database:** Implemented MemoryFact mapping from raw resume content, converting structured Pydantic LLM outputs to verifiable records.
4. **Matching:** Computed scores utilizing pgvector `<=>` embeddings in tandem with Hard Constraint evaluations.
5. **Phase Boundary:** Strictly isolated processing from application execution. Browser automation is NOT implemented.
