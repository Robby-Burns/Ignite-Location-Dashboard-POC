"""Unified Facility Operational Decision Agent.

Implements the single structured analysis architecture:
Facility Data (Mock Domo MCP)
  → Deterministic Python Analytics (Metrics, Trends, Deficits, Correlations, Highlights, Recs)
  → Single Structured LLM Interpretation Call (Gemini 2.5 Flash Lite)
  → Numerical Grounding Reconciliation
  → Unified Structured Output consumed directly by UI.

Separation of Responsibilities:
- Python owns the facts (exact calculations, thresholds, variances, percentages, trends).
- LLM owns the human-facing interpretation (what's happening, why it matters, what's driving it,
  what you could consider, why suggested, what we could learn, dynamic suggested questions).
- No hardcoded scenario → finding or recommendation mappings.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.agent.state_agent import NumericalGroundingReconciler
from src.analytics.attention_areas import (
    AttentionAreaItem,
    FacilityAttentionSummary,
    evaluate_attention_areas,
)
from src.analytics.calculations import (
    FacilityCalculations,
    calculate_facility_metrics,
)
from src.analytics.positive_highlights import (
    FacilityPositiveHighlightsSummary,
    evaluate_positive_highlights,
)
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
from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries


class UnifiedFindingRecommendation(BaseModel):
    """Advisory recommendation for a finding."""

    consider: str = Field(
        ...,
        description="Practical, advisory next step for leadership review (e.g. 'Consider reviewing...')",
    )
    whySuggested: str = Field(
        ..., description="Clinical, financial, or operational rationale"
    )
    role: str = Field(
        ..., description="Responsible facility department or leadership role"
    )
    horizon: str = Field(
        ..., description="Time horizon (e.g. 'Immediate (24h)', 'Short-term (7d)')"
    )


class UnifiedFindingEvidence(BaseModel):
    """Single evidence metric item."""

    label: str = Field(..., description="Metric label")
    value: str = Field(..., description="Formatted value with units")


class UnifiedAttentionFinding(BaseModel):
    """Full operational finding requiring attention with deep LLM interpretation."""

    id: str = Field(..., description="Unique finding ID")
    title: str = Field(..., description="Concise finding headline")
    domain: str = Field(..., description="Operational domain key")
    domainDisplayName: str = Field(..., description="Human-friendly domain name")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        ..., description="Severity classification"
    )
    metricValue: str = Field(..., description="Current formatted metric value")
    metricSub: str = Field(..., description="Comparison subtitle vs target")
    whatsHappening: str = Field(
        ..., description="Plain-language description of observed condition"
    )
    whyItMatters: str = Field(
        ..., description="Operational significance and potential risk"
    )
    driving: list[str] = Field(
        default_factory=list,
        description="Contributing domains or root cause factors supported by data",
    )
    isCompound: bool = Field(
        default=False, description="Whether this involves multi-domain compound risk"
    )
    recommendation: UnifiedFindingRecommendation | None = Field(
        default=None, description="Advisory recommendation"
    )
    evidence: list[UnifiedFindingEvidence] = Field(
        default_factory=list, description="Ground truth evidence metrics"
    )


class UnifiedPositiveHighlight(BaseModel):
    """Positive operational highlight with deep LLM interpretation."""

    title: str = Field(..., description="Headline celebrating achievement")
    domain: str = Field(..., description="Operational domain key")
    domain_display_name: str = Field(..., description="Human-friendly domain name")
    category: str = Field(
        default="TARGET_MET", description="Positive category classification"
    )
    metric_value: str = Field(..., description="Current formatted metric value")
    metric_sub: str = Field(..., description="Comparison subtitle vs benchmark")
    plain_language_description: str = Field(
        ..., description="Plain-language overview of the achievement"
    )
    supporting_metric: str = Field(..., description="Formatted primary evidence metric")
    significance: str = Field(
        ..., description="Why this positive performance matters to facility success"
    )
    whats_happening: str = Field(
        ..., description="Detailed explanation of what is going well"
    )
    why_it_matters: str = Field(
        ..., description="Operational and patient benefit of this result"
    )
    whats_driving_it: str = Field(
        ...,
        description="Observed factors driving performance, or explicit note that cause cannot be determined from data alone",
    )
    what_we_could_learn: str = Field(
        ...,
        description="Practical insights leadership can preserve or replicate across shifts",
    )
    supporting_metrics: list[str] = Field(
        default_factory=list, description="List of supporting evidence strings"
    )


class UnifiedFollowUpQuestion(BaseModel):
    """Dynamically generated suggested follow-up question."""

    question_id: str = Field(..., description="Unique question ID")
    question_text: str = Field(
        ..., description="Practical question a facility leader might ask"
    )
    related_domain: str = Field(
        ..., description="Primary operational domain related to the question"
    )
    context_summary: str = Field(
        ..., description="Why this question is relevant to the current data"
    )
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        default="MEDIUM", description="Urgency priority"
    )


class UnifiedVitalMetric(BaseModel):
    """Vital operational indicator card."""

    metric_name: str = Field(..., description="Metric key")
    label: str = Field(..., description="Display label")
    formatted_value: str = Field(..., description="Formatted value")
    subtitle: str = Field(..., description="Context / target subtitle")
    status: Literal["POSITIVE", "NEUTRAL", "ATTENTION", "CRITICAL"] = Field(
        default="NEUTRAL", description="Status rating"
    )
    trend: Literal["UP", "DOWN", "STABLE"] = Field(
        default="STABLE", description="Trend direction"
    )


class UnifiedFacilityAnalysisResponse(BaseModel):
    """Complete, unified operational analysis response consumed directly by the UI."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Human-friendly facility name")
    scenario: str = Field(default="baseline", description="Operational scenario name")
    report_date: str = Field(..., description="Snapshot date (ISO format)")
    overall_status: Literal["HEALTHY", "WATCH", "NEEDS_ATTENTION", "CRITICAL"] = Field(
        default="HEALTHY", description="Overall operational health status"
    )
    status_label: str = Field(..., description="Executive status banner label")
    executive_summary: str = Field(
        ..., description="Concise executive summary of current operational state"
    )
    vitals: list[UnifiedVitalMetric] = Field(
        default_factory=list, description="Deterministic vital metric cards"
    )
    findings: list[UnifiedAttentionFinding] = Field(
        default_factory=list, description="Operational findings requiring attention"
    )
    positive_highlights: list[UnifiedPositiveHighlight] = Field(
        default_factory=list, description="Operational areas meeting or exceeding targets"
    )
    suggested_questions: list[UnifiedFollowUpQuestion] = Field(
        default_factory=list, description="Dynamic suggested questions from analysis"
    )
    analysis_state: Literal["LLM_ANALYSIS", "DETERMINISTIC_FALLBACK"] = Field(
        default="LLM_ANALYSIS", description="Whether analysis was synthesized by LLM or fallback"
    )
    fallback_reason: str | None = Field(
        default=None, description="Reason if fallback was triggered"
    )
    audit_receipt: LLMExecutionReceipt = Field(
        ..., description="LLM execution and verification receipt"
    )
    data_freshness: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Data capture timestamp",
    )
    limitations_disclaimer: str = Field(
        default="Decision Support Only: All findings and recommendations are advisory suggestions for facility leadership review. Clinical and administrative decisions remain with authorized facility leadership.",
        description="Transparency disclaimer",
    )


UNIFIED_ANALYSIS_SYSTEM_PROMPT = """You are the Ignite Operational Decision Support Agent for Ignite Medical Resorts.
Translate verified facility telemetry into concise, actionable leadership decision-support insights.

ARCHITECTURAL PRINCIPLES:
1. PYTHON OWNS THE FACTS: All numbers, metrics, variances, and threshold breaches provided below are exact and verified. Do not calculate, estimate, or alter numbers.
2. EVIDENCE-BASED REASONING:
   - OBSERVED: What data directly proves.
   - INTERPRETATION: Concise operational explanation.
   - UNKNOWN: If cause is not in data, explicitly state data is insufficient.
3. ADVISORY FRAMING: Frame suggestions as options for leadership review (e.g. "Consider reviewing...").
4. STRICT NUMERICAL GROUNDING: Every number you cite MUST exist in the verified input facts.
5. CONCISE & PUNCHY: Keep each explanation to 1-2 direct sentences (max 25 words per field).

Return a JSON object conforming strictly to this schema:
{
  "executive_summary": "1-2 sentence executive summary of current facility state and primary priorities.",
  "findings_interpretations": [
    {
      "id": "item_id from input",
      "whats_happening": "1 concise sentence describing the floor condition.",
      "why_it_matters": "1 concise sentence explaining clinical, regulatory, or operational risk.",
      "whats_driving_it": ["domain1"],
      "what_you_could_consider": "1 concise practical advisory suggestion for leadership review.",
      "why_suggested": "1 concise sentence rationale."
    }
  ],
  "positive_interpretations": [
    {
      "title": "title from input",
      "whats_happening": "1 concise sentence on what is going well.",
      "why_it_matters": "1 concise sentence on why this matters to facility success.",
      "whats_driving_it": "Observed driver or note that specific driver cannot be determined from data alone.",
      "what_we_could_learn": "1 concise sentence lesson to sustain or replicate."
    }
  ],
  "suggested_questions": [
    {
      "question_text": "Practical question to investigate current findings?",
      "related_domain": "staffing",
      "context_summary": "Why relevant based on current findings.",
      "priority": "HIGH"
    }
  ]
}
"""


class FacilityUnifiedAnalysisAgent:
    """Agent that performs complete facility analysis using a single unified structured LLM call with in-memory caching."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
        cache_ttl_seconds: float = 300.0,
    ) -> None:
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()
        self.reconciler = NumericalGroundingReconciler()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, UnifiedFacilityAnalysisResponse]] = {}

    def clear_cache(self, facility_id: str | None = None) -> None:
        """Clear in-memory cached analyses for a specific facility or all."""
        if facility_id:
            keys_to_remove = [
                k for k in self._cache if k.startswith(f"{facility_id}:")
            ]
            for k in keys_to_remove:
                self._cache.pop(k, None)
        else:
            self._cache.clear()

    async def analyze_facility(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
        days_history: int = 30,
        force_refresh: bool = False,
    ) -> UnifiedFacilityAnalysisResponse:
        """Execute end-to-end unified facility analysis with in-memory cache and 1 structured LLM call."""
        cache_key = f"{facility_id}:{scenario}:{days_history}"
        now = datetime.now(UTC).timestamp()

        # Check in-memory cache
        if not force_refresh and cache_key in self._cache:
            cached_time, cached_response = self._cache[cache_key]
            if (now - cached_time) < self.cache_ttl_seconds:
                return cached_response

        # 1. Retrieve raw data via Mock Domo MCP client
        try:
            snapshot = self.mcp_client.get_facility_snapshot(
                facility_id=facility_id, scenario=scenario
            )
            history = self.mcp_client.get_facility_history(
                facility_id=facility_id, days_history=days_history, scenario=scenario
            )
            facilities = self.mcp_client.list_facilities()
        except Exception as e:
            if "not found" in str(e).lower() or "unavailable" in str(e).lower():
                raise DatasetUnavailableError(
                    f"Cannot analyze facility '{facility_id}': data unavailable."
                ) from e
            raise

        facility_name = facility_id.replace("-", " ").title()
        if not facility_name.startswith("Ignite"):
            facility_name = f"Ignite Medical Resort {facility_name}"
        for fac in facilities:
            if fac.facility_id == facility_id:
                facility_name = fac.facility_name
                break

        # 2. Compute verified deterministic Python analytics across all 8 domains (1 ms)
        calcs: FacilityCalculations = calculate_facility_metrics(snapshot, history, scenario=scenario)
        trends: FacilityTrendCalculations = calculate_historical_trends(
            snapshot, history, scenario=scenario
        )
        attention_summary: FacilityAttentionSummary = evaluate_attention_areas(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            calculations=calcs,
            trends=trends,
        )
        rec_summary: FacilityRecommendationsSummary = generate_deterministic_recommendations(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            calculations=calcs,
            trends=trends,
            attention_summary=attention_summary,
        )
        pos_summary: FacilityPositiveHighlightsSummary = evaluate_positive_highlights(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            trends=trends,
        )

        # 3. Derive deterministic vitals and overall status
        vitals = self._build_deterministic_vitals(snapshot)
        overall_status, status_label = self._determine_overall_status(attention_summary)

        # 4. Build ground truth numbers for reconciliation
        ground_truth = NumericalGroundingReconciler.build_ground_truth_set(
            snapshot, calcs
        )
        self._augment_ground_truth(ground_truth, attention_summary, trends, pos_summary)

        # 5. Formulate concise input facts payload for the single LLM call
        user_prompt = self._build_unified_prompt(
            facility_name=facility_name,
            snapshot=snapshot,
            calcs=calcs,
            attention_summary=attention_summary,
            rec_summary=rec_summary,
            pos_summary=pos_summary,
            trends=trends,
        )

        # 6. Execute single structured LLM call
        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=UNIFIED_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema_name="UnifiedFacilityAnalysisResponse",
        )

        # 7. Check if LLM call succeeded or fallback needed
        if llm_output is None or not receipt.is_live_call:
            response = self._build_fallback_response(
                facility_id=facility_id,
                facility_name=facility_name,
                scenario=scenario,
                snapshot=snapshot,
                vitals=vitals,
                overall_status=overall_status,
                status_label=status_label,
                attention_summary=attention_summary,
                rec_summary=rec_summary,
                pos_summary=pos_summary,
                receipt=receipt,
                reason="Live LLM call was unavailable; displaying validated deterministic analysis.",
            )
            self._cache[cache_key] = (now, response)
            return response

        # 8. Reconcile LLM output against verified ground truth numbers
        response = self._build_reconciled_response(
            facility_id=facility_id,
            facility_name=facility_name,
            scenario=scenario,
            snapshot=snapshot,
            vitals=vitals,
            overall_status=overall_status,
            status_label=status_label,
            attention_summary=attention_summary,
            rec_summary=rec_summary,
            pos_summary=pos_summary,
            llm_output=llm_output,
            ground_truth=ground_truth,
            receipt=receipt,
        )
        self._cache[cache_key] = (now, response)
        return response

    def _determine_overall_status(
        self, attention_summary: FacilityAttentionSummary
    ) -> tuple[Literal["HEALTHY", "WATCH", "NEEDS_ATTENTION", "CRITICAL"], str]:
        """Determine overall operational health status deterministically."""
        high_attention_count = sum(
            1
            for item in attention_summary.attention_items
            if item.severity in ("HIGH", "CRITICAL")
        )
        total_attention_count = len(attention_summary.attention_items)
        compound_count = len(attention_summary.cross_domain_correlations)

        if compound_count > 0 or high_attention_count >= 2:
            return "CRITICAL", "Critical Operational Attention Required"
        elif high_attention_count == 1 or total_attention_count >= 2:
            return "NEEDS_ATTENTION", "Operational Attention Recommended"
        elif total_attention_count == 1:
            return "WATCH", "Operational Watch: Monitoring Key Indicators"
        else:
            return "HEALTHY", "Operations Stable and Meeting Benchmarks"

    def _build_deterministic_vitals(
        self, snapshot: DailyFacilitySnapshot
    ) -> list[UnifiedVitalMetric]:
        """Compute deterministic vital cards from snapshot."""
        c = snapshot.census
        ad = snapshot.admissions_discharges
        st = snapshot.staffing
        th = snapshot.therapy
        ho = snapshot.hospitality

        return [
            UnifiedVitalMetric(
                metric_name="occupancy_rate_pct",
                label="Occupancy Rate",
                formatted_value=f"{c.occupancy_rate_pct:.1f}%",
                subtitle=f"{c.current_census} / {c.total_capacity} Beds (Net: {ad.net_flow:+d})",
                status="POSITIVE" if c.occupancy_rate_pct >= 90.0 else "ATTENTION",
                trend="UP" if ad.net_flow > 0 else ("DOWN" if ad.net_flow < 0 else "STABLE"),
            ),
            UnifiedVitalMetric(
                metric_name="hppd_actual",
                label="Direct Care HPPD",
                formatted_value=f"{st.hppd_actual:.2f} hrs",
                subtitle=f"Target: {st.hppd_budgeted_target:.2f} ({st.open_shifts_count} Open Shifts)",
                status="POSITIVE" if st.hppd_actual >= st.hppd_budgeted_target else "ATTENTION",
                trend="STABLE" if st.hppd_actual >= st.hppd_budgeted_target else "DOWN",
            ),
            UnifiedVitalMetric(
                metric_name="agency_staff_pct",
                label="Agency Staffing",
                formatted_value=f"{st.agency_staff_pct:.1f}%",
                subtitle="Target: < 10.0% Internal Mix",
                status="POSITIVE" if st.agency_staff_pct <= 10.0 else "ATTENTION",
                trend="UP" if st.agency_staff_pct > 10.0 else "STABLE",
            ),
            UnifiedVitalMetric(
                metric_name="treatment_completion_rate_pct",
                label="Therapy Completion",
                formatted_value=f"{th.treatment_completion_rate_pct:.1f}%",
                subtitle=f"{th.patients_meeting_weekly_goals_pct:.1f}% Goals Met (Hold: {th.patients_on_therapy_hold})",
                status="POSITIVE" if th.treatment_completion_rate_pct >= 90.0 else "ATTENTION",
                trend="STABLE",
            ),
            UnifiedVitalMetric(
                metric_name="dining_satisfaction_score",
                label="Guest Dining Score",
                formatted_value=f"{ho.dining_satisfaction_score:.1f}%",
                subtitle=f"NPS: {ho.guest_satisfaction_nps:+.0f} (Target: > 85.0%)",
                status="POSITIVE" if ho.dining_satisfaction_score >= 85.0 else "ATTENTION",
                trend="UP" if ho.dining_satisfaction_score >= 90.0 else "STABLE",
            ),
        ]

    def _build_unified_prompt(
        self,
        facility_name: str,
        snapshot: DailyFacilitySnapshot,
        calcs: FacilityCalculations,
        attention_summary: FacilityAttentionSummary,
        rec_summary: FacilityRecommendationsSummary,
        pos_summary: FacilityPositiveHighlightsSummary,
        trends: FacilityTrendCalculations,
    ) -> str:
        """Construct a concise prompt containing key pre-computed facts for the LLM."""
        attention_payload = []
        for item in attention_summary.attention_items[:4]:
            attention_payload.append(
                {
                    "id": item.item_id,
                    "domain": item.domain,
                    "title": item.title,
                    "severity": item.severity,
                    "current_value": f"{item.current_value} {item.unit}",
                    "threshold": f"{item.threshold_or_target} {item.unit}",
                    "variance": f"{item.variance_or_deficit} {item.unit}",
                    "evidence_fact": item.evidence_statement,
                    "related_domains": item.related_domains,
                }
            )

        pos_payload = []
        for h in pos_summary.highlights[:3]:
            pos_payload.append(
                {
                    "domain": h.domain,
                    "title": h.title,
                    "current_value": f"{h.current_value} {h.unit}",
                    "target": f"{h.benchmark_or_target_value} {h.unit}",
                    "evidence_statement": h.evidence_statement,
                }
            )

        payload = {
            "facility_id": snapshot.facility_id,
            "facility_name": facility_name,
            "scenario": attention_summary.scenario,
            "active_attention_conditions": attention_payload,
            "positive_highlights": pos_payload,
            "top_shifts": trends.meaningful_shifts[:3],
        }

        return (
            "Analyze and interpret the verified operational telemetry below for facility leadership:\n"
            + json.dumps(payload, separators=(",", ":"))
        )

    def _augment_ground_truth(
        self,
        ground_truth: set[float],
        attention_summary: FacilityAttentionSummary,
        trends: FacilityTrendCalculations,
        pos_summary: FacilityPositiveHighlightsSummary,
    ) -> None:
        """Add all calculated numbers into ground truth set."""
        def add_num(val: Any) -> None:
            if val is not None and isinstance(val, (int, float)):
                f = round(float(val), 2)
                ground_truth.add(f)
                ground_truth.add(round(f, 1))
                ground_truth.add(round(f, 0))
                ground_truth.add(abs(f))
                ground_truth.add(round(abs(f), 1))

        for item in attention_summary.attention_items:
            add_num(item.current_value)
            add_num(item.threshold_or_target)
            add_num(item.variance_or_deficit)

        for h in pos_summary.highlights:
            add_num(h.current_value)
            add_num(h.benchmark_or_target_value)

        for t in trends.trends.values():
            add_num(t.current_value)
            add_num(t.value_7d_ago)
            add_num(t.delta_7d)
            add_num(t.pct_change_7d)

    def _format_metric_with_unit(self, val: float, unit: str) -> str:
        """Format metric number with unit."""
        if unit == "%":
            return f"{val:.1f}%"
        if unit == "HPPD":
            return f"{val:.2f} HPPD"
        if unit == "days":
            return f"{val:.1f} days"
        if unit in ("shifts", "patients", "transfers", "authorizations", "guests"):
            return f"{round(val)} {unit}"
        if unit:
            return f"{val:.1f} {unit}"
        return f"{val:.1f}"

    def _build_reconciled_response(
        self,
        facility_id: str,
        facility_name: str,
        scenario: str,
        snapshot: DailyFacilitySnapshot,
        vitals: list[UnifiedVitalMetric],
        overall_status: Literal["HEALTHY", "WATCH", "NEEDS_ATTENTION", "CRITICAL"],
        status_label: str,
        attention_summary: FacilityAttentionSummary,
        rec_summary: FacilityRecommendationsSummary,
        pos_summary: FacilityPositiveHighlightsSummary,
        llm_output: dict[str, Any],
        ground_truth: set[float],
        receipt: LLMExecutionReceipt,
    ) -> UnifiedFacilityAnalysisResponse:
        """Assemble reconciled response from LLM interpretation and verified Python facts."""
        # 1. Executive summary
        raw_exec = llm_output.get("executive_summary", "")
        default_exec = (
            f"{facility_name} is operating at {snapshot.census.occupancy_rate_pct:.1f}% occupancy with {snapshot.census.current_census} occupied beds. "
            f"Leadership review is focused on {len(attention_summary.attention_items)} active operational condition(s)."
            if attention_summary.attention_items
            else f"{facility_name} is operating stably across all domains with zero active deficits."
        )
        exec_summary, _ = NumericalGroundingReconciler.reconcile_text(
            raw_exec, ground_truth, default_exec
        )

        # 2. Findings interpretations
        findings_list = llm_output.get("findings_interpretations", [])
        findings_by_id = {f.get("id"): f for f in findings_list if f.get("id")}
        findings_by_domain = {f.get("domain"): f for f in findings_list if f.get("domain")}

        findings: list[UnifiedAttentionFinding] = []
        rec_by_evidence = {r.rationale: r for r in rec_summary.recommendations}

        for idx, item in enumerate(attention_summary.attention_items):
            cur_str = self._format_metric_with_unit(item.current_value, item.unit)
            target_str = self._format_metric_with_unit(item.threshold_or_target, item.unit)
            sub_str = f"{cur_str} vs {target_str} Target"

            llm_f = (
                findings_by_id.get(item.item_id)
                or findings_by_domain.get(item.domain)
                or (findings_list[idx] if idx < len(findings_list) else {})
            )
            raw_happening = llm_f.get("whats_happening", item.evidence_statement)
            raw_matters = llm_f.get("why_it_matters", item.operational_risk_summary)
            raw_driving = llm_f.get("whats_driving_it", item.related_domains)
            raw_consider = llm_f.get("what_you_could_consider", "")
            raw_why_sugg = llm_f.get("why_suggested", "")

            valid_happening, _ = NumericalGroundingReconciler.reconcile_text(
                raw_happening, ground_truth, item.evidence_statement
            )
            valid_matters, _ = NumericalGroundingReconciler.reconcile_text(
                raw_matters, ground_truth, item.operational_risk_summary
            )

            # Match or build recommendation
            matched_rec = rec_by_evidence.get(item.evidence_statement)
            default_consider = (
                matched_rec.suggested_action_description
                if matched_rec
                else f"Consider reviewing {item.domain_display_name} operational workflows."
            )
            default_why_sugg = (
                matched_rec.expected_operational_impact
                if matched_rec
                else f"Helps resolve {item.title} deficit and align with target standards."
            )
            default_role = (
                matched_rec.target_role_or_department
                if matched_rec
                else "Facility Operations Leadership"
            )
            default_horizon = (
                "Immediate (24h)"
                if item.severity in ("CRITICAL", "HIGH")
                else "Short-term (7d)"
            )

            valid_consider, _ = NumericalGroundingReconciler.reconcile_text(
                raw_consider, ground_truth, default_consider
            )
            valid_why_sugg, _ = NumericalGroundingReconciler.reconcile_text(
                raw_why_sugg, ground_truth, default_why_sugg
            )

            evidence_items = [
                UnifiedFindingEvidence(label=item.domain_display_name, value=cur_str),
                UnifiedFindingEvidence(label="Target", value=target_str),
            ]
            if item.variance_or_deficit:
                var_str = self._format_metric_with_unit(item.variance_or_deficit, item.unit)
                evidence_items.append(UnifiedFindingEvidence(label="Variance", value=var_str))

            findings.append(
                UnifiedAttentionFinding(
                    id=item.item_id,
                    title=item.title,
                    domain=item.domain,
                    domainDisplayName=item.domain_display_name,
                    severity=item.severity,
                    metricValue=cur_str,
                    metricSub=sub_str,
                    whatsHappening=valid_happening,
                    whyItMatters=valid_matters,
                    driving=raw_driving if isinstance(raw_driving, list) else item.related_domains,
                    isCompound=item.is_cross_domain_compound,
                    recommendation=UnifiedFindingRecommendation(
                        consider=valid_consider,
                        whySuggested=valid_why_sugg,
                        role=default_role,
                        horizon=default_horizon,
                    ),
                    evidence=evidence_items,
                )
            )

        # 3. Positive highlights interpretations
        pos_map = {
            p.get("title", ""): p for p in llm_output.get("positive_interpretations", [])
        }
        positive_highlights: list[UnifiedPositiveHighlight] = []

        for h in pos_summary.highlights[:6]:
            cur_str = self._format_metric_with_unit(h.current_value, h.unit)
            bench_str = self._format_metric_with_unit(h.benchmark_or_target_value, h.unit)
            target_label = "Prior Week" if h.category == "TRAJECTORY_IMPROVEMENT" else "Target"

            if h.unit == "%":
                diff = h.current_value - h.benchmark_or_target_value
                if h.category == "TRAJECTORY_IMPROVEMENT":
                    metric_sub = f"{cur_str} · +{diff:.1f}% vs prior week"
                elif diff >= 0:
                    metric_sub = f"{cur_str} · {abs(diff):.1f}% above target"
                else:
                    metric_sub = f"{cur_str} · {abs(diff):.1f}% below threshold"
            else:
                metric_sub = f"{cur_str} vs {target_label} {bench_str}"

            llm_pos = pos_map.get(h.title, {})
            raw_pos_happening = llm_pos.get("whats_happening", h.evidence_statement)
            raw_pos_matters = llm_pos.get("why_it_matters", h.operational_impact)
            raw_pos_driving = llm_pos.get("whats_driving_it", h.driving_factors)
            raw_pos_learn = llm_pos.get("what_we_could_learn", h.lessons_learned)

            valid_pos_happening, _ = NumericalGroundingReconciler.reconcile_text(
                raw_pos_happening, ground_truth, h.evidence_statement
            )
            valid_pos_matters, _ = NumericalGroundingReconciler.reconcile_text(
                raw_pos_matters, ground_truth, h.operational_impact
            )
            valid_pos_driving, _ = NumericalGroundingReconciler.reconcile_text(
                raw_pos_driving, ground_truth, h.driving_factors
            )
            valid_pos_learn, _ = NumericalGroundingReconciler.reconcile_text(
                raw_pos_learn, ground_truth, h.lessons_learned
            )

            positive_highlights.append(
                UnifiedPositiveHighlight(
                    title=h.title,
                    domain=h.domain,
                    domain_display_name=h.domain_display_name,
                    category=h.category,
                    metric_value=cur_str,
                    metric_sub=metric_sub,
                    plain_language_description=valid_pos_happening,
                    supporting_metric=f"{cur_str} ({target_label}: {bench_str})",
                    significance=valid_pos_matters,
                    whats_happening=valid_pos_happening,
                    why_it_matters=valid_pos_matters,
                    whats_driving_it=valid_pos_driving,
                    what_we_could_learn=valid_pos_learn,
                    supporting_metrics=h.supporting_metrics or [f"{h.domain_display_name}: {cur_str}"],
                )
            )

        # 4. Dynamic suggested questions
        raw_questions = llm_output.get("suggested_questions", [])
        suggested_questions: list[UnifiedFollowUpQuestion] = []

        for i, q in enumerate(raw_questions[:6]):
            q_text = q.get("question_text", "")
            if not q_text:
                continue
            suggested_questions.append(
                UnifiedFollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-{i + 1:02d}",
                    question_text=q_text,
                    related_domain=q.get("related_domain", "operations"),
                    context_summary=q.get("context_summary", ""),
                    priority=q.get("priority", "MEDIUM") if q.get("priority") in ("HIGH", "MEDIUM", "LOW") else "MEDIUM",
                )
            )

        if not suggested_questions:
            suggested_questions = self._build_deterministic_questions(
                attention_summary, rec_summary, facility_id
            )

        return UnifiedFacilityAnalysisResponse(
            facility_id=facility_id,
            facility_name=facility_name,
            scenario=scenario,
            report_date=snapshot.snapshot_date.isoformat(),
            overall_status=overall_status,
            status_label=status_label,
            executive_summary=exec_summary,
            vitals=vitals,
            findings=findings,
            positive_highlights=positive_highlights,
            suggested_questions=suggested_questions,
            analysis_state="LLM_ANALYSIS",
            fallback_reason=None,
            audit_receipt=receipt,
            data_freshness=snapshot.snapshot_date.isoformat(),
        )

    def _build_fallback_response(
        self,
        facility_id: str,
        facility_name: str,
        scenario: str,
        snapshot: DailyFacilitySnapshot,
        vitals: list[UnifiedVitalMetric],
        overall_status: Literal["HEALTHY", "WATCH", "NEEDS_ATTENTION", "CRITICAL"],
        status_label: str,
        attention_summary: FacilityAttentionSummary,
        rec_summary: FacilityRecommendationsSummary,
        pos_summary: FacilityPositiveHighlightsSummary,
        receipt: LLMExecutionReceipt,
        reason: str,
    ) -> UnifiedFacilityAnalysisResponse:
        """Generate complete validated deterministic fallback when LLM is unavailable."""
        c = snapshot.census
        if attention_summary.attention_items:
            top_concerns = [item.title for item in attention_summary.attention_items[:2]]
            exec_summary = (
                f"{facility_name} is operating at {c.occupancy_rate_pct:.1f}% occupancy with {c.current_census} occupied beds. "
                f"Primary operational attention is focused on {', '.join(top_concerns)}. "
                f"(Deterministic fallback: AI interpretation is offline per Spec §8)."
            )
        else:
            exec_summary = (
                f"{facility_name} is operating at {c.occupancy_rate_pct:.1f}% occupancy with zero active deficit conditions detected. "
                f"(Deterministic fallback: AI interpretation is offline per Spec §8)."
            )

        rec_by_evidence = {r.rationale: r for r in rec_summary.recommendations}
        findings: list[UnifiedAttentionFinding] = []

        for item in attention_summary.attention_items:
            cur_str = self._format_metric_with_unit(item.current_value, item.unit)
            target_str = self._format_metric_with_unit(item.threshold_or_target, item.unit)
            sub_str = f"{cur_str} vs {target_str} Target"

            matched_rec = rec_by_evidence.get(item.evidence_statement)
            consider = (
                matched_rec.suggested_action_description
                if matched_rec
                else f"Consider reviewing {item.domain_display_name} operational workflows."
            )
            why_sugg = (
                matched_rec.expected_operational_impact
                if matched_rec
                else f"Helps resolve {item.title} deficit and align with target standards."
            )
            role = (
                matched_rec.target_role_or_department
                if matched_rec
                else "Facility Operations Leadership"
            )
            horizon = (
                "Immediate (24h)"
                if item.severity in ("CRITICAL", "HIGH")
                else "Short-term (7d)"
            )

            evidence_items = [
                UnifiedFindingEvidence(label=item.domain_display_name, value=cur_str),
                UnifiedFindingEvidence(label="Target", value=target_str),
            ]

            findings.append(
                UnifiedAttentionFinding(
                    id=item.item_id,
                    title=item.title,
                    domain=item.domain,
                    domainDisplayName=item.domain_display_name,
                    severity=item.severity,
                    metricValue=cur_str,
                    metricSub=sub_str,
                    whatsHappening=item.evidence_statement,
                    whyItMatters=item.operational_risk_summary,
                    driving=item.related_domains,
                    isCompound=item.is_cross_domain_compound,
                    recommendation=UnifiedFindingRecommendation(
                        consider=consider,
                        whySuggested=why_sugg,
                        role=role,
                        horizon=horizon,
                    ),
                    evidence=evidence_items,
                )
            )

        positive_highlights: list[UnifiedPositiveHighlight] = []
        for h in pos_summary.highlights[:6]:
            cur_str = self._format_metric_with_unit(h.current_value, h.unit)
            bench_str = self._format_metric_with_unit(h.benchmark_or_target_value, h.unit)
            target_label = "Prior Week" if h.category == "TRAJECTORY_IMPROVEMENT" else "Target"

            if h.unit == "%":
                diff = h.current_value - h.benchmark_or_target_value
                metric_sub = f"{cur_str} · +{diff:.1f}% vs prior week" if h.category == "TRAJECTORY_IMPROVEMENT" else f"{cur_str} · {abs(diff):.1f}% above target"
            else:
                metric_sub = f"{cur_str} vs {target_label} {bench_str}"

            positive_highlights.append(
                UnifiedPositiveHighlight(
                    title=h.title,
                    domain=h.domain,
                    domain_display_name=h.domain_display_name,
                    category=h.category,
                    metric_value=cur_str,
                    metric_sub=metric_sub,
                    plain_language_description=h.evidence_statement,
                    supporting_metric=f"{cur_str} ({target_label}: {bench_str})",
                    significance=h.operational_impact,
                    whats_happening=h.evidence_statement,
                    why_it_matters=h.operational_impact,
                    whats_driving_it=h.driving_factors,
                    what_we_could_learn=h.lessons_learned,
                    supporting_metrics=h.supporting_metrics or [f"{h.domain_display_name}: {cur_str}"],
                )
            )

        questions = self._build_deterministic_questions(
            attention_summary, rec_summary, facility_id
        )

        return UnifiedFacilityAnalysisResponse(
            facility_id=facility_id,
            facility_name=facility_name,
            scenario=scenario,
            report_date=snapshot.snapshot_date.isoformat(),
            overall_status=overall_status,
            status_label=status_label,
            executive_summary=exec_summary,
            vitals=vitals,
            findings=findings,
            positive_highlights=positive_highlights,
            suggested_questions=questions,
            analysis_state="DETERMINISTIC_FALLBACK",
            fallback_reason=reason,
            audit_receipt=receipt,
            data_freshness=snapshot.snapshot_date.isoformat(),
        )

    def _build_deterministic_questions(
        self,
        attention_summary: FacilityAttentionSummary,
        rec_summary: FacilityRecommendationsSummary,
        facility_id: str,
    ) -> list[UnifiedFollowUpQuestion]:
        """Generate deterministic follow-up questions from verified attention areas."""
        questions: list[UnifiedFollowUpQuestion] = []
        counter = 1

        for item in attention_summary.attention_items[:4]:
            questions.append(
                UnifiedFollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-{counter:02d}",
                    question_text=f"What is driving the {item.title.lower()} and what are the primary risk factors?",
                    related_domain=item.domain,
                    context_summary=item.evidence_statement,
                    priority="HIGH" if item.severity in ("CRITICAL", "HIGH") else "MEDIUM",
                )
            )
            counter += 1

        for rec in rec_summary.recommendations[:2]:
            questions.append(
                UnifiedFollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-{counter:02d}",
                    question_text=f"What data supports the suggestion: {rec.action_title}?",
                    related_domain=rec.domain,
                    context_summary=rec.rationale,
                    priority=rec.priority,
                )
            )
            counter += 1

        if not questions:
            questions.append(
                UnifiedFollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-01",
                    question_text="What operational strengths are maintaining current benchmark stability?",
                    related_domain="census",
                    context_summary="No active deficit conditions detected across evaluated domains.",
                    priority="LOW",
                )
            )

        return questions
