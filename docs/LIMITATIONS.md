# AI Job Application Agent — System Limitations & Boundary Disclosures

This document outlines the architectural, environmental, and operational boundaries of the **AI Job Application Agent (v1.0.0)**. These boundaries represent deliberate security constraints and technical trade-offs.

---

## 1. No Guaranteed Universal ATS Compatibility
- The agent is designed and validated against standard, modern web form patterns and common ATS platforms (e.g., Lever, Greenhouse, Ashby, standard multi-page HTML forms).
- **Arbitrary ATS compatibility is not guaranteed**. Enterprise portals using proprietary canvas rendering, heavily obfuscated dynamic JavaScript, or unsupported nested shadow-DOM structures may not be parsed accurately and will trigger a safe, fail-closed pause.

---

## 2. External Anti-Bot & WAF Systems
- Third-party job boards and ATS platforms often implement bot-mitigation technologies (such as Cloudflare Turnstile, Imperva/Incapsula, DataDome, Akamai Bot Manager, or AWS WAF).
- The agent **does not attempt to evade or bypass** these protections. When an anti-bot challenge is encountered, the agent safely transitions to `WAITING_FOR_USER` or aborts the run without attempting adversarial bypasses.
- *Evidence*: In Phase 16 validation against GlobalLogic, the agent encountered an Imperva WAF challenge page and correctly failed closed.

---

## 3. Mandatory Human Intervention for CAPTCHA
- The platform does not possess or utilize CAPTCHA-solving capabilities.
- Any form requiring reCAPTCHA, hCaptcha, Turnstile, or visual puzzle completion requires the user to interactively solve the challenge via the browser session.

---

## 4. Mandatory Human Intervention for OTP / 2FA
- Time-based One-Time Passwords (TOTP), SMS verification codes, or email confirmation links cannot be autonomously retrieved or completed by the agent.
- Encountering a two-factor authentication challenge pauses automation until the candidate provides the required token.

---

## 5. Explicit Submission Authorization Boundary
- Autonomous final application submission is **categorically prohibited** by design.
- The `DecisionEngine` intercepts final submission buttons and halts at `READY_FOR_REVIEW`.
- A human must review the completed application and provide explicit authorization before any application is transmitted.

---

## 6. Limited HR Outcome Ingestion
- Post-application communication (e.g., recruiter interview invitations, screening questions sent via email, automated rejection notices) is not automatically parsed or ingested by the v1.0.0 core.
- Application status transitions to `INTERVIEWING` or `REJECTED` currently rely on user updates or supported direct webhook notifications.

---

## 7. Analytics Outcome Coverage
- Analytics and funnel conversion metrics are strictly bound to authoritative telemetry recorded within the system.
- Outcomes originating outside the platform without manual candidate input or direct ATS connector confirmation cannot be tracked.

---

## 8. Web Behavior Dependencies
- Browser automation is powered by Playwright and requires web pages to follow standard DOM events (focus, change, click, blur).
- Non-standard inputs (e.g., custom drag-and-drop file areas lacking file input elements, virtualized scroll listboxes without DOM elements) may require manual user completion via HITL.
