"""Facility Positive Performance Agent for Story 2.3 — Identify Positive Performance.

Identifies, explains, and synthesizes operational areas meeting or exceeding targets,
positive historical momentum, and standout achievements for leadership recognition and operational replication.
Enforces strict numerical grounding (INV-002, AC-2.1.2) and transparent Spec §8 offline fallbacks.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.agent.state_agent import NumericalGroundingReconciler
from src.analytics.positive_highlights import (
    FacilityPositiveHighlightsSummary,
    evaluate_positive_highlights,
)
from src.analytics.trends import (
    FacilityTrendCalculations,
    calculate_historical_trends,
)
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient
from src.models.facility import DailyFacilitySnapshot


class StandupRecognitionNote(BaseModel):
    """Actionable recognition item for morning standup and team huddles."""

    domain: str = Field(..., description="Operational department or domain")
    team_or_role: str = Field(
        ..., description="Target team or operational role recognized"
    )
    achievement_headline: str = Field(..., description="What the team achieved")
    talking_point: str = Field(
        ...,
        description="Non-technical recognition bullet for leadership to speak at standup",
    )


class PositivePerformanceReport(BaseModel):
    """Complete plain-language positive performance and highlight report (Story 2.3)."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Facility name")
    analysis_date: str = Field(..., description="Snapshot date of analysis")
    scenario: str = Field(default="baseline", description="Evaluated scenario")
    analysis_state: Literal["ANALYSIS_COMPLETE", "AI_ANALYSIS_UNAVAILABLE"] = Field(
        default="ANALYSIS_COMPLETE", description="Explicit analysis state per Spec §8"
    )
    executive_highlights_summary: str = Field(
        ...,
        description="Executive overview of top operational achievements and positive momentum",
    )
    key_achievements: list[str] = Field(
        default_factory=list,
        description="Top bulleted achievements grounded in verified data",
    )
    standup_recognition_notes: list[StandupRecognitionNote] = Field(
        default_factory=list,
        description="Specific recognition talking points for morning standups and department leaders",
    )
    replication_insights: str = Field(
        ...,
        description="Operational practices and strengths that should be sustained or replicated across shifts",
    )
    verified_highlights: FacilityPositiveHighlightsSummary = Field(
        ...,
        description="Deterministic positive highlight computations and benchmark comparisons",
    )
    data_limitations_and_uncertainty: str = Field(
        default="Positive performance highlights are grounded strictly in verified snapshot and trend data.",
        description="Explicit disclosure of data boundaries (INV-004, INV-005)",
    )
    audit_receipt: LLMExecutionReceipt = Field(
        ..., description="LLM execution and verification receipt"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of report generation",
    )


SYSTEM_PROMPT_POSITIVE_HIGHLIGHTS = """You are an executive operational decision support agent for Ignite Medical Resorts.
Your objective is to identify, explain, and celebrate genuine operational achievements, targets met/exceeded, and positive trajectory improvements (AC-2.3.1, AC-2.3.2).

Rules and Invariants (Strictly Enforced):
1. AUTHENTIC HIGHLIGHTS ONLY: Highlight ONLY operational areas that genuinely meet or exceed targets or show positive trajectory improvements. DO NOT invent false praise for struggling domains.
2. ZERO INVENTION & NUMERICAL GROUNDING (INV-002, AC-2.1.2): Every number, metric, percentage, or delta mentioned MUST match the provided verified highlights and snapshot metrics.
3. BALANCED REPORTING: Praise authentic successes without obscuring operational reality.
4. NO REAL PHI (INV-008): Only aggregate operational metrics are cited; no patient names or identifiers.
5. NO HARDCODED SCENARIOS (INV-001): Base your assessment strictly on the dynamic metrics and verified highlights provided.

Return your explanation in valid JSON matching this exact structure:
{
  "executive_highlights_summary": "3-4 sentence leadership summary celebrating key facility achievements and momentum.",
  "key_achievements": [
    "...",
    "..."
  ],
  "standup_recognition_notes": [
    {
      "domain": "nursing",
      "team_or_role": "Nursing & Clinical Team",
      "achievement_headline": "...",
      "talking_point": "..."
    }
  ],
  "replication_insights": "2-3 sentences explaining operational practices and habits to sustain across shifts and departments."
}
"""


class FacilityPositiveHighlightAgent:
    """Agent that identifies and synthesizes positive operational performance and achievements for leadership."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def identify_positive_performance(
        self,
        facility_id: str,
        scenario: str = "baseline",
        days_history: int = 30,
    ) -> PositivePerformanceReport:
        """Retrieve facility data, compute deterministic positive highlights, and generate leadership recognition report."""
        facility_name = facility_id.replace("-", " ").title()

        # 1. Retrieve data via MCP
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
                    f"Cannot evaluate positive highlights for facility '{facility_id}': data unavailable."
                ) from e
            raise

        # 2. Compute verified deterministic trends and positive highlights
        trends = calculate_historical_trends(
            snapshot, history_series, scenario=scenario
        )
        positive_summary = evaluate_positive_highlights(
            snapshot=snapshot,
            history=history_series,
            scenario=scenario,
            trends=trends,
        )

        # 3. Formulate prompt containing verified facts and highlights
        user_prompt = self._build_positive_prompt(snapshot, positive_summary, trends)

        # 4. Execute LLM call with structured output
        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=SYSTEM_PROMPT_POSITIVE_HIGHLIGHTS,
            user_prompt=user_prompt,
            response_schema_name="PositivePerformanceReport",
        )

        # 5. Build ground truth numbers for reconciliation
        ground_truth = self._build_ground_truth_numbers(
            snapshot, positive_summary, trends
        )
        reconciled_discrepancies: list[str] = []

        # 6. Check if AI interpretation is available (Spec §8)
        if llm_output is None or not receipt.is_live_call:
            # Explicit AI_ANALYSIS_UNAVAILABLE state per Spec §8
            analysis_state = "AI_ANALYSIS_UNAVAILABLE"
            if positive_summary.total_highlights_count == 0:
                exec_summary = (
                    f"{facility_name} currently has no operational indicators meeting positive highlight criteria. "
                    f"Operational focus should center on resolving active deficits across departments. "
                    f"(AI interpretation is unavailable; displaying validated deterministic highlights per Spec §8)."
                )
            else:
                strong_str = ", ".join(
                    [
                        d.replace("_", " ").title()
                        for d in positive_summary.strongest_domains
                    ]
                )
                exec_summary = (
                    f"{facility_name} exhibits {positive_summary.total_highlights_count} positive operational highlights meeting or exceeding targets "
                    f"across {strong_str}. "
                    f"(AI interpretation is unavailable; displaying validated deterministic highlights per Spec §8)."
                )
            key_achievements = [
                hl.evidence_statement for hl in positive_summary.highlights[:5]
            ]
            standup_notes = self._build_deterministic_standup_notes(positive_summary)
            replication = "Maintain effective scheduling discipline, proactive clinical triage, and attentive guest service across all shifts."
            limitations = "AI narrative synthesis is offline. Positive highlights are derived strictly from deterministic benchmark and threshold calculations."
        else:
            # AI Analysis returned: Perform numerical grounding reconciliation (AC-2.1.2, INV-002)
            analysis_state = "ANALYSIS_COMPLETE"
            raw_exec = llm_output.get("executive_highlights_summary", "")
            default_exec = (
                f"{facility_name} demonstrates {positive_summary.total_highlights_count} verified operational highlights."
                if positive_summary.total_highlights_count > 0
                else f"{facility_name} currently has no operational indicators meeting positive highlight criteria."
            )
            exec_summary, is_exec_valid = NumericalGroundingReconciler.reconcile_text(
                raw_exec, ground_truth, default_exec
            )
            if not is_exec_valid:
                reconciled_discrepancies.append(
                    "Executive highlights summary contained unverified figures and was reconciled."
                )

            # Reconcile key achievements
            raw_achievements = llm_output.get("key_achievements", [])
            valid_achievements = []
            for ach in raw_achievements:
                valid_ach, is_ach_valid = NumericalGroundingReconciler.reconcile_text(
                    ach, ground_truth, ""
                )
                if is_ach_valid and valid_ach:
                    valid_achievements.append(valid_ach)
            if not valid_achievements:
                valid_achievements = [
                    hl.evidence_statement for hl in positive_summary.highlights[:5]
                ]
            key_achievements = valid_achievements

            # Reconcile standup recognition notes (reconcile both talking_point and achievement_headline)
            raw_standup = llm_output.get("standup_recognition_notes", [])
            valid_standup_notes = []
            for sn in raw_standup:
                raw_head = sn.get("achievement_headline", "Operational Achievement")
                valid_head, is_head_valid = NumericalGroundingReconciler.reconcile_text(
                    raw_head, ground_truth, "Operational Achievement"
                )
                raw_point = sn.get("talking_point", "")
                valid_point, is_point_valid = (
                    NumericalGroundingReconciler.reconcile_text(
                        raw_point, ground_truth, ""
                    )
                )
                if is_point_valid and valid_point:
                    valid_standup_notes.append(
                        StandupRecognitionNote(
                            domain=sn.get("domain", "operations"),
                            team_or_role=sn.get("team_or_role", "Facility Team"),
                            achievement_headline=valid_head
                            if is_head_valid
                            else "Operational Achievement",
                            talking_point=valid_point,
                        )
                    )
            if not valid_standup_notes:
                valid_standup_notes = self._build_deterministic_standup_notes(
                    positive_summary
                )
            standup_notes = valid_standup_notes

            raw_rep = llm_output.get(
                "replication_insights",
                "Sustain standard operating procedures and interdisciplinary communication.",
            )
            valid_rep, _ = NumericalGroundingReconciler.reconcile_text(
                raw_rep,
                ground_truth,
                "Sustain standard operating procedures and interdisciplinary communication.",
            )
            replication = valid_rep

            limitations = "Positive performance highlights are grounded strictly in verified snapshot and trend data."
            if reconciled_discrepancies:
                limitations += (
                    f" [Reconciliation Notice: {'; '.join(reconciled_discrepancies)}]"
                )

        return PositivePerformanceReport(
            facility_id=facility_id,
            facility_name=facility_name,
            analysis_date=snapshot.snapshot_date.isoformat(),
            scenario=scenario,
            analysis_state=analysis_state,
            executive_highlights_summary=exec_summary,
            key_achievements=key_achievements,
            standup_recognition_notes=standup_notes,
            replication_insights=replication,
            verified_highlights=positive_summary,
            data_limitations_and_uncertainty=limitations,
            audit_receipt=receipt,
        )

    def _build_ground_truth_numbers(
        self,
        snapshot: DailyFacilitySnapshot,
        positive_summary: FacilityPositiveHighlightsSummary,
        trends: FacilityTrendCalculations,
    ) -> set[float]:
        """Collect all verified numbers across snapshot, positive highlights, and trend calculations."""
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

        # Highlight numbers
        add_num(positive_summary.total_highlights_count)
        for hl in positive_summary.highlights:
            add_num(hl.current_value)
            add_num(hl.benchmark_or_target_value)

        # Trend numbers
        for t in trends.trends.values():
            add_num(t.current_value)
            add_num(t.value_7d_ago)
            add_num(t.value_14d_ago)
            add_num(t.delta_7d)
            add_num(t.pct_change_7d)

        return numbers

    def _build_positive_prompt(
        self,
        snapshot: DailyFacilitySnapshot,
        positive_summary: FacilityPositiveHighlightsSummary,
        trends: FacilityTrendCalculations,
    ) -> str:
        """Construct grounded prompt containing verified highlights and benchmark achievements."""
        hl_lines = []
        for hl in positive_summary.highlights:
            hl_lines.append(
                f"- [{hl.domain.upper()}] {hl.title}: current={hl.current_value} {hl.unit} "
                f"(target/benchmark={hl.benchmark_or_target_value} {hl.unit}, category={hl.category}, strength={hl.strength}). "
                f"Evidence: {hl.evidence_statement}"
            )

        prompt_dict = {
            "facility_id": snapshot.facility_id,
            "facility_name": snapshot.facility_id.replace("-", " ").title(),
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "scenario": positive_summary.scenario,
            "total_positive_highlights_count": positive_summary.total_highlights_count,
            "strongest_domains": positive_summary.strongest_domains,
            "verified_highlights": hl_lines,
            "meaningful_historical_shifts": trends.meaningful_shifts,
        }
        return (
            "Analyze and synthesize positive operational highlights for this facility based strictly on the verified achievements below:\n\n"
            + json.dumps(prompt_dict, indent=2)
        )

    def _build_deterministic_standup_notes(
        self,
        positive_summary: FacilityPositiveHighlightsSummary,
    ) -> list[StandupRecognitionNote]:
        """Generate deterministic standup recognition talking points without LLM."""
        notes = []
        for hl in positive_summary.highlights[:4]:
            role_map = {
                "census": "Intake & Admissions Team",
                "admissions_discharges": "Discharge Planning & Admissions Team",
                "length_of_stay": "Care Management Team",
                "staffing": "Nursing Leadership & Staff",
                "therapy": "Rehabilitation & Therapy Team",
                "payer_auth": "Case Management & Billing Team",
                "hospitality": "Culinary & Guest Services Team",
                "hospital_transfers": "Clinical Triage & Nursing Team",
            }
            team = role_map.get(hl.domain, "Facility Operations Team")
            notes.append(
                StandupRecognitionNote(
                    domain=hl.domain,
                    team_or_role=team,
                    achievement_headline=hl.title,
                    talking_point=f"Great job to the {team}: {hl.evidence_statement}",
                )
            )
        return notes
