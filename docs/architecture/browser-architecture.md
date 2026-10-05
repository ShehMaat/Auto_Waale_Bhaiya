# Browser Architecture

## 1. Browser Isolation
The browser worker uses Playwright. Following Principle 2 (Untrusted External Websites) and Principle 7 (Typed Browser Actions), the browser execution environment is heavily sandboxed.

## 2. The Policy Validator Engine
The LLM cannot send arbitrary JavaScript to Playwright. 
The LLM outputs an action intent. The Policy Validator Engine ensures:
- The action type is within the allowed list (`navigate`, `click`, `fill_text`, `select_option`, `upload_file`).
- The target element (CSS selector or XPath) is valid and visible.
- No cross-site scripting intents are present in the text to fill.

## 3. Handling Human-Only Interactions
Following Principle 5, CAPTCHAs, OTPs, and 2FA are explicitly handled by detecting common challenge patterns (e.g., iframes containing hCaptcha/reCAPTCHA, inputs labeled "Enter Code").
When detected:
1. The Playwright session state is paused.
2. A WebSocket event is emitted to the frontend notifying the user.
3. A secure proxy or VNC stream (or interactive debugging session) is exposed to the frontend allowing the user to manually solve the challenge.
4. Once the user solves it and signals completion, the orchestrator resumes the automated workflow.
