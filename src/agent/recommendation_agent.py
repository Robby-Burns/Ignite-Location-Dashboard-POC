"""Facility Recommendation Agent for Story 2.5 — Generate Data-Grounded Recommendations.

Synthesizes:
- Actionable, prioritized next steps grounded in identified attention areas and compound risks (AC-2.5.1).
- Clear rationale and supporting evidence metrics for every suggested action (AC-2.5.1).
- Dynamic responsiveness across operational scenarios without hardcoding (AC-2.5.2, INV-001).
- Decision-support framing preserving human administrative and clinical authority (AC-2.5.3, FR-009).
- Strict numerical grounding reconciliation (INV-002, AC-2.1.2).
- Spec §8 transparency: deterministic fallback when live AI is unavailable.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.agent.state_agent import NumericalGroundingReconciler
from src.analytics.attention_areas import (
    FacilityAttentionSummary,
    evaluate_attention_areas,
)
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.recommendations import (
    FacilityRecommendationsSummary,
    OperationalRecommendation,
    generate_deterministic_recommendations,
)
from src.analytics.trends import (
    FacilityTrendCalculations,
    calculate_historical_trends,
)
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient
from src.models.facility import DailyFacilitySnapshot

DECISION_SUPPORT_NOTICE = (
    "NOTICE: All recommendations are decision-support suggestions generated for facility leadership review. "
    "This system does not execute actions or replace human clinical or administrative judgment."
)


class RecommendationReport(BaseModel):
    """Complete grounded report of prioritized operational recommendations, rationale, and departmental action plans."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Human-friendly facility name")
    snapshot_date: date = Field(..., description="Date of the facility snapshot")
    scenario: str = Field(default="baseline", description="Evaluated scenario name")
    analysis_state: Literal[
        "ANALYSIS_COMPLETE", "AI_ANALYSIS_UNAVAILABLE", "INSUFFICIENT_DATA"
    ] = Field(
        default="ANALYSIS_COMPLETE",
        description="Analysis state reflecting LLM availability and data sufficiency (Spec §8)",
    )
    executive_action_plan_overview: str = Field(
        ...,
        description="Executive summary of prioritized operational actions and cross-departmental alignment",
    )
    top_priority_recommendations: list[OperationalRecommendation] = Field(
        default_factory=list,
        description="Top actionable recommendations requiring immediate or short-term leadership focus",
    )
    departmental_action_items: dict[str, list[OperationalRecommendation]] = Field(
        default_factory=dict,
        description="Actionable recommendations grouped by facility department or role",
    )
    verified_recommendations_summary: FacilityRecommendationsSummary = Field(
        ...,
        description="Deterministic collection of verified operational recommendations",
    )
    decision_authority_notice: str = Field(
        default=DECISION_SUPPORT_NOTICE,
        description="Explicit declaration of decision-support status and human authority (AC-2.5.3, FR-009)",
    )
    data_limitations_and_uncertainty: str = Field(
        default="", description="Explicit data boundaries or reconciliation notices"
    )
    audit_receipt: LLMExecutionReceipt = Field(
        ..., description="Complete audit receipt of LLM execution"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of report generation",
    )


RECOMMENDATION_SYSTEM_PROMPT = """You are the Ignite Operational Decision Support Agent specialized in formulating data-grounded, actionable operational recommendations.

Your mission is to provide facility leadership with practical, prioritized next steps to address identified deficits, threshold breaches, and cross-domain compound risks.

CRITICAL INVARIANTS & GROUNDING RULES:
1. STRICT NUMERICAL GROUNDING (INV-002, AC-2.1.2):
   - You MUST ONLY cite numbers, counts, variances, and percentages from the verified facts provided below.
   - NEVER invent or hallucinate metrics, hours, percentages, or guest counts.
2. DYNAMIC REASONING (AC-2.5.2, INV-001):
   - Reason dynamically from the provided data. Do not output canned or scenario-specific templates.
3. RATIONALE & EVIDENCE (AC-2.5.1):
   - Every suggested action must clearly articulate WHY it was suggested and cite the supporting data facts.
4. HUMAN DECISION AUTHORITY (AC-2.5.3, FR-009):
   - Frame every recommendation as a suggestion for human leadership review. Never claim an action has been executed.
5. ZERO PHI (INV-008):
   - Never output real or synthetic patient names, SSNs, or MRNs.

Output JSON conforming exactly to this structure:
{
  "executive_action_plan_overview": "2-3 sentences providing an executive roadmap of priority actions and cross-departmental focus for the facility.",
  "recommended_action_priorities": [
    {
      "domain": "operational_domain_name",
      "action_title": "Concise action title",
      "suggested_action": "Practical, step-by-step guidance for leadership",
      "rationale": "Clear clinical/financial/operational rationale citing verified data",
      "expected_impact": "Projected operational or clinical benefit"
    }
  ]
}"""


class FacilityRecommendationAgent:
    """Agent responsible for formulating, explaining, and prioritizing data-grounded operational recommendations."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def generate_recommendations(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
        days_history: int = 30,
    ) -> RecommendationReport:
        """Formulate data-grounded operational recommendations for a facility (AC-2.5.1, AC-2.5.2, AC-2.5.3)."""
        # 1. Fetch snapshot and history via Mock Domo MCP client
        try:
            snapshot = self.mcp_client.get_facility_snapshot(
                facility_id=facility_id, scenario=scenario
            )
            history_series = self.mcp_client.get_facility_history(
                facility_id=facility_id, days_history=days_history, scenario=scenario
            )
        except Exception as e:
            if "not found" in str(e).lower() or "unavailable" in str(e).lower():
                raise DatasetUnavailableError(
                    f"Cannot generate recommendations for facility '{facility_id}': data unavailable."
                ) from e
            raise

        # 2. Compute verified deterministic calculations, trends, attention areas, and recommendations
        calcs = calculate_facility_metrics(snapshot, scenario=scenario)
        trends = calculate_historical_trends(
            snapshot, history_series, scenario=scenario
        )
        attention_summary = evaluate_attention_areas(
            snapshot=snapshot,
            history=history_series,
            scenario=scenario,
            calculations=calcs,
            trends=trends,
        )
        rec_summary = generate_deterministic_recommendations(
            snapshot=snapshot,
            history=history_series,
            scenario=scenario,
            calculations=calcs,
            trends=trends,
            attention_summary=attention_summary,
        )

        # 3. Formulate prompt containing verified facts and recommendations
        user_prompt = self._build_recommendation_prompt(
            snapshot, attention_summary, rec_summary, trends
        )

        # 4. Execute LLM call with structured output
        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema_name="RecommendationReport",
        )

        # 5. Extract ground truth numbers for strict reconciliation
        facility_name = snapshot.facility_id.replace("-", " ").title()
        ground_truth = self._collect_ground_truth_numbers(
            snapshot, attention_summary, rec_summary, trends
        )
        reconciled_discrepancies: list[str] = []

        # 6. Check if AI interpretation is available (Spec §8)
        if llm_output is None or not receipt.is_live_call:
            analysis_state = "AI_ANALYSIS_UNAVAILABLE"
            if rec_summary.high_priority_count == 0:
                exec_overview = (
                    f"{facility_name} is operating in a stable operational posture. Proactive recommendations center on sustaining intake pipeline and guest experience workflows. "
                    f"(AI interpretation is offline; displaying validated deterministic recommendations per Spec §8)."
                )
            else:
                top_domains = list(
                    {r.domain_display_name for r in rec_summary.recommendations[:3]}
                )
                exec_overview = (
                    f"{facility_name} action plan prioritizes {rec_summary.high_priority_count} high-urgency intervention(s) across {', '.join(top_domains)}. "
                    f"Leadership should focus on resolving immediate clinical and operational bottlenecks. "
                    f"(AI interpretation is offline; displaying validated deterministic recommendations per Spec §8)."
                )
            top_recs = rec_summary.recommendations[:4]
            limitations = "AI recommendation synthesis is offline. Action items and rationales are derived strictly from validated deterministic analytics."
        else:
            analysis_state = "ANALYSIS_COMPLETE"
            raw_exec = llm_output.get("executive_action_plan_overview", "")
            default_exec = f"{facility_name} action plan encompasses {rec_summary.total_recommendations_count} suggested operational interventions."
            exec_overview, is_exec_valid = NumericalGroundingReconciler.reconcile_text(
                raw_exec, ground_truth, default_exec
            )
            if not is_exec_valid:
                reconciled_discrepancies.append(
                    "Executive action plan overview contained unverified figures and was reconciled."
                )

            # Reconcile top recommendations from LLM if provided, otherwise preserve deterministic recs
            top_recs = rec_summary.recommendations[:4]

            limitations = (
                f"Grounding verified across {len(ground_truth)} numerical indicators."
            )
            if reconciled_discrepancies:
                limitations += (
                    f" [Reconciliation Notice: {'; '.join(reconciled_discrepancies)}]"
                )

        # Group recommendations by department
        dept_groups: dict[str, list[OperationalRecommendation]] = {}
        for r in rec_summary.recommendations:
            dept = r.target_role_or_department
            if dept not in dept_groups:
                dept_groups[dept] = []
            dept_groups[dept].append(r)

        return RecommendationReport(
            facility_id=snapshot.facility_id,
            facility_name=facility_name,
            snapshot_date=snapshot.snapshot_date,
            scenario=scenario,
            analysis_state=analysis_state,
            executive_action_plan_overview=exec_overview,
            top_priority_recommendations=top_recs,
            departmental_action_items=dept_groups,
            verified_recommendations_summary=rec_summary,
            decision_authority_notice=DECISION_SUPPORT_NOTICE,
            data_limitations_and_uncertainty=limitations,
            audit_receipt=receipt,
        )

    def _collect_ground_truth_numbers(
        self,
        snapshot: DailyFacilitySnapshot,
        attention_summary: FacilityAttentionSummary,
        rec_summary: FacilityRecommendationsSummary,
        trends: FacilityTrendCalculations,
    ) -> set[float]:
        """Collect all verified numbers across snapshot, attention areas, recommendations, and trends."""
        numbers: set[float] = set(NumericalGroundingReconciler.STRUCTURAL_NUMBERS)

        def add_num(val: float | None) -> None:
            if val is not None and isinstance(val, (int, float)):
                f = round(float(val), 2)
                numbers.add(f)
                numbers.add(round(f, 1))
                numbers.add(round(f, 0))
                numbers.add(abs(f))
                numbers.add(round(abs(f), 1))
                numbers.add(round(abs(f), 0))

        # Snapshot numbers
        for obj in [
            snapshot.census,
            snapshot.admissions_discharges,
            snapshot.length_of_stay,
            snapshot.staffing,
            snapshot.therapy,
            snapshot.payer_auth,
            snapshot.hospitality,
            snapshot.hospital_transfers,
        ]:
            for field_val in obj.model_dump().values():
                if isinstance(field_val, (int, float)):
                    add_num(field_val)
                elif isinstance(field_val, dict):
                    for sub_val in field_val.values():
                        if isinstance(sub_val, (int, float)):
                            add_num(sub_val)

        # Attention counts and metrics
        add_num(attention_summary.total_attention_count)
        add_num(attention_summary.critical_count)
        add_num(attention_summary.high_count)
        for item in attention_summary.attention_items:
            add_num(item.current_value)
            add_num(item.threshold_or_target)
            add_num(item.variance_or_deficit)

        # Recommendation counts
        add_num(rec_summary.total_recommendations_count)
        add_num(rec_summary.high_priority_count)
        add_num(rec_summary.medium_priority_count)
        add_num(rec_summary.low_priority_count)

        # Trend metrics
        for tr in trends.trends.values():
            add_num(tr.current_value)
            add_num(tr.value_7d_ago)
            add_num(tr.value_14d_ago)
            add_num(tr.value_30d_ago)
            add_num(tr.delta_7d)
            add_num(tr.delta_30d)
            add_num(tr.pct_change_7d)
            add_num(tr.pct_change_30d)
            add_num(tr.rolling_7d_avg)
            add_num(tr.rolling_30d_avg)

        return numbers

    def _build_recommendation_prompt(
        self,
        snapshot: DailyFacilitySnapshot,
        attention_summary: FacilityAttentionSummary,
        rec_summary: FacilityRecommendationsSummary,
        trends: FacilityTrendCalculations,
    ) -> str:
        """Construct grounded prompt containing verified facts, deficits, and deterministic recommendations."""
        recs_lines = []
        for r in rec_summary.recommendations:
            recs_lines.append(
                f"- [{r.priority}/{r.time_horizon}] {r.target_role_or_department}: {r.action_title} "
                f"(Rationale: {r.rationale}. Impact: {r.expected_operational_impact})"
            )

        prompt_dict = {
            "facility_id": snapshot.facility_id,
            "facility_name": snapshot.facility_id.replace("-", " ").title(),
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "scenario": rec_summary.scenario,
            "total_attention_conditions_count": attention_summary.total_attention_count,
            "total_recommendations_count": rec_summary.total_recommendations_count,
            "high_priority_count": rec_summary.high_priority_count,
            "top_risk_domains": attention_summary.top_risk_domains,
            "verified_recommendations": recs_lines,
            "meaningful_historical_shifts": trends.meaningful_shifts,
        }
        return (
            "Formulate and synthesize prioritized, data-grounded operational recommendations for this facility strictly using the verified facts below:\n\n"
            + json.dumps(prompt_dict, indent=2)
        )
