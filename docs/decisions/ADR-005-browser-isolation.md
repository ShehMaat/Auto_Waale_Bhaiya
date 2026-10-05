# ADR-005: Browser Isolation

## Context
External job boards are untrusted. They may contain prompt injections or malicious scripts. Giving an LLM direct control over `page.evaluate()` or arbitrary shell commands is a critical security risk.

## Decision
We will implement a **Policy Engine** that sits between the LLM and Playwright. The LLM may only output JSON Action Intents (e.g., `{"action": "click", "selector": "#submit"}`). The Policy Engine validates these intents before translating them to Playwright commands.

## Consequences
- Prevents the agent from being hijacked via prompt injection (Principle 2 and 7).
- Increases the complexity of the browser worker service.
