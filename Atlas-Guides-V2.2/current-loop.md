# Atlas Guides — Current Story Loop

This file is a compact active-story audit record.

The runtime evidence store is authoritative for execution receipts.

## Story

```text
Story ID: 3.3
Title: Recommendations
Risk: LOW
Dependencies: Story 2.5
Loop: 1
State: CHECKING_1
```

## Story Scope & Acceptance Criteria
- **Objective**: Present prioritized suggested actions in a form useful to a human decision-maker.
- **Scope**: Priority, finding, why it matters, suggested next step, and evidence.
- **Acceptance Criteria**:
  - **AC-3.3.1**: Recommendations are prioritized and understandable.
  - **AC-3.3.2**: Recommendations include supporting information.
- **Rejection & Boundary Conditions**:
  - Recommendations must not be represented as completed actions.
  - Decision-support framing preserving human administrative and clinical authority (AC-2.5.3, FR-009).
  - Strict numerical grounding: All supporting metrics and deltas must trace directly to verified data or calculations (INV-002).
  - Zero PHI: Must not contain patient-identifying data (INV-008).
- **Failure Behavior**:
  - Unsupported recommendations are omitted or presented with an explicit limitation.

---

## Loop 1 — Builder

### 1. What I Built
- **"Actionable Recommendations" Interactive Dashboard Component ([`frontend/src/components/RecommendationsView.tsx`](file:///c:/Users/burns/OneDrive/Documents/GitHub/Ignite_Location_Dashboard_POC/frontend/src/components/RecommendationsView.tsx))**:
  - **Executive Action Roadmap Banner**: High-level leadership overview of prioritized cross-departmental alignment, snapshot date, scenario, and summary counters (Total Actions, High Priority, Medium Priority, Low Priority).
  - **Multi-Dimensional Filter Toolbar**:
    - **Priority Filter**: All Priorities, High Priority Only, Medium Priority Only, Low Priority Only.
    - **Time Horizon Filter**: All Timeframes, Immediate (24–48h), Short-Term (7 Days), Strategic (30 Days).
    - **Department Filter**: Dynamically populated from active department leads (e.g. Director of Nursing, Therapy Director, Case Management, Hospitality Director, Facility Leadership).
  - **5-Element Structured Recommendation Cards (AC-3.3.1, AC-3.3.2)**:
    1. **Header**: Action title, priority badge, time horizon badge, domain indicator, target role / department lead.
    2. **Operational Rationale ("Why This Action Was Suggested")**: Clear clinical, financial, or operational justification.
    3. **Suggested Practical Steps for Leadership Evaluation**: Concrete, structured action steps for administrative/clinical review.
    4. **Expected Operational Impact**: Projected benefit upon human execution.
    5. **Verifiable Supporting Metric Evidence**: Verifiable operational indicator tags grounded in telemetry.
  - **Decision Support & Human Authority Banner (AC-2.5.3, FR-009)**: Clear disclosure emphasizing that recommendations are decision-support suggestions for human review and never autonomous actions.
- **Frontend Type Definitions & Routing Integration ([`frontend/src/types.ts`](file:///c:/Users/burns/OneDrive/Documents/GitHub/Ignite_Location_Dashboard_POC/frontend/src/types.ts) & [`frontend/src/App.tsx`](file:///c:/Users/burns/OneDrive/Documents/GitHub/Ignite_Location_Dashboard_POC/frontend/src/App.tsx))**:
  - Added TypeScript interfaces: `OperationalRecommendation`, `FacilityRecommendationsSummary`, and `RecommendationReport`.
  - Wired the "Recommendations" tab to fetch `GET /api/agent/recommendations` dynamically on load and on scenario/facility change.
- **Story 3.3 Automated Test Suite ([`tests/test_recommendations_view.py`](file:///c:/Users/burns/OneDrive/Documents/GitHub/Ignite_Location_Dashboard_POC/tests/test_recommendations_view.py))**:
  - 5 comprehensive tests validating priority ordering (AC-3.3.1), supporting evidence metrics tracing (AC-3.3.2), rejection boundary on completed actions and human authority preservation, zero PHI & numerical grounding, and FastAPI REST endpoint validation across all 6 scenarios.

### 2. How I Approached It
- Leveraged the deterministic recommendation engine and grounding reconciler from Story 2.5 (`src/analytics/recommendations.py` & `src/agent/recommendation_agent.py`).
- Designed the UI specifically for facility executive leadership, structuring suggested actions into clean, non-technical cards with multi-dimensional filtering across priorities, time horizons, and departments.

### 3. Tests Added / Run
- `tests/test_recommendations_view.py::test_ac3_3_1_recommendations_prioritized_and_understandable` — PASSED
- `tests/test_recommendations_view.py::test_ac3_3_2_supporting_evidence_metrics_tracing` — PASSED
- `tests/test_recommendations_view.py::test_rejection_boundary_no_completed_actions_and_human_authority` — PASSED
- `tests/test_recommendations_view.py::test_ac3_3_zero_phi_and_grounding` — PASSED
- `tests/test_recommendations_view.py::test_fastapi_recommendations_endpoint` — PASSED
- Full repository test suite: `uv run pytest -v` (74/74 passed in 1.46s).
- Linters & Formatters: `uv run ruff check .` (0 errors) & `uv run ruff format --check .` (75 files formatted).
- Frontend production bundle: `cd frontend ; npm.cmd run build` (built in 2.76s).

### 4. Assumptions
- Recommendations generated across the 6 operational scenarios cover diverse departments and priorities, allowing leadership to filter dynamically.

### 5. Where to Look First
- `frontend/src/components/RecommendationsView.tsx`
- `tests/test_recommendations_view.py`
- `frontend/src/App.tsx`

### 6. Open Questions / Unresolved Risks
- None. Ready for Checker 1 audit.

---

## Current State

```text
Canonical State: CHECKING_1 (Story 3.3)
Status: Ready for Independent Checker 1 Audit
Blocker: None
```
