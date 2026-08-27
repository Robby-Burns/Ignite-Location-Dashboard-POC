# Atlas Guides — Project Specification

## Approval State

```text
Status: APPROVED
Version: 0.1
Project: Ignite Facility Operational Decision Agent POC
Authoritative Specification File: Ignite_Facility_Operational_Decision_Agent_POC_Spec_v0.1.md
Approved By: human owner / team
Approved At: 2026-08-27
```

> **Authoritative Specification:** See `Ignite_Facility_Operational_Decision_Agent_POC_Spec_v0.1.md` for the complete 24-section project specification contract.

## 1. Project Objective
Build a proof-of-concept operational decision agent that reviews facility data and helps a human understand what is happening across a medical facility. The agent identifies meaningful changes, explains what the numbers mean in plain language, identifies what is going well, identifies what may need attention, and provides suggested next steps. The POC simulates the Domo data connection via a mock Domo MCP.

## 2. Phases Summary
- **Phase 1 — Facility Data Foundation** (Risk: LOW)
  - Story 1.1: Create Facility Data Model
  - Story 1.2: Create Mock Domo MCP
- **Phase 2 — Operational Decision Analysis** (Risk: MEDIUM)
  - Story 2.1: Analyze Facility State
  - Story 2.2: Explain Metrics and Trends
  - Story 2.3: Identify Positive Performance
  - Story 2.4: Identify Areas Requiring Attention
  - Story 2.5: Generate Data-Grounded Recommendations
- **Phase 3 — Human-Facing Experience** (Risk: LOW)
  - Story 3.1: Facility Brief
  - Story 3.2: What It Means
  - Story 3.3: Recommendations
  - Story 3.4: Technical / How It Works
- **Phase 4 — Evaluation** (Risk: MEDIUM)
  - Story 4.1: Recommendation Evaluation
  - Story 4.2: Failure and Boundary Testing

---
*For full acceptance criteria, invariants, input/output schemas, and non-functional requirements, refer to `Ignite_Facility_Operational_Decision_Agent_POC_Spec_v0.1.md`.*

