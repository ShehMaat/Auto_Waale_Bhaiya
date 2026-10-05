# AI Job Application Agent — Deterministic Demonstration Guide

This guide provides a reproducible, step-by-step walkthrough to demonstrate the core capabilities, human-in-the-loop (HITL) interventions, and explicit submission boundaries of the **AI Job Application Agent (v1.0.0)**.

> **Demonstration Standard**:
> Always use the controlled **Golden ATS** for demonstrating successful application workflows.
> **Do NOT use GlobalLogic as the successful application demo.** GlobalLogic is strictly a safety/fail-closed validation example demonstrating anti-bot response.
> 
> *See the [Golden Application Workflow Diagram](diagrams/workflow.md) for a visual representation of this process.*

---

## 1. Prerequisites & Environment Setup

1. **Start Core Services**:
   ```bash
   docker compose up -d postgres redis minio
   ```
2. **Apply Migrations**:
   ```bash
   uv run alembic upgrade head
   ```
3. **Start the API Server**:
   ```bash
   uv run uvicorn apps.api.app.main:app --port 8000 --reload
   ```
4. **Start the Celery Worker**:
   ```bash
   uv run celery -A apps.api.app.worker.celery_app worker --loglevel=info
   ```
5. **Start the Frontend**:
   ```bash
   cd apps/web && npm run dev
   ```
6. **Launch the Golden ATS Mock Server**:
   ```bash
   uv run python tests/fixtures/golden_ats/app.py --port 5000
   ```

---

## 2. Step-by-Step Golden ATS Demo Flow

```
[ Step 1: Login ]
      |
      v
[ Step 2: Dashboard Overview ]
      |
      v
[ Step 3: Job Discovery & Selection ]
      |
      v
[ Step 4: Initiate Application ]
      |
      v
[ Step 5: Automated Form Filling (Known Fields) ]
      |
      v
[ Step 6: Dynamic Fields Navigation ]
      |
      v
[ Step 7: HITL Interruption (Unknown Required Field: "office_snack") ]
      |
      v
[ Step 8: User Provides Answer via Dashboard ]
      |
      v
[ Step 9: Automatic Resume Upload (MinIO S3) ]
      |
      v
[ Step 10: Final Review Screen (READY_FOR_REVIEW) ]
      |
      v
[ Step 11: Explicit Submission Authorization Boundary ]
      |
      v
[ Step 12: Application Completed & Analytics Updated ]
```

### Detailed Steps:

1. **Login**:
   - Navigate to `http://localhost:3000/login`.
   - Log in with test candidate credentials (`testuser@example.com` / `password123`).
2. **Dashboard Overview**:
   - View profile completeness, candidate skills summary, and past application statistics.
3. **Jobs Feed**:
   - Navigate to the **Jobs** tab.
   - Point out the semantic match score (e.g., 94% Match) and skill breakdown for the "Senior Full-Stack Engineer" position hosted on the local Golden ATS (`http://localhost:5000`).
4. **Initiate Application**:
   - Click **Apply with Agent**.
   - Note the state machine transition to `ApplicationStatus.IN_PROGRESS`.
5. **Browser Automation (Known Fields)**:
   - The browser worker launches an isolated Chromium context.
   - Standard fields (First Name, Last Name, Email, Phone, LinkedIn) are populated automatically from confirmed memory.
6. **Dynamic Fields Navigation**:
   - The worker navigates past page 1 to the custom questionnaires page.
7. **HITL Interruption**:
   - The form presents a mandatory unmapped question: `"What is your favorite office snack?"`.
   - The `DecisionEngine` detects that this field has no confirmed memory match.
   - **System Halts**: Status changes to `ApplicationStatus.WAITING_FOR_USER`.
   - The browser pauses; an intervention notification appears on the dashboard.
8. **User Response**:
   - The user opens the pending challenge modal in the UI and types: `"Almonds and Dark Chocolate"`.
   - Clicks **Submit Response**. The answer is saved into verified candidate memory, and the browser automation resumes.
9. **Resume Upload**:
   - The worker automatically downloads the candidate's verified resume from MinIO storage and attaches it via the form's file input.
10. **Final Review Halt (`READY_FOR_REVIEW`)**:
    - The worker reaches the final page where a "Submit Application" button is visible.
    - **Submission Boundary Triggered**: The `DecisionEngine` intercepts the button, suppresses the click, and transitions the state to `READY_FOR_REVIEW`.
11. **Explicit Submission Authorization**:
    - The user inspects the review screen displaying all filled values and attachments.
    - The user clicks the green **Approve & Submit Application** button.
    - The worker dispatches the submission with the user's explicit authorization token.
12. **Analytics & Funnel Verification**:
    - Navigate to the **Analytics** tab.
    - Observe the updated funnel metrics: Application Status is now `APPLIED`, with complete audit timeline and timing telemetry recorded.

---

## 3. Safety & Fail-Closed Demo (GlobalLogic)

To demonstrate safety policies under adversarial or bot-protected conditions:

1. Execute the real-world validation script:
   ```bash
   uv run python scripts/validate_real_globallogic.py
   ```
2. **Observed Behavior**:
   - The browser worker navigates to the external GlobalLogic career portal.
   - The portal returns an Imperva WAF / anti-bot challenge page.
3. **Safety Verification**:
   - The `DecisionEngine` and `BrowserSecurityPolicy` recognize the security barrier.
   - Execution terminates safely with a notification to the user.


