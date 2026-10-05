# ADR-003: Memory Design

## Context
LLMs frequently hallucinate facts (e.g., inventing a degree to satisfy a job requirement). This is unacceptable for job applications.

## Decision
We will implement an **Evidence-Based Memory System**. Every fact extracted or inferred by the LLM is assigned a `SUGGESTED` status and a provenance tag. It cannot be used to fill a form until a human upgrades it to `CONFIRMED`.

## Consequences
- Requires the user to actively confirm extracted facts during onboarding or application time.
- Guarantees zero hallucinations in final applications (Principle 3 and 6).
