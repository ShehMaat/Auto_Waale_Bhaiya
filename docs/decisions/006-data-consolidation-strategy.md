# 006 - Data Consolidation Strategy for Candidate and Applications

## Status
Accepted

## Context
During the Phase 1 Architecture Compliance Audit, a strict review against the Phase 0 contracts revealed that while the conceptual domains of `education`, `experience`, `projects`, `skills`, `certifications`, and `preferences` were outlined in the database design, explicit tables for these entities were omitted in favor of the `MemoryFact` table. Additionally, `application_answers` and `generated_answers` were consolidated into the `form_data_snapshot` JSON field on the `applications` table. Finally, `agent_events` are handled via `AgentState` checkpoints and `ApplicationEvent` logs.

We need to formalize this schema consolidation approach to ensure it strictly complies with the system's core architecture principles, specifically **Principle 6: Memory is Evidence-Based**.

## Decision
1. **Candidate Domains as MemoryFacts**: We will formally consolidate `education`, `experience`, `projects`, `skills`, `certifications`, and `preferences` into the `memory_facts` table. Creating static, rigid tables for these domains prevents the system from tracking the exact provenance (e.g., whether an experience entry was parsed from a PDF or suggested by an LLM) and confidence of each individual attribute. By using `MemoryFact`, every individual skill or work experience entry is automatically vectorized by `pgvector` for semantic matching and tightly bound to a provenance trail.
2. **Application Answers as JSONB**: We consolidate `application_answers` and `generated_answers` into the `form_data_snapshot` JSON field on the `applications` table. Job application forms are highly dynamic and do not conform to a static relational schema. Storing the final payload as JSON perfectly aligns with how Playwright will eventually inject the data into the DOM or API endpoints.
3. **Agent Events**: We map the `agent_events` conceptual domain to `agent_states` (for LangGraph state checkpointing) and `application_events` (for user-facing audit logs of what the agent did).
4. **Job Requirements**: We add an explicit `extracted_requirements` JSON field to the `jobs` table, aligning strictly with Phase 0 design.
5. **Job Match Scores**: We introduce a distinct `job_match_scores` table. While a match score could theoretically be a field on the `applications` table, separating it allows the background matching engine to score jobs *before* an application is initiated, fulfilling the "Job Matching" conceptual domain.

## Consequences
- **Positive:** Maximum flexibility for candidate attributes. Native support for provenance and semantic search across all candidate data. Perfect alignment with LangGraph state architecture.
- **Negative:** Querying candidate experience/education requires filtering the `memory_facts` table by `category`, which is slightly less ergonomic for standard relational queries but ideal for vector/LLM retrieval.

## Compliance Note
This decision brings Phase 1 into 100% conceptual compliance with Phase 0 `database-design.md` while optimizing for LLM-native patterns.
