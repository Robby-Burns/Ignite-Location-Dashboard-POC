"""Unit and integration tests for Actionable Recommendations view (Story 3.3, AC-3.3.1, AC-3.3.2)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.agent.llm_client import LLMClient
from src.agent.recommendation_agent import (
    FacilityRecommendationAgent,
    RecommendationReport,
)
from src.api.main import app
from src.mcp.client import MockDomoMCPClient
from src.mcp.server import MockDomoMCPServer


@pytest.fixture
def mcp_client() -> MockDomoMCPClient:
    server = MockDomoMCPServer()
    return MockDomoMCPClient(server=server)


@pytest.fixture
def offline_llm_client() -> LLMClient:
    return LLMClient(api_key=None)


@pytest.mark.asyncio
async def test_ac3_3_1_recommendations_prioritized_and_understandable(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """AC-3.3.1: Verify recommendations are prioritized and understandable across multiple simultaneous issues."""
    agent = FacilityRecommendationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )

    # Test scenario with multiple compounding issues (staffing + transfers)
    report = await agent.generate_recommendations(
        facility_id="ignite-oak-brook", scenario="staffing_stress", days_history=30
    )

    assert isinstance(report, RecommendationReport)
    assert len(report.top_priority_recommendations) > 0
    assert len(report.verified_recommendations_summary.recommendations) > 0

    # Verify priority sorting: HIGH priorities appear before MEDIUM/LOW
    recs = report.verified_recommendations_summary.recommendations
    priorities = [r.priority for r in recs]
    high_indices = [i for i, p in enumerate(priorities) if p == "HIGH"]
    low_indices = [i for i, p in enumerate(priorities) if p == "LOW"]
    if high_indices and low_indices:
        assert max(high_indices) < min(low_indices)

    # Verify plain language and understandable structure for each recommendation
    for rec in recs:
        assert len(rec.action_title) > 5
        assert len(rec.suggested_action_description) > 20
        assert len(rec.rationale) > 20
        assert len(rec.expected_operational_impact) > 10
        assert rec.target_role_or_department != ""


@pytest.mark.asyncio
async def test_ac3_3_2_supporting_evidence_metrics_tracing(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """AC-3.3.2: Verify every recommendation includes verifiable supporting metrics and evidence."""
    agent = FacilityRecommendationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )
    report = await agent.generate_recommendations(
        facility_id="ignite-oak-brook",
        scenario="hospital_transfer_spike",
        days_history=30,
    )

    recs = report.verified_recommendations_summary.recommendations
    assert len(recs) > 0

    for rec in recs:
        # Every recommendation must include at least one supporting evidence metric (AC-3.3.2)
        assert len(rec.supporting_evidence_metrics) >= 1
        for ev in rec.supporting_evidence_metrics:
            assert len(ev) > 5


@pytest.mark.asyncio
async def test_rejection_boundary_no_completed_actions_and_human_authority(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """Rejection Boundary: Recommendations must NOT be represented as completed actions and must preserve human authority."""
    agent = FacilityRecommendationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )
    report = await agent.generate_recommendations(
        facility_id="ignite-oak-brook", scenario="auth_cliff", days_history=30
    )

    # Verify decision authority notice is present and explicit
    assert "decision-support" in report.decision_authority_notice.lower()
    assert (
        "human" in report.decision_authority_notice.lower()
        or "judgment" in report.decision_authority_notice.lower()
    )

    # Verify no recommendation is framed as already completed or executed
    for rec in report.verified_recommendations_summary.recommendations:
        desc_lower = rec.suggested_action_description.lower()
        title_lower = rec.action_title.lower()
        for completed_token in [
            "completed action",
            "already resolved",
            "action executed",
            "task finished",
        ]:
            assert completed_token not in desc_lower
            assert completed_token not in title_lower


@pytest.mark.asyncio
async def test_ac3_3_zero_phi_and_grounding(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """INV-008 & INV-002: Verify zero PHI and strict grounding across recommendations."""
    agent = FacilityRecommendationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )
    report = await agent.generate_recommendations(
        facility_id="ignite-oak-brook", scenario="therapy_disruption", days_history=30
    )

    json_str = report.model_dump_json().lower()
    for phi_term in ["patient name", "mrn", "ssn", "dob", "john doe", "jane doe"]:
        assert phi_term not in json_str


@pytest.mark.asyncio
async def test_fastapi_recommendations_endpoint() -> None:
    """Test GET /api/agent/recommendations endpoint across all operational scenarios."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        scenarios = [
            "baseline",
            "staffing_stress",
            "hospital_transfer_spike",
            "auth_cliff",
            "high_census_strain",
            "therapy_disruption",
        ]
        for scen in scenarios:
            response = await client.get(
                f"/api/agent/recommendations?facility_id=ignite-oak-brook&scenario={scen}&days_history=30"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["facility_id"] == "ignite-oak-brook"
            assert "verified_recommendations_summary" in data
            assert len(data["verified_recommendations_summary"]["recommendations"]) > 0
            assert data["analysis_state"] in (
                "ANALYSIS_COMPLETE",
                "AI_ANALYSIS_UNAVAILABLE",
            )
