# ADR-004: Human in the Loop

## Context
Fully autonomous systems that submit applications without review can submit incorrect, embarrassing, or legally binding inaccurate information.

## Decision
The system is explicitly designed with **Hard Pauses** requiring human intervention:
1. **Missing Data:** If a required form field has no confirmed memory fact.
2. **Security Challenges:** If a CAPTCHA or OTP is detected (Principle 5).
3. **Final Submission:** (Principle 4) The `SUBMIT` action is disabled for the agent and exposed only as an explicit user API endpoint.

## Consequences
- Applications will block in a pending state until the user acts.
- Requires robust WebSocket or notification infrastructure to alert the user.
