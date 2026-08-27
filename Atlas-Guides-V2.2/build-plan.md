# Atlas Guides — Build Plan

## Project: Ignite Facility Operational Decision Agent POC
**Specification:** `Ignite_Facility_Operational_Decision_Agent_POC_Spec_v0.1.md` (or `spec.md`)  
**Status:** APPROVED  
**Version:** 0.1  

---

## 1. Rules & Invariants

- Only approved stories enter execution.
- Dependencies must be satisfied before a story is eligible for `READY` -> `BUILDING_1`.
- Story state is controlled by the harness/runtime.
- Every story has at most two Builder/Checker passes:
  - Clean Loop 1: `READY` → `BUILDING_1` → `CHECKING_1` → `STORY_VERIFIED`
  - Loop 2: `BUILDING_2` → `CHECKING_2` (only if Checker 1 returns `FAILED` or `UNVERIFIED`)
- There is NO Loop 3.
- Only unresolved Checker 2 results reach Evaluator.
- Phase completion requires the Phase Gate.
- Finalization occurs once after all phases pass, followed by independent Finalization Review.

---

## 2. Phase & Story Sequence

### Phase 1 — Facility Data Foundation
**Risk:** LOW  
**Exit Conditions:**
- Representative synthetic facility data is available across all defined operational areas.
- Historical data is available for meaningful trend scenarios.
- The agent can retrieve the required data through the mock interface.

| Story ID | Title | Risk | Dependencies | Status |
|---|---|---|---|---|
| **1.1** | Create Facility Data Model | LOW | None | **STORY_VERIFIED** |
| **1.2** | Create Mock Domo MCP | LOW | 1.1 | **STORY_VERIFIED** |
| **GATE-1** | Phase 1 Gate | LOW | 1.1, 1.2 | **PHASE_GATE_PASSED** |

---

### Phase 2 — Operational Decision Analysis
**Risk:** MEDIUM  
**Exit Conditions:**
- Numerical calculations are accurate and traceable.
- Positive operational indicators and watch items are identified correctly across evaluation scenarios.
- The agent does not fabricate metrics or missing historical context.

| Story ID | Title | Risk | Dependencies | Status |
|---|---|---|---|---|
| **2.1** | Analyze Facility State | LOW | 1.1, 1.2 | **STORY_VERIFIED** |
| **2.2** | Explain Metrics and Historical Context | MEDIUM | 2.1 | **STORY_VERIFIED** |
| **2.3** | Identify Positive Performance | MEDIUM | 2.2 | **STORY_VERIFIED** |
| **2.4** | Identify Areas Requiring Attention | MEDIUM | 2.2 | **STORY_VERIFIED** |
| **2.5** | Generate Data-Grounded Recommendations | MEDIUM | 2.4 | **STORY_VERIFIED** |
| **GATE-2** | Phase 2 Gate | MEDIUM | 2.1 - 2.5 | **PHASE_GATE_PASSED** |

---

### Phase 3 — Human-Facing Experience
**Risk:** LOW  
**Exit Conditions:**
- A human can understand the facility state without technical knowledge.
- The interface clearly distinguishes positive performance, areas to watch, and action-needed items.
- The CIO-facing view explains the system and its limitations.

| Story ID | Title | Risk | Dependencies | Status |
|---|---|---|---|---|
| **3.1** | Facility Brief | LOW | 2.3, 2.4 | **STORY_VERIFIED** |
| **3.2** | What It Means | LOW | 2.2 | **STORY_VERIFIED** |
| **3.3** | Recommendations | LOW | 2.5 | **BUILDING_1** |
| **3.4** | Technical / How It Works | LOW | 1.2, 2.1, 2.5 | PENDING |
| **GATE-3** | Phase 3 Gate | LOW | 3.1 - 3.4 | PENDING |

---

### Phase 4 — Evaluation
**Risk:** MEDIUM  
**Exit Conditions:**
- Known test scenarios produce expected categories of behavior.
- Changing source data changes findings and recommendations.
- Missing, inconsistent, or unavailable data produces appropriate limitations.
- No production PHI or credentials are required.

| Story ID | Title | Risk | Dependencies | Status |
|---|---|---|---|---|
| **4.1** | Recommendation Evaluation | MEDIUM | 2.5 | PENDING |
| **4.2** | Failure and Boundary Testing | MEDIUM | 2.1, 2.5 | PENDING |
| **GATE-4** | Phase 4 Gate | MEDIUM | 4.1, 4.2 | PENDING |

---

### Finalization & Review
**Risk:** HIGH  
**Exit Conditions:**
- Recoverable baseline established.
- Whole-repository cleanup performed safely.
- Full verification suite passes.
- Independent Finalization Reviewer signs off.

| Step | Title | Dependencies | Status |
|---|---|---|---|
| **FIN-1** | Finalizer Cleanup & Verification | GATE-4 | PENDING |
| **FIN-2** | Finalization Reviewer Audit | FIN-1 | PENDING |

