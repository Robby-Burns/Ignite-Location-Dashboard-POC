"""Facility Brief Agent for synthesizing concise, non-technical executive briefs (Story 3.1, AC-3.1.1)."""

from __future__ import annotations

from src.agent.attention_agent import FacilityAttentionAgent
from src.agent.llm_client import LLMClient
from src.agent.positive_agent import FacilityPositiveHighlightAgent
from src.agent.recommendation_agent import FacilityRecommendationAgent
from src.agent.state_agent import NumericalGroundingReconciler
from src.analytics.attention_areas import evaluate_attention_areas
from src.analytics.briefing import (
    FacilityBriefReport,
    synthesize_deterministic_facility_brief,
)
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.positive_highlights import evaluate_positive_highlights
from src.analytics.recommendations import generate_deterministic_recommendations
from src.analytics.trends import calculate_historical_trends
from src.mcp.client import MockDomoMCPClient


class FacilityBriefAgent:
    """Synthesizes human-readable, plain-language facility operational briefs."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.mcp_client = mcp_client
        self.llm_client = llm_client or LLMClient()
        self.positive_agent = FacilityPositiveHighlightAgent(
            mcp_client=mcp_client, llm_client=self.llm_client
        )
        self.attention_agent = FacilityAttentionAgent(
            mcp_client=mcp_client, llm_client=self.llm_client
        )
        self.recommendation_agent = FacilityRecommendationAgent(
            mcp_client=mcp_client, llm_client=self.llm_client
        )
        self.reconciler = NumericalGroundingReconciler()

    async def generate_facility_brief(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
        days_history: int = 30,
    ) -> FacilityBriefReport:
        """Generate a complete executive Facility Brief report."""
        # 1. Fetch snapshot from Mock Domo MCP
        snapshot = self.mcp_client.get_facility_snapshot(
            facility_id=facility_id, scenario=scenario
        )

        # 2. Lookup facility metadata
        facility_name = facility_id.replace("-", " ").title()
        if not facility_name.startswith("Ignite"):
            facility_name = f"Ignite Medical Resort {facility_name}"
        location = "Midwest / Chicago Metro"
        facilities = self.mcp_client.list_facilities()
        for fac in facilities:
            if fac.facility_id == facility_id:
                facility_name = fac.facility_name
                location = fac.location_region
                break

        # 3. Run deterministic calculations
        history = self.mcp_client.get_facility_history(
            facility_id=facility_id, days_history=days_history, scenario=scenario
        )
        calc_result = calculate_facility_metrics(snapshot, history, scenario=scenario)
        trends = calculate_historical_trends(snapshot, history, scenario=scenario)

        # 4. Generate upstream deterministic intelligence directly without redundant LLM calls
        positive_summary = evaluate_positive_highlights(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            trends=trends,
        )
        attention_summary = evaluate_attention_areas(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            calculations=calc_result,
            trends=trends,
        )
        rec_summary = generate_deterministic_recommendations(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            calculations=calc_result,
            trends=trends,
            attention_summary=attention_summary,
        )

        # 5. Synthesize deterministic brief
        brief = synthesize_deterministic_facility_brief(
            snapshot=snapshot,
            calculations=calc_result,
            positive_results=positive_summary,
            attention_results=attention_summary,
            recommendation_results=rec_summary,
            facility_name=facility_name,
            location=location,
            scenario=scenario,
        )

        return brief
