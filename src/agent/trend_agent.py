"""Facility Trend Explanation Agent for Story 2.2 — Explain Metrics and Historical Context.

Translates complex operational metrics and 30-day time-series trajectories into plain-language,
non-technical explanations for healthcare executives and clinical leaders.
Enforces strict numerical grounding (INV-002, AC-2.1.2) and transparent Spec §8 offline fallbacks.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.agent.state_agent import NumericalGroundingReconciler
from src.analytics.trends import (
    FacilityTrendCalculations,
    calculate_historical_trends,
)
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient
from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries


class MetricExplanationDetail(BaseModel):
    """Plain-language, non-technical explanation of a single metric (AC-2.2.1)."""

    metric_name: str = Field(..., description="Technical metric identifier")
    display_name: str = Field(..., description="Human-friendly label")
    domain: str = Field(..., description="Operational domain")
    current_value_formatted: str = Field(
        ..., description="Formatted current value with unit"
    )
    plain_language_meaning: str = Field(
        ...,
        description="What this metric represents in terms understandable to non-technical leaders",
    )
    operational_significance: str = Field(
        ...,
        description="Why this number matters to facility performance, regulatory standing, or finances",
    )
    benchmark_context: str = Field(
        ...,
        description="How current performance compares against standard benchmarks or target matrices",
    )


class DomainTrendExplanation(BaseModel):
    """Plain-language narrative explaining meaningful historical changes over time (AC-2.2.2)."""

    domain: str = Field(..., description="Operational domain")
    domain_display_name: str = Field(..., description="Domain label")
    headline: str = Field(..., description="Summary headline of 7-to-30 day trajectory")
    narrative: str = Field(
        ...,
        description="Multi-sentence plain-language explanation of trend trajectory, drivers, and stability",
    )
    trajectory_direction: Literal["INCREASING", "DECREASING", "STABLE", "VOLATILE"] = (
        Field(default="STABLE", description="Assessed historical trend direction")
    )
    is_meaningful_shift: bool = Field(
        default=False,
        description="Whether this trend represents a materially significant operational change",
    )
    cited_metrics: list[str] = Field(
        default_factory=list, description="Verified historical metrics and deltas cited"
    )


class FacilityTrendExplanationReport(BaseModel):
    """Complete plain-language metric and historical trend explanation report (Story 2.2)."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Facility name")
    analysis_date: str = Field(..., description="Snapshot date of analysis")
    scenario: str = Field(default="baseline", description="Evaluated scenario")
    analysis_state: Literal[
        "ANALYSIS_COMPLETE", "AI_ANALYSIS_UNAVAILABLE", "INSUFFICIENT_CONTEXT"
    ] = Field(
        default="ANALYSIS_COMPLETE", description="Explicit analysis state per Spec §8"
    )
    executive_trend_summary: str = Field(
        ...,
        description="Executive overview of 7-to-30 day facility momentum and historical shifts",
    )
    metric_explanations: dict[str, MetricExplanationDetail] = Field(
        default_factory=dict,
        description="Non-technical plain-language explanations of core operational metrics (AC-2.2.1)",
    )
    trend_explanations: dict[str, DomainTrendExplanation] = Field(
        default_factory=dict,
        description="Historical trajectory and change explanations across domains (AC-2.2.2)",
    )
    notable_shifts: list[str] = Field(
        default_factory=list,
        description="Factual list of significant historical shifts identified in the data",
    )
    data_limitations_and_uncertainty: str = Field(
        default="Trend analysis is grounded strictly in verified 30-day historical time-series data.",
        description="Explicit disclosure of data boundaries and missing metrics (INV-004, INV-005)",
    )
    audit_receipt: LLMExecutionReceipt = Field(
        ..., description="LLM execution and verification receipt"
    )
    verified_calculations: FacilityTrendCalculations = Field(
        ..., description="Underlying deterministic time-series calculations"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of report generation",
    )


SYSTEM_PROMPT_TREND_EXPLANATION = """You are an executive operational decision support agent for Ignite Medical Resorts.
Your objective is to explain important facility metrics in plain language (AC-2.2.1) and explain meaningful changes over time (AC-2.2.2).

Rules and Invariants (Strictly Enforced):
1. NON-TECHNICAL PLAIN LANGUAGE (AC-2.2.1): Explain what numbers mean without assuming deep clinical or statistical background.
2. ZERO INVENTION & NUMERICAL GROUNDING (INV-002, AC-2.1.2): Every number, delta, or percentage you mention MUST exist in the provided trend data. Do not fabricate numbers.
3. CAUSAL BOUNDARIES: Do not claim a cause that is not supported by the data. State observations factually.
4. INSUFFICIENT CONTEXT: If historical data is fewer than 7 days, explicitly state that context is insufficient to substantiate multi-week trajectories.
5. NO REAL PHI (INV-008): Only aggregate facility indicators are used; no patient names or identifiers.
6. NO HARDCODED SCENARIOS (INV-001): Base your assessment strictly on the dynamic metrics and trends provided.

Return your explanation in valid JSON matching this exact structure:
{
  "executive_trend_summary": "3-4 sentence leadership summary of overall 30-day facility trajectory and key momentum shifts.",
  "metric_explanations": {
    "current_census": {
      "plain_language_meaning": "...",
      "operational_significance": "...",
      "benchmark_context": "..."
    },
    "hppd_actual": { ... },
    "treatment_completion_rate_pct": { ... },
    "expiring_authorizations_48h": { ... },
    "readmission_rate_30d_pct": { ... }
  },
  "trend_explanations": {
    "census": {
      "headline": "...",
      "narrative": "...",
      "trajectory_direction": "STABLE", // INCREASING, DECREASING, STABLE, VOLATILE
      "is_meaningful_shift": false,
      "cited_metrics": ["..."]
    },
    "admissions_discharges": { ... },
    "length_of_stay": { ... },
    "staffing": { ... },
    "therapy": { ... },
    "payer_auth": { ... },
    "hospitality": { ... },
    "hospital_transfers": { ... }
  },
  "notable_shifts": ["..."],
  "data_limitations": "..."
}
"""


class FacilityTrendExplanationAgent:
    """Agent that explains operational metrics and 30-day historical trends for leadership decision support."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def explain_facility_trends(
        self,
        facility_id: str,
        scenario: str = "baseline",
        days_history: int = 30,
    ) -> FacilityTrendExplanationReport:
        """Retrieve facility data, compute deterministic time-series trends, and generate plain-language explanations."""
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
                    f"Cannot explain trends for facility '{facility_id}': data unavailable."
                ) from e
            raise

        # 2. Compute verified deterministic historical trends and metric definitions
        trend_calcs = calculate_historical_trends(
            snapshot=snapshot,
            history=history_series,
            scenario=scenario,
        )

        # 3. Check data sufficiency boundary
        if not trend_calcs.is_context_sufficient:
            # Insufficient Context state (fewer than 7 days)
            analysis_state = "INSUFFICIENT_CONTEXT"
            exec_summary = (
                f"Historical context for {facility_name} is limited to {trend_calcs.days_analyzed} day(s). "
                f"A minimum of 7 days of historical records is required to substantiate multi-week trend trajectories without claiming unsupported causes."
            )
            metric_explanations = self._build_deterministic_metric_explanations(
                snapshot, trend_calcs
            )
            trend_explanations = self._build_deterministic_trend_explanations(
                trend_calcs
            )
            limitations = " ".join(trend_calcs.context_limitations)
            receipt = LLMExecutionReceipt(
                receipt_id=f"REC-OFFLINE-{snapshot.facility_id[:8]}-insufficient-ctx",
                provider="deterministic-insufficient-context",
                model="deterministic",
                latency_ms=0.0,
                is_live_call=False,
            )

            return FacilityTrendExplanationReport(
                facility_id=facility_id,
                facility_name=facility_name,
                analysis_date=snapshot.snapshot_date.isoformat(),
                scenario=scenario,
                analysis_state=analysis_state,
                executive_trend_summary=exec_summary,
                metric_explanations=metric_explanations,
                trend_explanations=trend_explanations,
                notable_shifts=trend_calcs.meaningful_shifts,
                data_limitations_and_uncertainty=limitations,
                audit_receipt=receipt,
                verified_calculations=trend_calcs,
            )

        # 4. Formulate prompt containing verified facts
        user_prompt = self._build_trend_prompt(snapshot, history_series, trend_calcs)

        # 5. Execute LLM call with structured output
        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=SYSTEM_PROMPT_TREND_EXPLANATION,
            user_prompt=user_prompt,
            response_schema_name="FacilityTrendExplanationReport",
        )

        # 6. Build ground truth numbers for reconciliation
        ground_truth = self._build_trend_ground_truth_set(snapshot, trend_calcs)
        reconciled_discrepancies: list[str] = []

        # 7. Check if AI interpretation is available (Spec §8)
        if llm_output is None or not receipt.is_live_call:
            # Explicit AI_ANALYSIS_UNAVAILABLE state per Spec §8
            analysis_state = "AI_ANALYSIS_UNAVAILABLE"
            c_trend = trend_calcs.trends.get("current_census")
            st_trend = trend_calcs.trends.get("hppd_actual")
            exec_summary = (
                f"{facility_name} operational trajectory over {trend_calcs.days_analyzed} days: "
                f"Census is {c_trend.current_value if c_trend else snapshot.census.current_census} guests (7d delta: {c_trend.delta_7d if c_trend else 0:+} guests); "
                f"Nursing HPPD delivered is {st_trend.current_value if st_trend else snapshot.staffing.hppd_actual} (7d delta: {st_trend.delta_7d if st_trend else 0:+} HPPD). "
                f"(AI interpretation is unavailable; displaying validated deterministic time-series trends per Spec §8)."
            )
            metric_explanations = self._build_deterministic_metric_explanations(
                snapshot, trend_calcs
            )
            trend_explanations = self._build_deterministic_trend_explanations(
                trend_calcs
            )
            notable_shifts = trend_calcs.meaningful_shifts
            limitations = "AI trend interpretation is offline. Metrics, definitions, and trajectory summaries are derived strictly from deterministic time-series calculations."
        else:
            # AI Analysis returned: Perform numerical grounding reconciliation (AC-2.1.2, F-1)
            analysis_state = "ANALYSIS_COMPLETE"
            raw_exec = llm_output.get("executive_trend_summary", "")
            default_exec = f"{facility_name} 30-day historical analysis: {len(trend_calcs.meaningful_shifts)} significant operational shifts detected across evaluated domains."
            exec_summary, is_exec_valid = NumericalGroundingReconciler.reconcile_text(
                raw_exec, ground_truth, default_exec
            )
            if not is_exec_valid:
                reconciled_discrepancies.append(
                    "Executive trend summary contained unverified numbers and was reconciled with verified time-series metrics."
                )

            # Reconcile Metric Explanations (AC-2.2.1)
            metric_explanations = {}
            raw_metric_exp = llm_output.get("metric_explanations", {})
            deterministic_defs = trend_calcs.metric_definitions

            for m_key, defn in deterministic_defs.items():
                curr_val_str = self._format_metric_val(m_key, snapshot)
                if m_key in raw_metric_exp:
                    m_data = raw_metric_exp[m_key]
                    raw_meaning = m_data.get(
                        "plain_language_meaning", defn.plain_language_meaning
                    )
                    raw_sig = m_data.get(
                        "operational_significance", defn.operational_significance
                    )
                    raw_bench = m_data.get(
                        "benchmark_context", defn.benchmark_or_target_desc
                    )

                    valid_meaning, _ = NumericalGroundingReconciler.reconcile_text(
                        raw_meaning, ground_truth, defn.plain_language_meaning
                    )
                    valid_sig, _ = NumericalGroundingReconciler.reconcile_text(
                        raw_sig, ground_truth, defn.operational_significance
                    )
                    valid_bench, _ = NumericalGroundingReconciler.reconcile_text(
                        raw_bench, ground_truth, defn.benchmark_or_target_desc
                    )

                    metric_explanations[m_key] = MetricExplanationDetail(
                        metric_name=m_key,
                        display_name=defn.display_name,
                        domain=defn.domain,
                        current_value_formatted=curr_val_str,
                        plain_language_meaning=valid_meaning,
                        operational_significance=valid_sig,
                        benchmark_context=valid_bench,
                    )
                else:
                    metric_explanations[m_key] = MetricExplanationDetail(
                        metric_name=m_key,
                        display_name=defn.display_name,
                        domain=defn.domain,
                        current_value_formatted=curr_val_str,
                        plain_language_meaning=defn.plain_language_meaning,
                        operational_significance=defn.operational_significance,
                        benchmark_context=defn.benchmark_or_target_desc,
                    )

            # Reconcile Domain Trend Explanations (AC-2.2.2)
            trend_explanations = {}
            raw_trends = llm_output.get("trend_explanations", {})
            domains = [
                "census",
                "admissions_discharges",
                "length_of_stay",
                "staffing",
                "therapy",
                "payer_auth",
                "hospitality",
                "hospital_transfers",
            ]

            for d_name in domains:
                d_display = d_name.replace("_", " ").title()
                fallback_trend = self._get_domain_trend_fallback(d_name, trend_calcs)

                if d_name in raw_trends:
                    raw_d = raw_trends[d_name]
                    raw_head = raw_d.get("headline", fallback_trend.headline)
                    raw_narrative = raw_d.get("narrative", fallback_trend.narrative)

                    valid_head, _ = NumericalGroundingReconciler.reconcile_text(
                        raw_head, ground_truth, fallback_trend.headline
                    )
                    valid_narrative, is_narrative_valid = (
                        NumericalGroundingReconciler.reconcile_text(
                            raw_narrative, ground_truth, fallback_trend.narrative
                        )
                    )
                    if not is_narrative_valid:
                        reconciled_discrepancies.append(
                            f"Trend narrative for domain '{d_name}' was reconciled due to ungrounded numerical claims."
                        )

                    raw_cited = raw_d.get("cited_metrics", fallback_trend.cited_metrics)
                    valid_cited = []
                    for c_item in raw_cited:
                        valid_c, is_c_valid = (
                            NumericalGroundingReconciler.reconcile_text(
                                c_item, ground_truth, ""
                            )
                        )
                        if is_c_valid and valid_c:
                            valid_cited.append(valid_c)
                    if not valid_cited:
                        valid_cited = fallback_trend.cited_metrics

                    trend_explanations[d_name] = DomainTrendExplanation(
                        domain=d_name,
                        domain_display_name=d_display,
                        headline=valid_head,
                        narrative=valid_narrative,
                        trajectory_direction=raw_d.get(
                            "trajectory_direction", fallback_trend.trajectory_direction
                        ),
                        is_meaningful_shift=raw_d.get(
                            "is_meaningful_shift", fallback_trend.is_meaningful_shift
                        ),
                        cited_metrics=valid_cited,
                    )
                else:
                    trend_explanations[d_name] = fallback_trend

            # Notable shifts
            raw_notable = llm_output.get(
                "notable_shifts", trend_calcs.meaningful_shifts
            )
            valid_notable = []
            for item in raw_notable:
                valid_item, is_item_valid = NumericalGroundingReconciler.reconcile_text(
                    item, ground_truth, ""
                )
                if is_item_valid and valid_item:
                    valid_notable.append(valid_item)
            if not valid_notable:
                valid_notable = trend_calcs.meaningful_shifts
            notable_shifts = valid_notable

            limitations = llm_output.get(
                "data_limitations",
                "Trend analysis grounded in verified 30-day historical time-series data.",
            )
            if reconciled_discrepancies:
                limitations += (
                    f" [Reconciliation Notice: {'; '.join(reconciled_discrepancies)}]"
                )

        return FacilityTrendExplanationReport(
            facility_id=facility_id,
            facility_name=facility_name,
            analysis_date=snapshot.snapshot_date.isoformat(),
            scenario=scenario,
            analysis_state=analysis_state,
            executive_trend_summary=exec_summary,
            metric_explanations=metric_explanations,
            trend_explanations=trend_explanations,
            notable_shifts=notable_shifts,
            data_limitations_and_uncertainty=limitations,
            audit_receipt=receipt,
            verified_calculations=trend_calcs,
        )

    def _build_trend_ground_truth_set(
        self,
        snapshot: DailyFacilitySnapshot,
        trend_calcs: FacilityTrendCalculations,
    ) -> set[float]:
        """Collect all verified numbers across current snapshot and historical trend analytics."""
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

        # Trend calculations numbers
        add_num(trend_calcs.days_analyzed)
        for t in trend_calcs.trends.values():
            add_num(t.current_value)
            add_num(t.value_7d_ago)
            add_num(t.value_14d_ago)
            add_num(t.value_30d_ago)
            add_num(t.delta_7d)
            add_num(t.delta_30d)
            add_num(t.pct_change_7d)
            add_num(t.pct_change_30d)
            add_num(t.rolling_7d_avg)
            add_num(t.rolling_30d_avg)
            add_num(t.min_30d)
            add_num(t.max_30d)

        return numbers

    def _build_trend_prompt(
        self,
        snapshot: DailyFacilitySnapshot,
        history: FacilityHistoricalSeries,
        trend_calcs: FacilityTrendCalculations,
    ) -> str:
        """Construct dynamic grounded prompt containing verified metrics and time-series deltas."""
        trend_lines = []
        for t in trend_calcs.trends.values():
            pct_str = f"{t.pct_change_7d:+}%" if t.pct_change_7d is not None else "N/A"
            delta_str = f"{t.delta_7d:+}" if t.delta_7d is not None else "0"
            trend_lines.append(
                f"- {t.display_name} ({t.domain}): current={t.current_value} {t.unit}, "
                f"7d_ago={t.value_7d_ago}, delta_7d={delta_str} ({pct_str}), "
                f"7d_avg={t.rolling_7d_avg}, 30d_range=[{t.min_30d}, {t.max_30d}], direction={t.trend_direction}."
            )

        prompt_dict = {
            "facility_id": snapshot.facility_id,
            "facility_name": snapshot.facility_id.replace("-", " ").title(),
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "scenario": trend_calcs.scenario,
            "days_analyzed": trend_calcs.days_analyzed,
            "meaningful_shifts": trend_calcs.meaningful_shifts,
            "verified_trends": trend_lines,
        }
        return (
            "Explain the operational metrics and historical trends for this facility based strictly on the verified data below:\n\n"
            + json.dumps(prompt_dict, indent=2)
        )

    def _build_deterministic_metric_explanations(
        self,
        snapshot: DailyFacilitySnapshot,
        trend_calcs: FacilityTrendCalculations,
    ) -> dict[str, MetricExplanationDetail]:
        """Build standard plain-language metric explanations without LLM."""
        explanations = {}
        for m_key, defn in trend_calcs.metric_definitions.items():
            curr_str = self._format_metric_val(m_key, snapshot)
            explanations[m_key] = MetricExplanationDetail(
                metric_name=m_key,
                display_name=defn.display_name,
                domain=defn.domain,
                current_value_formatted=curr_str,
                plain_language_meaning=defn.plain_language_meaning,
                operational_significance=defn.operational_significance,
                benchmark_context=defn.benchmark_or_target_desc,
            )
        return explanations

    def _build_deterministic_trend_explanations(
        self,
        trend_calcs: FacilityTrendCalculations,
    ) -> dict[str, DomainTrendExplanation]:
        """Build deterministic domain trend narratives without LLM."""
        explanations = {}
        domains = [
            "census",
            "admissions_discharges",
            "length_of_stay",
            "staffing",
            "therapy",
            "payer_auth",
            "hospitality",
            "hospital_transfers",
        ]
        for d in domains:
            explanations[d] = self._get_domain_trend_fallback(d, trend_calcs)
        return explanations

    def _get_domain_trend_fallback(
        self,
        domain: str,
        trend_calcs: FacilityTrendCalculations,
    ) -> DomainTrendExplanation:
        """Create deterministic domain trend explanation from calculated time-series."""
        d_display = domain.replace("_", " ").title()
        domain_trends = [t for t in trend_calcs.trends.values() if t.domain == domain]

        if not domain_trends:
            return DomainTrendExplanation(
                domain=domain,
                domain_display_name=d_display,
                headline=f"{d_display} Trajectory Assessment",
                narrative=f"Operational metrics in {d_display} are being monitored.",
                trajectory_direction="STABLE",
                is_meaningful_shift=False,
                cited_metrics=[],
            )

        summaries = [t.shift_summary for t in domain_trends]
        directions = [t.trend_direction for t in domain_trends]
        has_meaningful = any(t.is_meaningful_shift for t in domain_trends)

        primary_dir: Literal["INCREASING", "DECREASING", "STABLE", "VOLATILE"] = (
            "STABLE"
        )
        if has_meaningful:
            if "DECREASING" in directions and "INCREASING" in directions:
                primary_dir = "VOLATILE"
            elif "DECREASING" in directions:
                primary_dir = "DECREASING"
            elif "INCREASING" in directions:
                primary_dir = "INCREASING"
            elif "VOLATILE" in directions:
                primary_dir = "VOLATILE"
        elif "VOLATILE" in directions:
            primary_dir = "VOLATILE"

        headline = f"{d_display} {primary_dir.title()} Trajectory"
        narrative = " ".join(summaries)
        cited = [
            f"{t.metric_name}: {t.current_value} (7d delta: {t.delta_7d})"
            for t in domain_trends
            if t.delta_7d is not None
        ]

        return DomainTrendExplanation(
            domain=domain,
            domain_display_name=d_display,
            headline=headline,
            narrative=narrative,
            trajectory_direction=primary_dir,
            is_meaningful_shift=has_meaningful,
            cited_metrics=cited,
        )

    def _format_metric_val(
        self, metric_key: str, snapshot: DailyFacilitySnapshot
    ) -> str:
        """Format current snapshot metric with appropriate unit."""
        if metric_key == "current_census":
            return f"{snapshot.census.current_census} guests"
        elif metric_key == "occupancy_rate_pct":
            return f"{snapshot.census.occupancy_rate_pct}%"
        elif metric_key == "net_flow":
            return f"{snapshot.admissions_discharges.net_flow:+} guests"
        elif metric_key == "average_los_days":
            return f"{snapshot.length_of_stay.average_los_days} days"
        elif metric_key == "hppd_actual":
            return f"{snapshot.staffing.hppd_actual} HPPD"
        elif metric_key == "open_shifts_count":
            return f"{snapshot.staffing.open_shifts_count} open shifts"
        elif metric_key == "agency_staff_pct":
            return f"{snapshot.staffing.agency_staff_pct}%"
        elif metric_key == "treatment_completion_rate_pct":
            return f"{snapshot.therapy.treatment_completion_rate_pct}%"
        elif metric_key == "expiring_authorizations_48h":
            return f"{snapshot.payer_auth.expiring_authorizations_48h} authorizations"
        elif metric_key == "dining_satisfaction_score":
            return f"{snapshot.hospitality.dining_satisfaction_score} pts"
        elif metric_key == "guest_satisfaction_nps":
            return f"{snapshot.hospitality.guest_satisfaction_nps} NPS"
        elif metric_key == "readmission_rate_30d_pct":
            return f"{snapshot.hospital_transfers.readmission_rate_30d_pct}%"
        elif metric_key == "acute_transfers_this_week":
            return f"{snapshot.hospital_transfers.acute_transfers_this_week} transfers"
        return "N/A"
