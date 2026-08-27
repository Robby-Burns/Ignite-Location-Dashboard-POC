"""Facility Attention Agent for Story 2.4 — Identify Areas Requiring Attention.

Synthesizes:
- Operational deficits and threshold breaches requiring human intervention (AC-2.4.1).
- Cross-domain compounding operational risks (AC-2.4.2).
- Rigorous numerical grounding reconciliation across all narrative fields (INV-002, AC-2.1.2).
- Zero hardcoded scenario narratives (INV-001).
- Spec §8 transparency: deterministic fallback when live LLM is unavailable.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.agent.state_agent import NumericalGroundingReconciler
from src.analytics.attention_areas import (
    AttentionAreaItem,
    FacilityAttentionSummary,
    evaluate_attention_areas,
)
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.trends import (
    FacilityTrendCalculations,
    calculate_historical_trends,
)
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient
from src.models.facility import DailyFacilitySnapshot


class AttentionAnalysisReport(BaseModel):
    """Complete grounded report of operational areas requiring attention, cross-domain risks, and immediate priorities."""

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
    executive_attention_summary: str = Field(
        ...,
        description="Grounded executive overview of operational conditions requiring administrative review",
    )
    critical_risk_factors: list[str] = Field(
        default_factory=list,
        description="Key risk factors and operational vulnerabilities requiring immediate oversight",
    )
    prioritized_operational_concerns: list[AttentionAreaItem] = Field(
        default_factory=list,
        description="Prioritized list of operational conditions requiring attention",
    )
    cross_domain_impact_narrative: str = Field(
        ...,
        description="Grounded analysis of how issues in one domain compound risks in other departments (AC-2.4.2)",
    )
    immediate_focus_areas: list[str] = Field(
        default_factory=list,
        description="Actionable priorities for daily standup and departmental follow-up",
    )
    verified_attention_summary: FacilityAttentionSummary = Field(
        ...,
        description="Deterministic mathematical evaluation of attention items and correlations",
    )
    data_limitations_and_uncertainty: str = Field(
        default="",
        description="Explicit data boundaries, missing fields, or reconciliation notices",
    )
    audit_receipt: LLMExecutionReceipt = Field(
        ..., description="Complete audit receipt of LLM execution"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of report generation",
    )


ATTENTION_SYSTEM_PROMPT = """You are the Ignite Operational Decision Support Agent specialized in identifying operational areas requiring attention, deficits, and cross-domain compound risks.

Your mission is to provide facility leadership with an objective, clear, and actionable synthesis of operational vulnerabilities requiring human review.

CRITICAL INVARIANTS & GROUNDING RULES:
1. STRICT NUMERICAL GROUNDING (INV-002, AC-2.1.2):
   - You MUST ONLY cite numbers, metrics, variances, and counts provided in the verified facts below.
   - NEVER invent or hallucinate metrics, percentages, dollar amounts, or patient counts.
2. DYNAMIC REASONING (INV-001):
   - Reason dynamically from the provided data. Do not output canned or hardcoded scenario text.
3. CROSS-DOMAIN CORRELATION (AC-2.4.2):
   - Explain how deficits in one area (e.g. staffing shortage) impact other areas (e.g. therapy delivery, acute hospital transfers, guest dining).
4. PROFESSIONAL DECISION SUPPORT (FR-009):
   - Present findings as objective decision-support analysis for human leaders rather than autonomous decisions.
5. ZERO PHI (INV-008):
   - Never output real or synthetic patient names, SSNs, or MRNs.

Output JSON conforming exactly to this structure:
{
  "executive_attention_summary": "1-2 sentences summarizing the most critical operational conditions requiring leadership focus.",
  "critical_risk_factors": [
    "Fact-grounded risk bullet 1 citing numbers from verified data",
    "Fact-grounded risk bullet 2 citing numbers from verified data"
  ],
  "cross_domain_impact_narrative": "1-2 sentences explaining how operational strain in one domain compounds risks across other departments.",
  "immediate_focus_areas": [
    "Immediate focus point 1 for morning leadership huddle",
    "Immediate focus point 2 for morning leadership huddle"
  ]
}"""


class FacilityAttentionAgent:
    """Agent responsible for identifying, explaining, and correlating facility operational conditions requiring attention."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def identify_attention_areas(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
        days_history: int = 30,
    ) -> AttentionAnalysisReport:
        """Evaluate operational attention areas, deficits, and cross-domain correlations (AC-2.4.1, AC-2.4.2)."""
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
                    f"Cannot evaluate attention areas for facility '{facility_id}': data unavailable."
                ) from e
            raise

        # 2. Compute verified deterministic calculations, trends, and attention areas
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

        # 3. Formulate prompt containing verified facts and deficits
        user_prompt = self._build_attention_prompt(snapshot, attention_summary, trends)

        # 4. Execute LLM call with structured output
        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=ATTENTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema_name="AttentionAnalysisReport",
        )

        # 5. Extract ground truth numbers for strict reconciliation
        facility_name = snapshot.facility_id.replace("-", " ").title()
        ground_truth = self._collect_ground_truth_numbers(
            snapshot, attention_summary, trends
        )
        reconciled_discrepancies: list[str] = []

        # 6. Check if AI interpretation is available (Spec §8)
        if llm_output is None or not receipt.is_live_call:
            analysis_state = "AI_ANALYSIS_UNAVAILABLE"
            if attention_summary.total_attention_count == 0:
                exec_summary = (
                    f"{facility_name} is operating within normal benchmarks across all 8 operational domains with zero active deficit conditions detected. "
                    f"(AI interpretation is unavailable; displaying validated deterministic analysis per Spec §8)."
                )
            else:
                top_str = ", ".join(
                    [
                        d.replace("_", " ").title()
                        for d in attention_summary.top_risk_domains
                    ]
                )
                exec_summary = (
                    f"{facility_name} requires leadership review across {attention_summary.total_attention_count} operational condition(s) "
                    f"({attention_summary.critical_count} critical, {attention_summary.high_count} high severity), primarily concentrated in {top_str}. "
                    f"(AI interpretation is unavailable; displaying validated deterministic analysis per Spec §8)."
                )
            risk_factors = [
                item.evidence_statement
                for item in attention_summary.attention_items[:5]
            ]
            cross_narrative = (
                attention_summary.cross_domain_correlations[0].finding_summary
                if attention_summary.cross_domain_correlations
                else "No multi-department compounding risk triggers detected across current operational metrics."
            )
            immediate_focus = self._build_deterministic_focus_areas(attention_summary)
            limitations = "AI narrative synthesis is offline. Attention conditions and correlations are derived strictly from deterministic benchmark calculations."
        else:
            analysis_state = "ANALYSIS_COMPLETE"
            raw_exec = llm_output.get("executive_attention_summary", "")
            default_exec = (
                f"{facility_name} exhibits {attention_summary.total_attention_count} operational condition(s) requiring attention."
                if attention_summary.total_attention_count > 0
                else f"{facility_name} has no operational deficits requiring attention."
            )
            exec_summary, is_exec_valid = NumericalGroundingReconciler.reconcile_text(
                raw_exec, ground_truth, default_exec
            )
            if not is_exec_valid:
                reconciled_discrepancies.append(
                    "Executive attention summary contained unverified figures and was reconciled."
                )

            # Reconcile risk factors
            raw_risks = llm_output.get("critical_risk_factors", [])
            valid_risks = []
            for rk in raw_risks:
                valid_rk, is_rk_valid = NumericalGroundingReconciler.reconcile_text(
                    rk, ground_truth, ""
                )
                if is_rk_valid and valid_rk:
                    valid_risks.append(valid_rk)
            if not valid_risks:
                valid_risks = [
                    item.evidence_statement
                    for item in attention_summary.attention_items[:5]
                ]
            risk_factors = valid_risks

            # Reconcile cross-domain impact narrative
            raw_cross = llm_output.get("cross_domain_impact_narrative", "")
            default_cross = (
                attention_summary.cross_domain_correlations[0].finding_summary
                if attention_summary.cross_domain_correlations
                else "Departmental performance metrics are operating independently without compound cross-domain failure patterns."
            )
            cross_narrative, is_cross_valid = (
                NumericalGroundingReconciler.reconcile_text(
                    raw_cross, ground_truth, default_cross
                )
            )
            if not is_cross_valid:
                reconciled_discrepancies.append(
                    "Cross-domain narrative contained unverified numbers and was reconciled."
                )

            # Reconcile immediate focus areas
            raw_focus = llm_output.get("immediate_focus_areas", [])
            valid_focus = []
            for fc in raw_focus:
                valid_fc, is_fc_valid = NumericalGroundingReconciler.reconcile_text(
                    fc, ground_truth, ""
                )
                if is_fc_valid and valid_fc:
                    valid_focus.append(valid_fc)
            if not valid_focus:
                valid_focus = self._build_deterministic_focus_areas(attention_summary)
            immediate_focus = valid_focus

            limitations = (
                f"Grounding verified across {len(ground_truth)} numerical indicators."
            )
            if reconciled_discrepancies:
                limitations += (
                    f" [Reconciliation Notice: {'; '.join(reconciled_discrepancies)}]"
                )

        return AttentionAnalysisReport(
            facility_id=snapshot.facility_id,
            facility_name=facility_name,
            snapshot_date=snapshot.snapshot_date,
            scenario=scenario,
            analysis_state=analysis_state,
            executive_attention_summary=exec_summary,
            critical_risk_factors=risk_factors,
            prioritized_operational_concerns=attention_summary.attention_items,
            cross_domain_impact_narrative=cross_narrative,
            immediate_focus_areas=immediate_focus,
            verified_attention_summary=attention_summary,
            data_limitations_and_uncertainty=limitations,
            audit_receipt=receipt,
        )

    def _collect_ground_truth_numbers(
        self,
        snapshot: DailyFacilitySnapshot,
        attention_summary: FacilityAttentionSummary,
        trends: FacilityTrendCalculations,
    ) -> set[float]:
        """Collect all verified numbers across snapshot, attention items, correlations, and trends."""
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

        # Attention item numbers
        add_num(attention_summary.total_attention_count)
        add_num(attention_summary.critical_count)
        add_num(attention_summary.high_count)
        add_num(attention_summary.medium_count)
        add_num(attention_summary.low_count)

        for item in attention_summary.attention_items:
            add_num(item.current_value)
            add_num(item.threshold_or_target)
            add_num(item.variance_or_deficit)

        # Trend numbers
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

    def _build_attention_prompt(
        self,
        snapshot: DailyFacilitySnapshot,
        attention_summary: FacilityAttentionSummary,
        trends: FacilityTrendCalculations,
    ) -> str:
        """Construct grounded prompt containing verified deficits and cross-domain relationships."""
        items_lines = []
        for item in attention_summary.attention_items:
            items_lines.append(
                f"- [{item.severity}/{item.urgency}] {item.domain.upper()}: {item.title} (current={item.current_value} {item.unit}, "
                f"threshold={item.threshold_or_target} {item.unit}, variance={item.variance_or_deficit} {item.unit}). "
                f"Evidence: {item.evidence_statement}"
            )

        corr_lines = []
        for corr in attention_summary.cross_domain_correlations:
            corr_lines.append(
                f"- Correlation [{', '.join(corr.domains)} - {corr.impact_level}]: {corr.finding_summary} "
                f"(Evidence: {'; '.join(corr.evidence_facts)})"
            )

        prompt_dict = {
            "facility_id": snapshot.facility_id,
            "facility_name": snapshot.facility_id.replace("-", " ").title(),
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "scenario": attention_summary.scenario,
            "total_attention_conditions_count": attention_summary.total_attention_count,
            "critical_count": attention_summary.critical_count,
            "high_count": attention_summary.high_count,
            "top_risk_domains": attention_summary.top_risk_domains,
            "verified_attention_items": items_lines,
            "cross_domain_correlations": corr_lines,
            "meaningful_historical_shifts": trends.meaningful_shifts,
        }
        return (
            "Analyze and synthesize operational attention areas and cross-domain compound risks for this facility strictly using the verified facts below:\n\n"
            + json.dumps(prompt_dict, indent=2)
        )

    def _build_deterministic_focus_areas(
        self, attention_summary: FacilityAttentionSummary
    ) -> list[str]:
        """Generate deterministic focus points for facility standup huddles."""
        if not attention_summary.attention_items:
            return [
                "Maintain adherence to standard operating procedures across all shifts.",
                "Continue routine clinical and administrative monitoring.",
            ]
        focus = []
        for item in attention_summary.attention_items[:3]:
            focus.append(
                f"Review {item.domain_display_name} ({item.title}): {item.operational_risk_summary}"
            )
        return focus
