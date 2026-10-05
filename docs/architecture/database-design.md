# Database Design

## 1. Overview
The database design centers around PostgreSQL with `pgvector` for semantic search. The schemas strictly enforce Principle 6 (Evidence-Based Memory).

## 2. Core Entities

### 2.1 Users & Profiles
- **User**: Authentication and account metadata.
- **CandidateProfile**: Core fixed details (Name, Contact, Links).

### 2.2 Provenanced Memory
To adhere to the anti-hallucination and evidence-based memory principles:
- **MemoryFact**: A distinct piece of candidate information (e.g., "Expected Salary", "Python Experience").
  - `key`: The concept (e.g., `expected_salary`)
  - `value`: The data (e.g., `120,000 USD`)
  - `confidence_score`: Float
  - `status`: Enum (`SUGGESTED`, `CONFIRMED`, `REJECTED`)
  - `provenance_type`: Enum (`USER_INPUT`, `RESUME_EXTRACTION`, `LLM_INFERENCE`)
  - `provenance_reference`: Link to source (e.g., document ID, chat log ID)
  - `vector_embedding`: pgvector representation of the fact.

### 2.3 Job Discovery & Applications
- **JobListing**: Discovered jobs from external sources.
  - `source_url`: URL of the listing
  - `raw_html`: Raw untrusted content (stored in MinIO)
  - `parsed_description`: Sanitized description
  - `extracted_requirements`: JSONB of structured requirements.
- **JobApplication**: State machine tracking the application lifecycle.
  - `status`: Enum (`DISCOVERED`, `MATCHING`, `APPLYING`, `NEEDS_INTERVENTION`, `READY_FOR_REVIEW`, `SUBMITTED`, `FAILED`)
  - `intervention_reason`: If paused, why? (e.g., `CAPTCHA`, `MISSING_INFO`)
  - `form_data_snapshot`: The final JSON representation of the filled form.

### 2.4 Audit & Analytics
- **ApplicationEventLog**: Immutable ledger of all actions taken during an application flow.
  - Required to maintain a complete audit trail (Principle 4 & 7).
  - Includes timestamp, actor (`AGENT`, `HUMAN`), action type, and outcome.
