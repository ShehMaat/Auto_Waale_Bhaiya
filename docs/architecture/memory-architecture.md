# Memory Architecture

## 1. Provenance and Evidence-Based Memory
Following Principle 6, the agent's memory is completely evidence-based. It is a strictly controlled graph of facts, where every fact is tagged with its provenance.

## 2. Memory Types
1.  **Core Profile:** Immutable facts established during onboarding (Name, Email).
2.  **Extracted Facts:** Facts parsed from uploaded resumes/documents (e.g., "Worked at Google from 2020-2023"). These are marked `PROVENANCE_RESUME`.
3.  **Inferred Facts:** Facts the LLM deduces during an application (e.g., "Willing to relocate"). These are marked `PROVENANCE_INFERENCE` and set to `status = SUGGESTED`.

## 3. The Trust Boundary (Anti-Hallucination)
Principle 3 demands the system never hallucinate.
When filling an application form, the agent queries the memory vector store for relevant facts.
- If a `CONFIRMED` fact is found, it is used.
- If only `SUGGESTED` facts exist, or no facts exist, the agent CANNOT proceed. It must pause the workflow and generate a request to the user via the API (`POST /human-interventions`).

Only after the human responds via the Next.js frontend (e.g., clicking "Confirm" or entering a new value) does the fact become `status = CONFIRMED` with `PROVENANCE_USER_INPUT`, allowing the application to proceed.
