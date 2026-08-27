# Atlas Guides — Project Specification

## Status

```text
Status: DRAFT | APPROVED | AMENDED | BLOCKED
Version: 0.1
Project:
Owner:
Approved By:
Approved At:
```

> This document defines **what must be true** for the project to be considered correct.
> It does not define which model, IDE, agent runtime, or implementation technique must be used.

---

# 1. Project Overview

## 1.1 Name

Ignite Facility Operational Decision Agent POC

## 1.2 Objective

Build a proof-of-concept operational decision agent that reviews facility data and helps a human understand what is happening across a medical facility.

The agent should identify meaningful changes, explain what the numbers mean in plain language, identify what is going well, identify what may need attention, and provide suggested next steps.

The POC will simulate the Domo data connection because live Domo MCP access is not currently available.

## 1.3 Problem

Facility leaders have access to operational information across multiple areas, but individual metrics do not always explain what is changing, why it matters, or what should be considered next.

The POC demonstrates how an AI application can turn facility data into understandable decision support rather than simply displaying another set of dashboards or metrics.

## 1.4 Desired Outcome

A human facility leader can use the application to quickly understand the current facility situation, what has changed, what is going well, what needs attention, why an item matters, and what action may be worth considering.

The POC also makes the system understandable to a CIO by showing where data came from, what was calculated, what the AI interpreted, what supports each recommendation, and what the system cannot determine.

The POC must demonstrate that findings and recommendations respond to the underlying data rather than being hard-coded to specific demonstration scenarios.

---

# 2. Users / Actors

| Actor | Role | Needs / Responsibilities |
|---|---|---|
| Facility Leader | Primary user | Understand facility performance and decide what requires attention
Operations / Clinical Leadership | Secondary user | Review trends, issues, and suggested actions
CIO / Technology Leadership | POC reviewer | Understand data flow, AI behavior, calculations, limitations, and technical design
Operational Decision Agent | Decision-support system | Review available facility information and produce understandable findings and recommendations
Mock Domo MCP | POC data source | Provide representative facility data through an MCP-style interface |

---

# 3. Scope

## 3.1 In Scope

- Facility operational snapshot
- Census and occupancy
- Admissions and discharges
- Length-of-stay information
- Therapy participation and progress indicators
- Staffing coverage and staffing changes
- Payer and authorization information
- Guest experience and hospitality information
- Hospital transfer indicators
- Historical data for trend and change analysis
- Plain-language explanation of metrics
- Identification of positive performance
- Identification and prioritization of areas requiring attention
- Data-grounded recommendations
- Supporting evidence for findings and recommendations
- CIO-facing technical explanation
- Mock Domo MCP data source
- Evaluation of whether outputs change when underlying data changes

## 3.2 Out of Scope

- Facility operational snapshot
- Census and occupancy
- Admissions and discharges
- Length-of-stay information
- Therapy participation and progress indicators
- Staffing coverage and staffing changes
- Payer and authorization information
- Guest experience and hospitality information
- Hospital transfer indicators
- Historical data for trend and change analysis
- Plain-language explanation of metrics
- Identification of positive performance
- Identification and prioritization of areas requiring attention
- Data-grounded recommendations
- Supporting evidence for findings and recommendations
- CIO-facing technical explanation
- Mock Domo MCP data source
- Evaluation of whether outputs change when underlying data changes

## 3.3 Explicit Non-Goals

- Facility operational snapshot
- Census and occupancy
- Admissions and discharges
- Length-of-stay information
- Therapy participation and progress indicators
- Staffing coverage and staffing changes
- Payer and authorization information
- Guest experience and hospitality information
- Hospital transfer indicators
- Historical data for trend and change analysis
- Plain-language explanation of metrics
- Identification of positive performance
- Identification and prioritization of areas requiring attention
- Data-grounded recommendations
- Supporting evidence for findings and recommendations
- CIO-facing technical explanation
- Mock Domo MCP data source
- Evaluation of whether outputs change when underlying data changes

---

# 4. Inputs

Define the information, data, files, events, or external systems the solution receives.

| Input | Source | Format | Required? | Constraints |
|---|---|---|---|---|
| Facility census and occupancy | Mock Domo MCP | Structured records | Yes | Synthetic data only |
| Admissions and discharges | Mock Domo MCP | Structured records | Yes | Synthetic data only |
| Therapy and patient progress indicators | Mock Domo MCP | Structured records | Yes | Operational indicators only; no clinical diagnosis |
| Staffing and coverage | Mock Domo MCP | Structured records | Yes | Synthetic data only |
| Payer and authorization information | Mock Domo MCP | Structured records | Yes | Synthetic data only |
| Guest experience / hospitality | Mock Domo MCP | Structured records | Yes | Synthetic data only |
| Historical facility metrics | Mock Domo MCP | Structured records | Yes | Must support comparison/trend analysis |
| Facility targets or contextual benchmarks | Mock Domo MCP | Structured records | Optional | Used only when available; absence must not be silently treated as failure |

---

# 5. Outputs

Define the observable outputs the system must produce.

| Output | Consumer | Format | Required Behavior |
|---|---|---|---|
| Facility Brief | Facility Leader | Human-readable interface | Summarizes current state, positive performance, areas requiring attention, and key changes |
| What It Means | Facility Leader | Human-readable interface | Explains important numbers, changes, and why they matter |
| Recommendations | Facility Leader | Human-readable interface | Provides prioritized, data-grounded suggested next steps with supporting evidence |
| Technical / How It Works | CIO / Technology Leadership | Human-readable interface | Explains data sources, calculations, AI reasoning, evidence, limitations, and POC boundaries |

---

# 6. Functional Requirements

## FR-001 — Review Facility Data

**Requirement**

The system must review available facility information across the defined operational areas.

**Behavior**

The system should use available current and historical information to establish a picture of facility operations.

**Failure behavior**

If required information is unavailable, the system must identify the missing information and must not present unsupported conclusions as facts.

## FR-002 — Explain What the Numbers Mean

**Requirement**

The system must translate important facility metrics into plain-language meaning for a human user.

**Behavior**

For meaningful metrics or changes, the output should explain the current value, relevant comparison or trend, and why the information may matter.

**Failure behavior**

If the system lacks sufficient context to interpret a metric, it must state that limitation rather than inventing a meaning.

## FR-003 — Identify What Is Going Well

**Requirement**

The system must identify positive facility performance when supported by the available data.

**Behavior**

Positive findings should be based on current values, changes over time, comparisons, or available facility context.

**Failure behavior**

The system must not manufacture positive findings when the data does not support them.

## FR-004 — Identify What Needs Attention

**Requirement**

The system must identify and prioritize meaningful operational conditions that may require human attention.

**Behavior**

The system should consider current conditions, changes over time, relationships between relevant data, and available context.

**Failure behavior**

The system must not identify a condition as a fact when the available data does not support it.

## FR-005 — Generate Recommendations

**Requirement**

The system must provide suggested next steps for identified areas requiring attention.

**Behavior**

Recommendations must be generated from the available information and should explain why the recommendation was made.

Recommendations are suggestions for human review and action.

**Failure behavior**

If the system cannot support a reasonable recommendation with available information, it must say so rather than inventing one.

## FR-006 — Support Accurate Numerical Analysis

**Requirement**

Numerical calculations, comparisons, percentages, averages, changes, and trends presented to the user must be accurate and traceable to the available data.

**Behavior**

The system must separate reliable numerical analysis from natural-language interpretation. Numerical results must not be invented by the language model.

**Failure behavior**

Calculation errors, missing values, or insufficient data must be surfaced rather than silently producing a result.

## FR-007 — Ground Findings in Evidence

**Requirement**

Important findings and recommendations must identify the information that supports them.

**Behavior**

A human user should be able to understand which facility metrics, changes, or relationships contributed to a finding.

**Failure behavior**

The system must not present unsupported reasoning as evidence.

## FR-008 — Avoid Hard-Coded Intelligence

**Requirement**

Findings, prioritization, explanations, and recommendations must respond to the supplied data rather than being hard-coded for predetermined demonstration scenarios.

**Behavior**

Changing relevant input data should be capable of changing the resulting interpretation or recommendation.

**Failure behavior**

If output remains tied to a predetermined scenario rather than the supplied data, the behavior does not satisfy this requirement.

## FR-009 — Maintain Human Decision Authority

**Requirement**

The system must present recommendations as decision support rather than autonomous decisions.

**Behavior**

The output should clearly distinguish observations and analysis from suggested actions. Human users remain responsible for deciding whether and how to act.

**Failure behavior**

The system must not claim that a recommendation has been executed or that a human decision has been made when neither occurred.

## FR-010 — Provide CIO-Facing Technical Transparency

**Requirement**

The application must provide a human-readable explanation of how the POC works.

**Behavior**

The technical view should explain the data source, data flow, numerical analysis, AI interpretation, recommendation generation, evidence, limitations, and the difference between the mock Domo connection and a potential production integration.

**Failure behavior**

The technical view must not imply that the POC has a live Domo integration when it does not.

# 7. Behavioral Rules / Invariants

These are rules that must remain true regardless of implementation.

## INV-001

The system must not present a hard-coded finding or recommendation as though it were derived from the current facility data.

## INV-002

Numbers shown to the user must be traceable to available input data or documented calculations.

## INV-003

The system must distinguish between what the data shows, what the system infers, and what it recommends.

## INV-004

The system must not invent missing data, clinical facts, causes, or outcomes.

## INV-005

When evidence is insufficient or ambiguous, the system must communicate uncertainty or limitation.

## INV-006

Recommendations remain suggestions for human review. The system must not represent a recommendation as an executed action or human decision.

## INV-007

The system must use historical information when available to identify meaningful changes and trends rather than relying only on a single point-in-time value.

## INV-008

Synthetic POC data must not contain real patient PHI.

# 8. Failure, Recovery, and Fallback Behavior

For each meaningful failure path:

| Failure | Detection | Required Response | Recovery | User/System State |
|---|---|---|---|---|
| Mock Domo data unavailable | Tool/data request fails | Clearly report that current data could not be retrieved | Retry or restore mock source | Data unavailable |
| Required data missing | Required field or dataset unavailable | Identify the missing information and limit affected conclusions | Provide corrected data | Partial analysis |
| Invalid or inconsistent data | Validation/calculation detects issue | Do not silently use unreliable values | Correct or exclude affected data | Analysis limited |
| Numerical calculation failure | Calculation error | Do not present an unverified number | Retry or report unavailable calculation | Calculation unavailable |
| LLM unavailable | AI request fails | Do not fabricate interpretation or recommendation | Retry when appropriate | Analysis unavailable |
| Insufficient evidence | Agent cannot support conclusion | State uncertainty and avoid unsupported recommendation | Obtain additional context/data | Insufficient evidence |

## Explicit Failure States

```text
DATA_UNAVAILABLE
PARTIAL_DATA
CALCULATION_UNAVAILABLE
AI_ANALYSIS_UNAVAILABLE
INSUFFICIENT_EVIDENCE
ANALYSIS_COMPLETE
```

## Fallback Rules

The system must prefer an explicit limitation over an invented result.

If AI interpretation is unavailable, the system may still display validated raw or calculated metrics when those values are available, but must not substitute hard-coded AI conclusions.

## Retry Rules

Retry transient data or AI failures when appropriate. Retries must not create duplicate side effects because the POC does not perform autonomous external actions.

## Idempotency Requirements

The POC does not perform external operational actions. Re-running an analysis must not create duplicate external side effects.

# 9. Security / Data Requirements

## Authentication

Live production authentication is out of scope for this POC. Any mock connection must use local/non-production configuration.

## Authorization

The POC must not expose real patient information or production systems.

## Data Protection

All demonstration data must be synthetic or appropriately de-identified. The POC must not require real PHI.

## Secrets

Production credentials, Domo credentials, and other real secrets must not be embedded in source code or mock data.

## Audit / Traceability

The system should retain enough information during the POC to understand what data supported a finding or recommendation and distinguish calculated values from AI-generated interpretation.

## Privacy / Compliance

The POC must use synthetic data and must not be presented as handling production PHI or as a validated clinical decision-support system.

# 10. Performance / Reliability Requirements

Only include measurable requirements that matter.

| Requirement | Target | Measurement |
|---|---|---|
| Response time | [target] | [measurement] |
| Throughput | [target] | [measurement] |
| Availability | [target] | [measurement] |
| Recovery | [target] | [measurement] |

---

# 11. Integration Requirements

| Integration | Purpose | Required Behavior | Failure Behavior |
|---|---|---|---|
| Mock Domo MCP | Simulate the facility data source | Provide representative facility data through an MCP-style interface | Clearly report unavailable or incomplete data |
| AI analysis capability | Interpret available information and generate explanations/recommendations | Produce data-grounded human-readable analysis | Do not fabricate analysis if unavailable |

The POC must preserve a clear boundary between the agent and the data source so that a future Domo MCP connection can replace the mock source without changing the intended user experience or decision-support behavior.

# 12. Constraints

## Technical

- Live Domo MCP access is not available for the POC.
- The Domo data source must therefore be simulated.
- Numerical accuracy must be maintained independently of language-model prose generation.
- Findings and recommendations must not be hard-coded to the demonstration dataset.
- The POC should remain small enough to demonstrate the core decision-support behavior quickly.

## Business

- The POC should demonstrate practical value to a facility leader rather than AI terminology or technical novelty.
- Recommendations must support human decision-making rather than replace it.

## Regulatory / Security

- Use synthetic/de-identified data only.
- Do not use real PHI.
- Do not represent the POC as a validated clinical decision system.

## Operational

- The primary experience must be understandable without technical AI knowledge.
- The CIO-facing technical view must explain how the system works without requiring software-development knowledge.

## Budget / Time

- This is a focused proof of concept and should prioritize demonstrating the core workflow over production completeness.

# 13. Dependencies

| Dependency | Type | Required For | Risk |
|---|---|---|---|
| Mock Domo MCP | Internal / POC | Data retrieval | Low |
| Synthetic facility dataset | Internal / POC | Data analysis | Medium |
| AI analysis capability | External / Technical | Interpretation and recommendations | Medium |
| Numerical analysis capability | Internal / Technical | Accurate calculations and trends | Low |

---

# 14. Risks

## Risk Levels

```text
LOW
MEDIUM
HIGH
```

### RISK-001

**Description:** Mock data structure may differ from the eventual Domo MCP interface.

**Impact:** Future integration could require changes to data handling.

**Likelihood:** Medium

**Mitigation:** Keep the agent/data boundary clear and avoid coupling the user-facing experience to the mock source structure.

**Verification:** Confirm that the agent consumes data through the defined interface rather than directly depending on mock implementation details.

### RISK-002

**Description:** The language model may produce an interpretation or recommendation that is not sufficiently supported by the data.

**Impact:** A human could receive misleading decision support.

**Likelihood:** Medium

**Mitigation:** Require evidence-grounded output, explicit uncertainty, and human review.

**Verification:** Test recommendations against known datasets and intentionally changed inputs.

### RISK-003

**Description:** Insufficient historical data may prevent meaningful trend analysis.

**Impact:** The system may overreact to a single measurement.

**Likelihood:** Medium

**Mitigation:** Include historical synthetic data and require the system to state when trend context is unavailable.

**Verification:** Test both sufficient-history and insufficient-history scenarios.

### RISK-004

**Description:** POC users may interpret recommendations as clinical decisions.

**Impact:** Incorrect expectations about system authority.

**Likelihood:** Low

**Mitigation:** Clearly identify the system as decision support and maintain human decision authority.

**Verification:** Review user-facing output and technical documentation for appropriate boundaries.

# 15. Phases

Each phase must have a clear purpose and explicit exit condition.

## Phase 1 — Facility Data Foundation

**Objective**

Create the synthetic facility data and mock Domo MCP interface needed to demonstrate the operational decision workflow.

**Risk**

LOW

**Stories**

- 1.1 — Create Facility Data Model
- 1.2 — Create Mock Domo MCP

**Exit Conditions**

- Representative facility data is available across the defined operational areas.
- Historical data is available for meaningful trend scenarios.
- The agent can retrieve the required data through the mock interface.

## Phase 2 — Operational Decision Analysis

**Objective**

Demonstrate that the system can accurately calculate, interpret, prioritize, and explain facility information without hard-coded recommendations.

**Risk**

MEDIUM

**Stories**

- 2.1 — Analyze Facility State
- 2.2 — Explain Metrics and Trends
- 2.3 — Identify Positive Performance
- 2.4 — Identify Areas Requiring Attention
- 2.5 — Generate Data-Grounded Recommendations

**Exit Conditions**

- Numerical calculations are accurate.
- Findings change when relevant input data changes.
- Recommendations are generated from available evidence.
- Unsupported conclusions are identified as uncertain or omitted.

## Phase 3 — Human-Facing Experience

**Objective**

Present the agent's analysis in a simple interface designed for a facility leader.

**Risk**

LOW

**Stories**

- 3.1 — Facility Brief
- 3.2 — What It Means
- 3.3 — Recommendations
- 3.4 — Technical / How It Works

**Exit Conditions**

- A human can understand the facility state without technical knowledge.
- The interface clearly distinguishes positive performance, areas to watch, and action-needed items.
- The CIO-facing view explains the system and its limitations.

## Phase 4 — Evaluation

**Objective**

Demonstrate that the POC behaves as a data-driven decision-support system rather than a hard-coded demonstration.

**Risk**

MEDIUM

**Stories**

- 4.1 — Recommendation Evaluation
- 4.2 — Failure and Boundary Testing

**Exit Conditions**

- Known test scenarios produce expected categories of behavior.
- Changing source data can change findings and recommendations.
- Missing, inconsistent, or unavailable data produces appropriate limitations.
- No production PHI or credentials are required.
# 16. Stories

Each story should be small enough to implement and verify independently.

## Story 1.1 — Create Facility Data Model

**Objective**

Create representative synthetic facility data covering the operational areas required by the POC.

**Risk**

LOW

**Dependencies**

- None

**Scope**

Synthetic datasets for census, occupancy, admissions, discharges, LOS, therapy, staffing, payer/authorization, hospitality, hospital transfers, and historical values.

### Acceptance Criteria

#### AC-1.1.1

Representative data exists for each required operational area.

**Verification**

Inspect the synthetic dataset and confirm required fields and representative records exist.

#### AC-1.1.2

Historical values exist for metrics where change or trend analysis is expected.

**Verification**

Confirm multiple dated observations exist for selected metrics.

### Rejection / Boundary Conditions

- Real patient PHI must not be included.
- Missing historical data must be represented as missing rather than fabricated.

### Failure Behavior

If required synthetic data cannot be loaded, the application reports the affected dataset as unavailable.

## Story 1.2 — Create Mock Domo MCP

**Objective**

Provide an MCP-style interface through which the agent can retrieve synthetic facility data.

**Risk**

LOW

**Dependencies**

- Story 1.1

**Scope**

Mock data retrieval interface representing the future Domo data boundary.

### Acceptance Criteria

#### AC-1.2.1

The agent can retrieve the required facility datasets through the mock interface.

**Verification**

Run the agent against the mock interface and verify successful retrieval.

#### AC-1.2.2

The user-facing application does not claim that the mock interface is a live Domo connection.

**Verification**

Review the application and technical view.

### Rejection / Boundary Conditions

- No real Domo credentials are required.
- The POC must not imply production Domo connectivity.

### Failure Behavior

Unavailable mock data must result in an explicit data-unavailable state.

## Story 2.1 — Analyze Facility State

**Objective**

Create a current picture of facility operations from available data.

**Risk**

MEDIUM

**Dependencies**

- Story 1.2

**Scope**

Current-state metrics and cross-domain facility information.

### Acceptance Criteria

#### AC-2.1.1

The system produces a human-readable facility summary from the current data.

**Verification**

Run the agent against the test dataset and inspect the resulting summary.

#### AC-2.1.2

The summary does not introduce numbers that are not present in the source data or derived from documented calculations.

**Verification**

Compare displayed values against source data and calculation results.

### Rejection / Boundary Conditions

- Unsupported facts must not be presented as facts.
- Missing data must not be silently substituted.

### Failure Behavior

The system identifies unavailable information and limits the analysis accordingly.

## Story 2.2 — Explain Metrics and Trends

**Objective**

Explain meaningful facility numbers and changes in plain language.

**Risk**

MEDIUM

**Dependencies**

- Story 2.1

**Scope**

Metric meaning, comparisons, trends, and significance.

### Acceptance Criteria

#### AC-2.2.1

The system explains important metrics in terms understandable to a non-technical human.

**Verification**

Review output for representative metrics.

#### AC-2.2.2

The system can explain a meaningful change over time when historical data is available.

**Verification**

Provide a dataset with a known trend and verify that the output recognizes the change.

### Rejection / Boundary Conditions

- The system must not claim a cause that is not supported by the data.
- The system must communicate when context is insufficient.

### Failure Behavior

Insufficient context results in an explicit limitation.

## Story 2.3 — Identify Positive Performance

**Objective**

Identify areas where facility performance is stable or improving when supported by data.

**Risk**

MEDIUM

**Dependencies**

- Story 2.2

**Scope**

Positive findings across operational areas.

### Acceptance Criteria

#### AC-2.3.1

The system identifies supported positive trends or conditions.

**Verification**

Use a dataset containing known improving metrics and compare the output with expected findings.

### Rejection / Boundary Conditions

- Positive findings must not be generated solely to make the demonstration appear successful.

### Failure Behavior

If positive performance cannot be established, the system does not manufacture it.

## Story 2.4 — Identify Areas Requiring Attention

**Objective**

Identify and prioritize meaningful operational conditions requiring human review.

**Risk**

MEDIUM

**Dependencies**

- Story 2.2

**Scope**

Cross-domain observations, trends, and prioritization.

### Acceptance Criteria

#### AC-2.4.1

The system identifies supported areas requiring attention.

**Verification**

Run known test scenarios containing meaningful changes or operational concerns.

#### AC-2.4.2

The system considers relationships between relevant datasets when determining significance.

**Verification**

Provide a scenario where multiple related data points together create a stronger concern than any individual value.

### Rejection / Boundary Conditions

- The system must not state that a problem exists when the evidence does not support that conclusion.
- The system must not use fixed scenario-specific rules as the sole source of findings.

### Failure Behavior

The system reports insufficient evidence when it cannot support a conclusion.

## Story 2.5 — Generate Data-Grounded Recommendations

**Objective**

Provide useful suggested next steps based on identified areas requiring attention.

**Risk**

MEDIUM

**Dependencies**

- Story 2.4

**Scope**

Prioritized recommendations, rationale, and supporting evidence.

### Acceptance Criteria

#### AC-2.5.1

Each recommendation identifies why it was suggested.

**Verification**

Inspect recommendation output for supporting evidence and rationale.

#### AC-2.5.2

Changing relevant source data can change the resulting recommendation.

**Verification**

Run the same scenario with materially changed inputs and compare outputs.

#### AC-2.5.3

Recommendations are clearly presented as suggestions for human review.

**Verification**

Review user-facing output.

### Rejection / Boundary Conditions

- Recommendations must not be hard-coded to the demonstration dataset.
- The system must not claim an action was performed.

### Failure Behavior

If evidence is insufficient, the system reports that a recommendation cannot be reliably generated.

## Story 3.1 — Facility Brief

**Objective**

Provide a concise human-facing summary of the facility.

**Risk**

LOW

**Dependencies**

- Story 2.3
- Story 2.4

**Scope**

Current status, positive performance, watch items, and action-needed items.

### Acceptance Criteria

#### AC-3.1.1

A human can understand the facility's current state without technical AI knowledge.

**Verification**

Review the interface using representative data.

### Rejection / Boundary Conditions

- Do not expose raw technical implementation details as the primary experience.

### Failure Behavior

If analysis is incomplete, the brief identifies the limitation.

## Story 3.2 — What It Means

**Objective**

Explain important numbers and findings in plain language.

**Risk**

LOW

**Dependencies**

- Story 2.2

**Scope**

Current value, comparison/trend, meaning, and why it matters.

### Acceptance Criteria

#### AC-3.2.1

Important metrics are accompanied by understandable context.

**Verification**

Review representative metric explanations.

### Rejection / Boundary Conditions

- Avoid unsupported causal claims.

### Failure Behavior

Uninterpretable metrics are clearly identified.

## Story 3.3 — Recommendations

**Objective**

Present prioritized suggested actions in a form useful to a human decision-maker.

**Risk**

LOW

**Dependencies**

- Story 2.5

**Scope**

Priority, finding, why it matters, suggested next step, and evidence.

### Acceptance Criteria

#### AC-3.3.1

Recommendations are prioritized and understandable.

**Verification**

Review output from scenarios with multiple simultaneous issues.

#### AC-3.3.2

Recommendations include supporting information.

**Verification**

Trace recommendations back to source metrics/calculations.

### Rejection / Boundary Conditions

- Recommendations must not be represented as completed actions.

### Failure Behavior

Unsupported recommendations are omitted or presented with an explicit limitation.

## Story 3.4 — Technical / How It Works

**Objective**

Give the CIO a human-readable explanation of the POC's data flow and reasoning.

**Risk**

LOW

**Dependencies**

- Story 1.2
- Story 2.1
- Story 2.5

**Scope**

Data source, data flow, numerical analysis, AI reasoning, evidence, limitations, and future Domo integration boundary.

### Acceptance Criteria

#### AC-3.4.1

The technical view explains which information comes from the data source.

**Verification**

Compare the technical view with the POC data flow.

#### AC-3.4.2

The technical view explains the difference between numerical analysis and AI-generated interpretation.

**Verification**

Review the page for clear separation of responsibilities.

#### AC-3.4.3

The technical view clearly identifies the Domo connection as simulated.

**Verification**

Review displayed integration description.

### Rejection / Boundary Conditions

- Do not imply production readiness or live Domo access.

### Failure Behavior

Technical limitations must be stated explicitly.

## Story 4.1 — Recommendation Evaluation

**Objective**

Verify that recommendations are data-driven rather than hard-coded.

**Risk**

MEDIUM

**Dependencies**

- Story 2.5

**Scope**

Controlled test scenarios and changed-input tests.

### Acceptance Criteria

#### AC-4.1.1

Known input changes produce corresponding changes in analysis when the changed data is materially relevant.

**Verification**

Run paired datasets and compare results.

#### AC-4.1.2

The system does not repeatedly produce the same predetermined recommendation when the supporting data is removed or changed.

**Verification**

Remove or alter the evidence behind a known recommendation and verify the recommendation changes or is withdrawn.

### Rejection / Boundary Conditions

- A fixed expected sentence is not required; the requirement is behavior grounded in the changed data.

### Failure Behavior

Failed evaluation is recorded and the POC is not considered complete.

## Story 4.2 — Failure and Boundary Testing

**Objective**

Verify appropriate behavior when information is missing, unavailable, or insufficient.

**Risk**

MEDIUM

**Dependencies**

- Story 2.1
- Story 2.5

**Scope**

Missing data, calculation failures, AI unavailable, insufficient evidence, and invalid data.

### Acceptance Criteria

#### AC-4.2.1

The system identifies missing or unavailable data rather than inventing a value.

**Verification**

Remove required input and inspect the result.

#### AC-4.2.2

The system does not produce an unsupported recommendation when evidence is insufficient.

**Verification**

Run an intentionally ambiguous scenario.

### Rejection / Boundary Conditions

- No fabricated values.
- No fabricated clinical facts.

### Failure Behavior

The appropriate explicit failure state is displayed.
# 17. Non-Functional Requirements

## Maintainability

The separation between data retrieval, numerical analysis, AI interpretation, and presentation should be understandable and changeable without rewriting the entire POC.

## Observability

The POC should provide enough visibility to understand what data was retrieved, what calculations were performed, and what information supported an important recommendation.

## Accessibility

The primary user experience should use plain language and avoid requiring knowledge of AI, MCP, Domo, or software development.

## Scalability

Production-scale scalability is out of scope. The POC should avoid unnecessary coupling that would prevent a future expansion to additional facilities or a real Domo data source.

## Reliability

The system must prefer an explicit limitation or unavailable state over an invented result.

# 18. Domain Standards

List standards that apply to this project.

```text
MCP Builder Standard
Applicable AI / Agent Harness Standards
Applicable Data Governance Standard
Applicable Security / Privacy Standards
```

Examples:

- MCP Builder Standard
- Organization security standard
- API standard
- Data governance standard

The standards themselves belong outside this specification.

---

# 19. Tooling / Repository Profile

Do not put model or provider assignments here.

Reference the project tooling profile:

```text
profiles/tooling-profile.yaml
```

The tooling profile defines commands such as:

- test
- lint
- format check
- type check
- security scan
- secret scan
- dependency scan

This specification defines **what must be verified**, not which tool performs the verification.

---

# 20. Definition of Done

The project is complete only when:

- all required stories are verified;
- the mock Domo MCP provides the required synthetic facility information;
- the application produces a human-readable facility brief;
- the application explains what important numbers and changes mean;
- the application identifies what is going well when supported by data;
- the application identifies areas requiring attention when supported by data;
- recommendations are generated from available information rather than hard-coded for the demonstration scenario;
- numerical results are accurate and traceable;
- changing relevant source data can change findings and recommendations;
- missing or insufficient data produces appropriate limitations;
- recommendations are clearly presented as suggestions requiring human judgment;
- the CIO-facing technical view explains the data flow, analysis, AI reasoning, evidence, and limitations;
- no real PHI or production credentials are required;
- required documentation is complete;
- required regression and evaluation checks pass;
- no unresolved blocking findings remain;
- finalization passes.

# 21. Acceptance Matrix

| Requirement | Story | Acceptance Criterion | Evidence Required | Status |
|---|---|---|---|---|
| FR-001 | 2.1 | Facility state can be summarized from available data | Agent run output | DRAFT |
| FR-002 | 2.2 / 3.2 | Important metrics are explained in plain language | UI review / test output | DRAFT |
| FR-003 | 2.3 | Supported positive performance is identified | Evaluation dataset | DRAFT |
| FR-004 | 2.4 | Meaningful areas requiring attention are identified | Evaluation dataset | DRAFT |
| FR-005 | 2.5 / 3.3 | Recommendations are data-grounded and actionable as suggestions | Recommendation evaluation | DRAFT |
| FR-006 | 2.1 / 4.2 | Numerical outputs are accurate and traceable | Calculation tests | DRAFT |
| FR-007 | 2.5 / 3.3 | Findings identify supporting information | UI/output inspection | DRAFT |
| FR-008 | 4.1 | Changing source data can change findings/recommendations | Paired dataset evaluation | DRAFT |
| FR-009 | 3.3 | Recommendations remain human decisions | UI review | DRAFT |
| FR-010 | 3.4 | CIO can understand data flow, reasoning, and limitations | Technical tab review | DRAFT |
| INV-001 | 4.1 | No hard-coded scenario-specific intelligence | Changed-input evaluation | DRAFT |
| INV-002 | 4.1 / 4.2 | Numbers trace to source/calculation | Calculation evidence | DRAFT |
| INV-003 | 3.2 / 3.3 | Observation, interpretation, and recommendation are distinguishable | UI review | DRAFT |
| INV-004 | 4.2 | Missing facts are not invented | Failure test | DRAFT |
| INV-005 | 4.2 | Uncertainty is communicated | Boundary test | DRAFT |
| INV-006 | 3.3 | No action is represented as executed | UI review | DRAFT |
| INV-007 | 2.2 | Historical data is used when available | Trend test | DRAFT |
| INV-008 | 1.1 | POC uses synthetic data | Dataset inspection | DRAFT |

This matrix should make it possible to trace:

```text
Requirement
    ↓
Story
    ↓
Acceptance Criterion
    ↓
Execution Evidence
    ↓
Verification
```

# 22. Approval

The specification is not executable until explicitly approved.

```text
Status: APPROVED

Version:
Approved By:
Approved At:
Approval Notes:
```

---

# 23. Specification Amendment

Once approved, this specification is locked.

A defect discovered during implementation does **not** permit an agent to silently edit this file.

The required process is:

```text
Implementation discovers contradiction
        ↓
Evaluator records SPEC_DEFECT
        ↓
Story becomes BLOCKED
        ↓
Human reviews specification
        ↓
APPROVE / REJECT amendment
        ↓
If approved:
    increment version
    record change
    reconcile build-plan.md
    determine affected stories
        ↓
Affected work becomes eligible
```

## Amendment Record

```text
Amendment ID:
Previous Version:
New Version:
Date:
Requested Change:
Reason:
Affected Requirements:
Affected Phases:
Affected Stories:
Approved By:
Approval Date:
```

---

# 24. Final Notes

This POC is intended to demonstrate the concept of an operational decision agent for an Ignite medical facility.

The central user experience is:

```text
What is happening?
        ↓
What changed?
        ↓
What does it mean?
        ↓
What's going well?
        ↓
What needs attention?
        ↓
What should we consider doing?
```

The POC should demonstrate useful decision support without pretending that the system has live Domo access, production clinical data, or autonomous decision-making authority.

The specification intentionally does not require a specific LLM, provider, agent framework, or implementation technique. The required outcome is data-grounded analysis that a human can understand and evaluate.

---

## Specification Principle

**The specification describes the required outcome and constraints.**

It should not prescribe:

- a specific AI model;
- a specific AI provider;
- a specific IDE;
- a specific agent runtime;
- a particular prompt;
- an implementation technique unless that technique itself is a requirement;
- internal code structure unless required by an explicit contract.

Those concerns belong in the appropriate Atlas role, directive, tooling profile, domain standard, or implementation artifact.
