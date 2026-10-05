# System Architecture

## System Overview

```mermaid
flowchart TD
    UI[Next.js UI] -->|HTTP/REST| API[FastAPI API]
    API --> DB[(PostgreSQL + pgvector)]
    API --> Redis[Redis]
    API --> MinIO[(MinIO Object Storage)]
    
    DB -->|Candidate/Job/App Data| DecisionServices[Semantic / Decision Services]
    Redis -->|Tasks| Celery[Celery Background Workers]
    
    Celery -->|Spawns| BrowserWorker[Browser Worker]
    DecisionServices -->|Validates Actions| BrowserWorker
    
    BrowserWorker --> Playwright[Playwright / Chromium]
    Playwright --> ATS[External Job / ATS Website]
```

## AI Decision Pipeline

Note: The LLM is NOT the source of truth and cannot directly execute arbitrary browser actions. It produces reasoning which must pass strict, deterministic action validation.

```mermaid
flowchart TD
    LLM[LLM Provider] -->|Structured Reasoning| DecisionEngine[Decision Engine]
    DecisionEngine -->|Generates| Action[Typed Browser Action]
    Action --> Validator[Action Validator]
    Validator --> SecurityPolicy[Browser Security Policy]
    SecurityPolicy -->|Passes Policy| Worker[Browser Worker]
    Worker --> Playwright[Playwright Automation]
    Playwright --> Target[Target Website]
    
    classDef untrusted fill:#ffcccc,stroke:#ff0000,stroke-width:2px,color:#000;
    class LLM untrusted
```
