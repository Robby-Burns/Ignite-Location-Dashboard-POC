"""Facility State Agent for Story 2.1 — Analyze Facility State.

Translates current facility metrics and cross-domain calculations into human-readable
operational state analysis while strictly enforcing numerical grounding and Spec §8 fallbacks.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.schemas import FacilityCalculations
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient
from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries


class DomainStateNarrative(BaseModel):
    """Plain-language operational narrative for a specific domain."""

    domain: str = Field(..., description="Domain name")
    headline: str = Field(..., description="Single-line domain operational headline")
    narrative: str = Field(..., description="Multi-sentence operational assessment")
    key_metrics_cited: list[str] = Field(
        default_factory=list, description="List of source metric values referenced"
    )
    status: Literal["POSITIVE", "NEUTRAL", "ATTENTION", "CRITICAL"] = Field(
        default="NEUTRAL", description="Assessed status"
    )


class FacilityStateAnalysis(BaseModel):
    """Human-readable operational facility state analysis (AC-2.1.1, AC-2.1.2)."""

    facility_id: str = Field(..., description="Unique facility identifier")
    facility_name: str = Field(..., description="Facility name")
    analysis_date: str = Field(
        ..., description="Snapshot date of analysis (ISO format)"
    )
    scenario: str = Field(
        default="baseline", description="Operational scenario evaluated"
    )
    analysis_state: Literal[
        "ANALYSIS_COMPLETE", "AI_ANALYSIS_UNAVAILABLE", "PARTIAL_DATA"
    ] = Field(
        default="ANALYSIS_COMPLETE", description="Explicit analysis state per Spec §8"
    )
    executive_summary: str = Field(
        ..., description="Concise executive operational summary for leadership"
    )
    overall_health_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Composite operational health index (0-100) derived deterministically",
    )
    overall_status: Literal[
        "OPTIMAL", "STABLE", "ATTENTION_REQUIRED", "CRITICAL_RISK"
    ] = Field(default="STABLE", description="Overall operational status")
    domain_narratives: dict[str, DomainStateNarrative] = Field(
        default_factory=dict, description="Domain-by-domain plain-language assessments"
    )
    cross_domain_findings: list[str] = Field(
        default_factory=list, description="Inter-departmental operational interactions"
    )
    verified_calculations: FacilityCalculations = Field(
        ..., description="Complete underlying verified mathematical calculations"
    )
    data_limitations_and_uncertainty: str = Field(
        default="Analysis grounded strictly in current daily snapshot and 30-day historical time-series.",
        description="Explicit disclosure of data boundaries and missing metrics (INV-004, INV-005)",
    )
    audit_receipt: LLMExecutionReceipt = Field(
        ..., description="LLM execution and verification receipt"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of report generation",
    )


class NumericalGroundingReconciler:
    """Reconciles LLM-generated narrative claims against source data and calculations (AC-2.1.2, INV-002)."""

    # Harmless structural/temporal numbers permitted in narratives
    STRUCTURAL_NUMBERS: ClassVar[set[float]] = {
        0.0,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
        7.0,
        14.0,
        20.0,
        24.0,
        30.0,
        48.0,
        72.0,
        100.0,
    }

    @classmethod
    def build_ground_truth_set(
        cls,
        snapshot: DailyFacilitySnapshot,
        calculations: FacilityCalculations,
    ) -> set[float]:
        """Collect all verified numbers present in raw snapshot and calculated domains."""
        numbers: set[float] = set(cls.STRUCTURAL_NUMBERS)

        def add_num(val: Any) -> None:
            if val is not None and isinstance(val, (int, float)):
                f = round(float(val), 2)
                numbers.add(f)
                numbers.add(round(f, 1))
                numbers.add(round(f, 0))

        # Census
        c = snapshot.census
        for v in [
            c.current_census,
            c.total_capacity,
            c.occupancy_rate_pct,
            c.available_beds,
            c.previous_day_census,
            c.previous_week_census,
            c.budgeted_target_census,
        ]:
            add_num(v)

        # Admissions / Discharges
        ad = snapshot.admissions_discharges
        for v in [
            ad.today_admissions,
            ad.today_discharges,
            ad.net_flow,
            ad.pending_admissions,
            ad.pending_discharges,
            ad.rolling_7d_admissions,
            ad.rolling_7d_discharges,
        ]:
            add_num(v)

        # LOS
        los = snapshot.length_of_stay
        for v in [
            los.average_los_days,
            los.target_los_days,
            los.short_stay_count,
            los.long_stay_count,
            los.los_outliers_count,
        ]:
            add_num(v)

        # Staffing
        st = snapshot.staffing
        for v in [
            st.hppd_actual,
            st.hppd_budgeted_target,
            st.rn_hours_actual,
            st.lpn_hours_actual,
            st.cna_hours_actual,
            st.call_in_absences_count,
            st.open_shifts_count,
            st.overtime_hours,
            st.agency_staff_pct,
        ]:
            add_num(v)

        # Therapy
        th = snapshot.therapy
        for v in [
            th.avg_daily_treatment_minutes_scheduled,
            th.avg_daily_treatment_minutes_delivered,
            th.treatment_completion_rate_pct,
            th.patients_meeting_weekly_goals_pct,
            th.patients_on_therapy_hold,
        ]:
            add_num(v)

        # Payer
        pa = snapshot.payer_auth
        for v in [
            pa.expiring_authorizations_48h,
            pa.expiring_authorizations_72h,
            pa.pending_reauthorizations_count,
            pa.auth_denials_pending_appeal_count,
        ]:
            add_num(v)
        for mix_val in pa.payer_mix_pct.values():
            add_num(mix_val)

        # Hospitality
        ho = snapshot.hospitality
        for v in [
            ho.dining_satisfaction_score,
            ho.cleanliness_room_comfort_score,
            ho.guest_satisfaction_nps,
            ho.open_guest_service_requests,
            ho.avg_request_resolution_hours,
        ]:
            add_num(v)

        # Transfers
        ht = snapshot.hospital_transfers
        for v in [
            ht.unplanned_transfers_30d_count,
            ht.readmission_rate_30d_pct,
            ht.benchmark_readmission_rate_pct,
            ht.acute_transfers_this_week,
        ]:
            add_num(v)
        for reason_val in ht.transfers_by_reason.values():
            add_num(reason_val)

        # Calculations deltas and observations
        for summary in calculations.domains.values():
            for m in summary.metrics.values():
                add_num(m.value)
                add_num(m.target_or_budget)
                add_num(m.delta_vs_target)
                add_num(m.delta_vs_prev_day)
                add_num(m.delta_vs_prev_week)

        return numbers

    @classmethod
    def reconcile_text(
        cls,
        text: str,
        ground_truth: set[float],
        fallback_text: str,
    ) -> tuple[str, bool]:
        """Validate all numbers in text against ground truth. If ungrounded numbers exist, return fallback."""
        if not text:
            return fallback_text, False

        # Extract all numbers (e.g. "94", "100.0", "94%")
        matches = re.findall(r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)(%?)", text)
        for num_str, _ in matches:
            try:
                num_val = round(float(num_str), 2)
                # Check direct or rounded match
                if (
                    num_val not in ground_truth
                    and round(num_val, 1) not in ground_truth
                    and round(num_val, 0) not in ground_truth
                ):
                    # Found ungrounded number! Reject text and return verified fallback
                    return fallback_text, False
            except ValueError:
                continue

        return text, True


SYSTEM_PROMPT_STATE_ANALYSIS = """You are an executive operational decision support agent for Ignite Medical Resorts.
Your purpose is to translate facility operational data into a clear, insightful, professional summary for facility leaders.

Rules and Invariants (Strictly Enforced):
1. ACCURACY & ZERO INVENTION (INV-002, AC-2.1.2): Every number you mention MUST exist in the provided metrics. Do not fabricate or estimate numbers.
2. OBSERVATION vs INFERENCE (INV-003): Clearly distinguish between what the verified numbers show and your operational interpretation.
3. NO HARDCODED SCENARIO TEMPLATES (INV-001, FR-008): Base your assessment dynamically on the exact numbers provided.
4. NO REAL PHI (INV-008): Only aggregate facility indicators are used; no patient names or identifiers.
5. NO AUTONOMOUS ACTIONS (INV-006, FR-009): Present findings as decision support for human review.

Return your analysis in valid JSON with this exact structure:
{
  "executive_summary": "Comprehensive 3-5 sentence operational overview highlighting key strengths and immediate pressure points.",
  "domain_narratives": {
    "census": {
      "headline": "...",
      "narrative": "...",
      "key_metrics_cited": ["..."],
      "status": "POSITIVE" // "POSITIVE", "NEUTRAL", "ATTENTION", "CRITICAL"
    },
    "staffing": { ... },
    "therapy": { ... },
    "payer_auth": { ... },
    "hospitality": { ... },
    "hospital_transfers": { ... },
    "length_of_stay": { ... },
    "admissions_discharges": { ... }
  },
  "cross_domain_findings": ["..."],
  "data_limitations": "..."
}
"""


class FacilityStateAgent:
    """Agent that analyzes facility operational state from Mock Domo MCP data."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def analyze_facility_state(
        self,
        facility_id: str,
        scenario: str = "baseline",
        days_history: int = 30,
    ) -> FacilityStateAnalysis:
        """Retrieve facility data, compute deterministic calculations, and generate human-readable state analysis."""
        facility_name = facility_id.replace("-", " ").title()

        # 1. Retrieve current snapshot and historical series via MCP
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
                    f"Cannot analyze facility '{facility_id}': data unavailable."
                ) from e
            raise

        # 2. Compute verified deterministic mathematical metrics
        calculations = calculate_facility_metrics(
            snapshot=snapshot,
            history=history_series,
            scenario=scenario,
        )

        # 3. Derive deterministic health score and overall status (FR-006, F-4)
        overall_health_score = self._compute_health_score(calculations)
        overall_status = (
            "CRITICAL_RISK"
            if overall_health_score < 60
            else ("ATTENTION_REQUIRED" if overall_health_score < 75 else "STABLE")
        )

        # 4. Formulate prompt containing verified facts
        user_prompt = self._build_user_prompt(snapshot, history_series, calculations)

        # 5. Execute LLM call with structured output
        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=SYSTEM_PROMPT_STATE_ANALYSIS,
            user_prompt=user_prompt,
            response_schema_name="FacilityStateAnalysis",
        )

        # 6. Build ground truth numbers for reconciliation
        ground_truth = NumericalGroundingReconciler.build_ground_truth_set(
            snapshot, calculations
        )
        reconciled_discrepancies: list[str] = []

        # 7. Check if AI interpretation is available (Spec §8)
        if llm_output is None or not receipt.is_live_call:
            # Explicit AI_ANALYSIS_UNAVAILABLE State per Spec §8
            analysis_state = "AI_ANALYSIS_UNAVAILABLE"
            c = snapshot.census
            st = snapshot.staffing
            exec_summary = (
                f"{facility_name} is operating at {c.occupancy_rate_pct}% occupancy with {c.current_census} occupied beds out of {c.total_capacity} capacity. "
                f"Operational health score is {overall_health_score}/100 ({overall_status}). "
                f"Nursing staffing delivered {st.hppd_actual} HPPD vs {st.hppd_budgeted_target} budgeted. "
                f"(AI interpretation is unavailable; displaying validated calculations and metrics per Spec §8)."
            )
            domain_narratives = {}
            for d_name, calc in calculations.domains.items():
                domain_narratives[d_name] = DomainStateNarrative(
                    domain=d_name,
                    headline=f"{calc.domain_display_name} ({calc.risk_level.title()} Risk)",
                    narrative=" ".join(calc.key_findings),
                    key_metrics_cited=list(calc.metrics.keys()),
                    status="CRITICAL"
                    if calc.risk_level == "HIGH"
                    else ("ATTENTION" if calc.risk_level == "MEDIUM" else "POSITIVE"),
                )
            cross_findings = [c.finding_summary for c in calculations.correlations]
            limitations = "AI analysis is offline/unavailable. Indicators and domain observations are derived strictly from deterministic mathematical calculations."
        else:
            # AI Analysis returned: Perform numerical grounding reconciliation (AC-2.1.2, F-1)
            analysis_state = "ANALYSIS_COMPLETE"
            raw_exec = llm_output.get("executive_summary", "")
            default_exec = (
                f"{facility_name} is operating at {snapshot.census.occupancy_rate_pct}% occupancy with "
                f"{snapshot.census.current_census} occupied beds. Operational health score is {overall_health_score}/100."
            )
            exec_summary, is_exec_valid = NumericalGroundingReconciler.reconcile_text(
                raw_exec, ground_truth, default_exec
            )
            if not is_exec_valid:
                reconciled_discrepancies.append(
                    "Executive summary contained unverified numbers and was reconciled with verified snapshot metrics."
                )

            domain_narratives = {}
            raw_narratives = llm_output.get("domain_narratives", {})
            for domain_name, calc in calculations.domains.items():
                fallback_narrative = " ".join(calc.key_findings)
                fallback_headline = f"{calc.domain_display_name} Assessment"
                if domain_name in raw_narratives:
                    raw_d = raw_narratives[domain_name]
                    raw_headline = raw_d.get("headline", fallback_headline)
                    raw_body = raw_d.get("narrative", fallback_narrative)

                    valid_headline, _ = NumericalGroundingReconciler.reconcile_text(
                        raw_headline, ground_truth, fallback_headline
                    )
                    valid_narrative, is_narrative_valid = (
                        NumericalGroundingReconciler.reconcile_text(
                            raw_body, ground_truth, fallback_narrative
                        )
                    )
                    if not is_narrative_valid:
                        reconciled_discrepancies.append(
                            f"Domain narrative for '{domain_name}' was reconciled due to ungrounded numerical claims."
                        )

                    # Reconcile cited metrics to prevent hallucinated numbers in cited strings
                    raw_cited = raw_d.get(
                        "key_metrics_cited", list(calc.metrics.keys())
                    )
                    valid_cited = []
                    for cited_item in raw_cited:
                        valid_item, is_item_valid = (
                            NumericalGroundingReconciler.reconcile_text(
                                cited_item, ground_truth, ""
                            )
                        )
                        if is_item_valid and valid_item:
                            valid_cited.append(valid_item)
                    if not valid_cited:
                        valid_cited = list(calc.metrics.keys())

                    domain_narratives[domain_name] = DomainStateNarrative(
                        domain=domain_name,
                        headline=valid_headline,
                        narrative=valid_narrative,
                        key_metrics_cited=valid_cited,
                        status=raw_d.get("status", "NEUTRAL"),
                    )
                else:
                    domain_narratives[domain_name] = DomainStateNarrative(
                        domain=domain_name,
                        headline=fallback_headline,
                        narrative=fallback_narrative,
                        key_metrics_cited=list(calc.metrics.keys()),
                        status="ATTENTION" if calc.risk_level == "HIGH" else "NEUTRAL",
                    )

            # Reconcile cross domain findings
            raw_cross = llm_output.get(
                "cross_domain_findings",
                [c.finding_summary for c in calculations.correlations],
            )
            valid_cross = []
            for cf in raw_cross:
                valid_cf, is_cf_valid = NumericalGroundingReconciler.reconcile_text(
                    cf, ground_truth, ""
                )
                if is_cf_valid and valid_cf:
                    valid_cross.append(valid_cf)
            if not valid_cross:
                valid_cross = [c.finding_summary for c in calculations.correlations]

            cross_findings = valid_cross
            limitations = llm_output.get(
                "data_limitations",
                "Analysis based strictly on verified snapshot and historical metrics.",
            )
            if reconciled_discrepancies:
                limitations += (
                    f" [Reconciliation Notice: {'; '.join(reconciled_discrepancies)}]"
                )

        return FacilityStateAnalysis(
            facility_id=facility_id,
            facility_name=facility_name,
            analysis_date=snapshot.snapshot_date.isoformat(),
            scenario=scenario,
            analysis_state=analysis_state,
            executive_summary=exec_summary,
            overall_health_score=overall_health_score,
            overall_status=overall_status,
            domain_narratives=domain_narratives,
            cross_domain_findings=cross_findings,
            verified_calculations=calculations,
            data_limitations_and_uncertainty=limitations,
            audit_receipt=receipt,
        )

    def _build_user_prompt(
        self,
        snapshot: DailyFacilitySnapshot,
        history: FacilityHistoricalSeries,
        calculations: FacilityCalculations,
    ) -> str:
        """Construct grounded prompt containing verified metrics and calculations."""
        facility_name = snapshot.facility_id.replace("-", " ").title()
        metrics_dump = {
            "facility_id": snapshot.facility_id,
            "facility_name": facility_name,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "domains": {
                name: {
                    "display_name": summary.domain_display_name,
                    "metrics": {
                        m_name: {
                            "value": m.value,
                            "unit": m.unit,
                            "target": m.target_or_budget,
                            "delta_target": m.delta_vs_target,
                            "delta_prev_week": m.delta_vs_prev_week,
                            "trend": m.trend_direction,
                            "status": m.status,
                        }
                        for m_name, m in summary.metrics.items()
                    },
                    "key_findings": summary.key_findings,
                    "risk_level": summary.risk_level,
                }
                for name, summary in calculations.domains.items()
            },
            "cross_domain_correlations": [
                {
                    "domains": c.domains,
                    "finding": c.finding_summary,
                    "evidence": c.evidence_facts,
                    "impact": c.impact_level,
                }
                for c in calculations.correlations
            ],
        }
        return f"Analyze the following verified facility operational dataset:\n\n{json.dumps(metrics_dump, indent=2)}"

    def _compute_health_score(self, calculations: FacilityCalculations) -> int:
        """Compute composite operational health score (0-100) from verified calculations."""
        score = 100
        for summary in calculations.domains.values():
            if summary.risk_level == "HIGH":
                score -= 15
            elif summary.risk_level == "MEDIUM":
                score -= 7

        for corr in calculations.correlations:
            if corr.impact_level == "CRITICAL":
                score -= 10
            elif corr.impact_level == "MODERATE":
                score -= 5

        return max(30, min(98, score))
