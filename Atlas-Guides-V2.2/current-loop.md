# Atlas Guides — Current Story Loop

This file is a compact active-story audit record.

The runtime evidence store is authoritative for execution receipts.

## Story

```text
Story ID: 2.5
Title: Generate Data-Grounded Recommendations
Risk: MEDIUM
Dependencies: Story 2.1, 2.2, 2.3, 2.4
Loop: 1
State: BUILDING_1
```

## Story Scope & Acceptance Criteria
- **Objective**: Synthesize prioritized, actionable, data-grounded operational recommendations derived directly from identified attention areas and cross-domain compound risks.
- **Scope**: Departmental and executive recommendation generation, rationale and evidence linking, dynamic data-responsiveness, decision-support framing (human authority), and numerical grounding reconciliation.
- **Acceptance Criteria**:
  - **AC-2.5.1**: Each recommendation identifies why it was suggested (explicit clinical/financial/operational rationale and supporting evidence metrics).
  - **AC-2.5.2**: Changing relevant source data dynamically alters the resulting recommendations (demonstrating dynamic reasoning without hardcoded scenario mapping).
  - **AC-2.5.3**: Recommendations are clearly presented as suggestions for human decision-makers rather than autonomous actions (FR-009).
- **Rejection & Boundary Conditions**:
  - Rejection: Must not claim an action was performed or make autonomous clinical decisions.
  - Boundary: Must not generate generic canned recommendations untethered from facility data (INV-001).
  - Strict numerical grounding: all metrics, targets, and variances cited in recommendations must trace directly to data (INV-002, AC-2.1.2).
  - Zero PHI: zero patient-identifying data in outputs (INV-008).
- **Failure Behavior**:
  - Spec §8 deterministic fallback (`AI_ANALYSIS_UNAVAILABLE`) when live LLM keys are absent.
  - Insufficient context reports explicit limitation.

---

## Loop 1 — Builder

### 1. What I Built
- **Deterministic Recommendations Engine (`src/analytics/recommendations.py`)**:
  - Implemented `generate_deterministic_recommendations` transforming attention areas, deficit breaches, and cross-domain compound risks into actionable operational recommendations (AC-2.5.1, AC-2.5.2).
  - Explicit justification for every suggested action (`rationale` and `supporting_evidence_metrics` per AC-2.5.1).
  - Departmental role assignment (e.g. Director of Nursing, Case Management, Director of Rehabilitation, Culinary Services).
  - Time horizon tagging (`IMMEDIATE_24H`, `SHORT_TERM_7D`, `STRATEGIC_30D`) and priority rating (`HIGH`, `MEDIUM`, `LOW`).
  - Decision-support governance disclaimer on every recommendation preserving human administrative and clinical authority (AC-2.5.3, FR-009).
  - Proactive continuous improvement recommendations for normal/healthy operations.
- **Facility Recommendation Agent (`src/agent/recommendation_agent.py`)**:
  - Synthesizes `RecommendationReport` containing executive action plan roadmaps, prioritized recommendations, departmental action breakdowns, and explicit decision authority notices.
  - Strictly enforces `NumericalGroundingReconciler` across all narrative fields (INV-002, AC-2.1.2).
  - Implements Spec §8 compliant fallback (`AI_ANALYSIS_UNAVAILABLE`) when live LLM keys are absent.
- **REST API Endpoints (`src/api/routes.py`)**:
  - `GET /api/agent/recommendations`: Exposes recommendation report with verified calculations, supporting evidence, and LLM audit receipt.
- **Test Suite (`tests/test_recommendation_agent.py`)**:
  - 8 comprehensive tests covering AC-2.5.1 (rationale & evidence metrics), AC-2.5.2 (dynamic sensitivity across scenarios: staffing stress, transfer spike, auth cliff, baseline), AC-2.5.3 / FR-009 (decision-support framing & zero autonomous claims), numerical grounding reconciler, Spec §8 offline fallback, zero PHI invariants, and FastAPI REST endpoints.

### 2. How I Approached It
- Directly linked recommendations to verified deficit metrics and cross-domain compound correlations.
- Enforced strict human decision authority framing across all levels of output.

### 3. Tests Added / Run
- `tests/test_recommendation_agent.py::test_ac2_5_1_every_recommendation_has_rationale_and_evidence` — PASSED
- `tests/test_recommendation_agent.py::test_ac2_5_2_changing_source_data_dynamically_alters_recommendations` — PASSED
- `tests/test_recommendation_agent.py::test_ac2_5_3_decision_support_framing_and_human_authority` — PASSED
- `tests/test_recommendation_agent.py::test_ac2_5_strict_numerical_grounding_reconciliation` — PASSED
- `tests/test_recommendation_agent.py::test_spec_section_8_offline_recommendations_fallback` — PASSED
- `tests/test_recommendation_agent.py::test_boundary_no_phi_in_recommendation_output` — PASSED
- `tests/test_recommendation_agent.py::test_failure_behavior_unavailable_facility_raises_error` — PASSED
- `tests/test_recommendation_agent.py::test_fastapi_recommendations_endpoint` — PASSED
- Full repository test suite: `uv run pytest -v` (58/58 passed in 1.11s).
- Linter & Formatter: `uv run ruff check .` (0 errors) & `uv run ruff format --check .` (clean, 69 files).

### 4. Assumptions
- Phase 2 stories (2.1, 2.2, 2.3, 2.4, 2.5) form the complete intelligence foundation for Phase 3 UI dashboards.

### 5. Where to Look First
- `src/analytics/recommendations.py` (`generate_deterministic_recommendations`, `OperationalRecommendation`)
- `src/agent/recommendation_agent.py` (`FacilityRecommendationAgent`, `generate_recommendations`)
- `src/api/routes.py` (`GET /api/agent/recommendations`)
- `tests/test_recommendation_agent.py`

### 6. Open Questions / Unresolved Risks
- None. Ready for Checker 1 audit.

---

## Loop 1 — Checker

Populate only if the harness routed the story here.

---

## Loop 2 — Builder

Populate only if the harness routed the story here.

---

## Loop 2 — Checker

Populate only if the harness routed the story here.

---

## Evaluation

Populate only when Checker 2 remains unresolved.

---

## Current State

```text
Canonical State: CHECKING_1 (Story 2.5)
Blocker: None
```
