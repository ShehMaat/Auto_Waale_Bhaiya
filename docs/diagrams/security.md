# Security Architecture & Threat Model

## Security Architecture

```mermaid
flowchart TD
    Auth[User Authentication] --> Own[Authorization / Ownership]
    Own --> Isol[Application Isolation]
    Isol --> Untrusted[Untrusted Web Content]
    Untrusted --> Insp[Page Inspection]
    Insp --> InjectDef[Prompt Injection Defense]
    InjectDef --> Typed[Typed Actions]
    Typed --> Valid[Action Validation]
    Valid --> SecPol[Security Policy]
    SecPol --> Sens[Sensitive Field Protection]
    Sens --> HITL[HITL Boundary]
    HITL --> Snap[Fresh Submission Snapshot]
    Snap --> Boundary((Explicit Authorization))
    Boundary --> Submit[Submission]

    style Boundary fill:#ff9900,stroke:#333,stroke-width:4px,color:#000
```

*Note: The security architecture includes protections for SSRF, DNS rebinding, browser context isolation, memory provenance/trust verification, replay protection, stale approval protection, fail-closed behavior, and complete auditability.*

## Threat Model

```mermaid
flowchart LR
    subgraph Threats
        T1(Untrusted Job)
        T2(Untrusted Webpage)
        T3(Malicious Prompt Injection)
        T4(Malicious Document)
        T5(Sensitive Candidate Data)
        T6(Stale Approval)
        T7(Replay Attempt)
        T8(Cross-user Access Attempt)
        T9(External Anti-bot Challenge)
    end

    subgraph Controls
        C1[Structured Schema Enforcement]
        C2[Prompt Injection Defense]
        C3[MinIO S3 / Pre-signed URLs]
        C4[HITL Interruption]
        C5[Single-Use Redis Tokens & State Gating]
        C6[Tenant/User Row-Level Scoping]
        C7[Fail-Closed Execution / Pause]
    end

    T1 -.->|Mitigated by| C1
    T2 -.->|Mitigated by| C1
    T3 -.->|Mitigated by| C2
    T4 -.->|Mitigated by| C3
    T5 -.->|Mitigated by| C4
    T6 -.->|Mitigated by| C5
    T7 -.->|Mitigated by| C5
    T8 -.->|Mitigated by| C6
    T9 -.->|Mitigated by| C7
```
