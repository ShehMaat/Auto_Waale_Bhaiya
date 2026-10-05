# ADR-002: Agent Orchestration

## Context
LLMs given raw tools and unconstrained loops (e.g., ReAct agents) are prone to wandering, infinite loops, and executing dangerous actions.

## Decision
We will use **LangGraph** to model the agent as a strict state machine rather than an autonomous loop.
The agent must transition through predefined states (`DISCOVER`, `MATCH`, `APPLY`, `REVIEW`, `SUBMIT`).

## Consequences
- Reduces the agent's autonomy but drastically increases safety.
- Easier to audit and debug where an application failed.
- Enforces Principle 1 (LLM as Reasoner).
