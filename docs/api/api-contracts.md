# API Contracts

## 1. Overview
The REST API serves as the primary interface between the Next.js frontend and the FastAPI backend. It enforces human-in-the-loop controls.

## 2. Key Endpoints

### 2.1 Applications
- `GET /applications` - List applications.
- `GET /applications/{id}` - Get application status and event log.
- `POST /applications/{id}/approve-submission` - **Critical Endpoint:** Explicitly approves the final submission of a validated application form (Enforces Principle 4).
- `POST /applications/{id}/reject` - Aborts the application process.

### 2.2 Memory and Facts
- `GET /memory` - List all candidate facts.
- `POST /memory/{fact_id}/confirm` - Promotes a `SUGGESTED` fact to `CONFIRMED` (Enforces Principle 6).
- `PUT /memory/{fact_id}` - User edits a fact, marking it as `CONFIRMED` with `PROVENANCE_USER_INPUT`.

### 2.3 Interventions
- `GET /interventions/pending` - List tasks requiring human attention (e.g., CAPTCHAs, missing info).
- `POST /interventions/{id}/resolve` - Submits the human's solution or provided data, unpausing the state machine (Enforces Principle 5).

## 3. WebSockets
- `/ws/applications/{id}` - Real-time stream of state changes, browser actions, and intervention requests.
