"""Unit and integration tests for What It Means view (Story 3.2, AC-3.2.1, INV-003)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.agent.llm_client import LLMClient
from src.agent.trend_agent import (
    FacilityTrendExplanationAgent,
    FacilityTrendExplanationReport,
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
async def test_ac3_2_1_plain_language_metric_context(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """AC-3.2.1: Verify important metrics are accompanied by understandable context."""
    agent = FacilityTrendExplanationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )
    report = await agent.explain_facility_trends(
        facility_id="ignite-oak-brook", scenario="baseline", days_history=30
    )

    assert isinstance(report, FacilityTrendExplanationReport)
    assert "Ignite Oak Brook" in report.facility_name
    assert len(report.metric_explanations) >= 7

    # Verify key operational metrics have plain-language meaning and significance
    required_metrics = [
        "current_census",
        "hppd_actual",
        "agency_staff_pct",
        "treatment_completion_rate_pct",
        "dining_satisfaction_score",
        "acute_transfers_this_week",
        "expiring_authorizations_48h",
    ]
    for m_key in required_metrics:
        assert m_key in report.metric_explanations, f"Missing metric: {m_key}"
        detail = report.metric_explanations[m_key]
        assert len(detail.plain_language_meaning) > 15
        assert len(detail.operational_significance) > 15
        assert len(detail.benchmark_context) > 5


@pytest.mark.asyncio
async def test_inv003_distinguishable_observation_interpretation_significance(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """INV-003: Verify observation, interpretation, and significance layers are distinct and distinguishable."""
    agent = FacilityTrendExplanationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )
    report = await agent.explain_facility_trends(
        facility_id="ignite-oak-brook", scenario="staffing_stress", days_history=30
    )

    # 1. Observation layer: Verified numerical calculations exist
    calcs = report.verified_calculations
    assert "hppd_actual" in calcs.trends
    hppd_calc = calcs.trends["hppd_actual"]
    assert hppd_calc.current_value == pytest.approx(3.62, abs=0.1)
    assert hppd_calc.delta_7d is not None
    assert hppd_calc.delta_30d is not None

    # 2. Interpretation layer: Domain narrative explains what occurred
    assert "staffing" in report.trend_explanations
    staffing_trend = report.trend_explanations["staffing"]
    assert (
        "Direct Care" in staffing_trend.headline
        or "Staffing" in staffing_trend.headline
    )
    assert len(staffing_trend.narrative) > 30

    # 3. Significance layer: Operational meaning and impact
    hppd_detail = report.metric_explanations["hppd_actual"]
    assert "nursing care" in hppd_detail.plain_language_meaning.lower()
    assert (
        "regulatory" in hppd_detail.operational_significance.lower()
        or "care" in hppd_detail.operational_significance.lower()
    )


@pytest.mark.asyncio
async def test_ac3_2_dynamic_scenarios(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """AC-3.2.1: Verify trend explanations dynamically adapt to changing operational scenarios."""
    agent = FacilityTrendExplanationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )

    # 1. Baseline
    baseline_report = await agent.explain_facility_trends(
        facility_id="ignite-oak-brook", scenario="baseline"
    )
    assert len(baseline_report.notable_shifts) >= 0

    # 2. Hospital Transfer Spike
    transfer_report = await agent.explain_facility_trends(
        facility_id="ignite-oak-brook", scenario="hospital_transfer_spike"
    )
    assert "hospital_transfers" in transfer_report.trend_explanations
    ht_trend = transfer_report.trend_explanations["hospital_transfers"]
    assert ht_trend.trajectory_direction in ("INCREASING", "VOLATILE")
    assert ht_trend.is_meaningful_shift is True

    # 3. Auth Cliff
    auth_report = await agent.explain_facility_trends(
        facility_id="ignite-oak-brook", scenario="auth_cliff"
    )
    assert "payer_auth" in auth_report.trend_explanations
    auth_trend = auth_report.trend_explanations["payer_auth"]
    assert auth_trend.trajectory_direction in ("INCREASING", "DECREASING", "VOLATILE")


@pytest.mark.asyncio
async def test_ac3_2_zero_phi_and_grounding(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """INV-008 & INV-002: Verify zero patient PHI and strict grounding in trend outputs."""
    agent = FacilityTrendExplanationAgent(
        mcp_client=mcp_client, llm_client=offline_llm_client
    )
    report = await agent.explain_facility_trends(
        facility_id="ignite-oak-brook", scenario="hospital_transfer_spike"
    )

    json_str = report.model_dump_json().lower()
    for phi_term in ["patient name", "mrn", "ssn", "dob", "john doe", "jane doe"]:
        assert phi_term not in json_str

    # Grounding check: Snapshot value matches trend observation
    snapshot = mcp_client.get_facility_snapshot(
        facility_id="ignite-oak-brook", scenario="hospital_transfer_spike"
    )
    assert (
        report.verified_calculations.trends["current_census"].current_value
        == snapshot.census.current_census
    )


@pytest.mark.asyncio
async def test_fastapi_explain_trends_endpoint() -> None:
    """Test GET /api/agent/explain-trends REST API route for flagship facility across scenarios."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        scenarios = [
            "baseline",
            "staffing_stress",
            "hospital_transfer_spike",
            "auth_cliff",
        ]
        for scen in scenarios:
            response = await client.get(
                f"/api/agent/explain-trends?facility_id=ignite-oak-brook&scenario={scen}&days_history=30"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["facility_id"] == "ignite-oak-brook"
            assert len(data["metric_explanations"]) >= 7
            assert len(data["trend_explanations"]) >= 6
            assert data["analysis_state"] in (
                "ANALYSIS_COMPLETE",
                "AI_ANALYSIS_UNAVAILABLE",
            )
