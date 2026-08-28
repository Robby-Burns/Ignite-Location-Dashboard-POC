"""Unit and integration tests for Facility Brief (Story 3.1, AC-3.1.1)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.agent.brief_agent import FacilityBriefAgent
from src.agent.llm_client import LLMClient
from src.analytics.briefing import FacilityBriefReport
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
async def test_ac3_1_1_facility_brief_plain_language_structure(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """AC-3.1.1: Verify human-readable, non-technical facility operational brief."""
    agent = FacilityBriefAgent(mcp_client=mcp_client, llm_client=offline_llm_client)
    brief = await agent.generate_facility_brief(
        facility_id="ignite-oak-brook", scenario="baseline"
    )

    assert isinstance(brief, FacilityBriefReport)
    assert brief.header.facility_name == "Ignite Medical Resort Oak Brook"
    assert brief.header.overall_status == "HEALTHY"
    assert "Stable" in brief.header.status_label
    assert len(brief.header.executive_summary) > 20
    assert (
        "87.3%" in brief.header.executive_summary
        or "96 / 110" in brief.header.executive_summary
    )

    # Vitals check
    assert len(brief.vitals) >= 5
    metric_names = [v.metric_name for v in brief.vitals]
    assert "occupancy_rate_pct" in metric_names
    assert "hppd_actual" in metric_names
    assert "agency_staff_pct" in metric_names
    assert "treatment_completion_rate_pct" in metric_names
    assert "dining_satisfaction_score" in metric_names

    # Positive highlights
    assert len(brief.positive_highlights) > 0
    for h in brief.positive_highlights:
        assert h.title
        assert h.domain
        assert h.plain_language_description
        assert h.supporting_metric

    # Limitations & governance (plain language, non-technical)
    assert brief.limitations.is_simulated_domo is True
    assert "Decision Support Only" in brief.limitations.disclaimer
    for note in brief.limitations.data_completeness_notes:
        assert "INV-" not in note
        assert "Spec §" not in note


@pytest.mark.asyncio
async def test_ac3_1_1_dynamic_scenarios(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """AC-3.1.1 & AC-2.5.2: Verify brief dynamically adapts to operational scenarios."""
    agent = FacilityBriefAgent(mcp_client=mcp_client, llm_client=offline_llm_client)

    # 1. Baseline -> Healthy
    baseline_brief = await agent.generate_facility_brief(scenario="baseline")
    assert baseline_brief.header.overall_status == "HEALTHY"

    # 2. Staffing Stress -> Needs Attention or Critical
    staffing_brief = await agent.generate_facility_brief(scenario="staffing_stress")
    assert staffing_brief.header.overall_status in ("NEEDS_ATTENTION", "CRITICAL")
    assert any(
        "Staffing" in item.domain or "Nursing" in item.title
        for item in staffing_brief.watch_items
    )
    assert any(
        "Staffing" in item.department
        or "Nursing" in item.title
        or "Staffing" in item.title
        for item in staffing_brief.action_items
    )

    # 3. Hospital Transfer Spike -> Needs Attention
    transfer_brief = await agent.generate_facility_brief(
        scenario="hospital_transfer_spike"
    )
    assert transfer_brief.header.overall_status in ("NEEDS_ATTENTION", "CRITICAL")
    assert any(
        "Transfer" in item.domain
        or "Transfer" in item.title
        or "Hospital" in item.domain
        for item in transfer_brief.watch_items
    )

    # 4. Auth Cliff -> Needs Attention
    auth_brief = await agent.generate_facility_brief(scenario="auth_cliff")
    assert auth_brief.header.overall_status in ("NEEDS_ATTENTION", "CRITICAL")
    assert any(
        "Authorization" in item.domain
        or "Authorization" in item.title
        or "Payer" in item.domain
        for item in auth_brief.watch_items
    )


@pytest.mark.asyncio
async def test_ac3_1_zero_phi_and_grounding(
    mcp_client: MockDomoMCPClient, offline_llm_client: LLMClient
) -> None:
    """INV-008 & INV-002: Verify zero patient PHI and strict numerical grounding in brief."""
    agent = FacilityBriefAgent(mcp_client=mcp_client, llm_client=offline_llm_client)
    brief = await agent.generate_facility_brief(scenario="staffing_stress")

    json_str = brief.model_dump_json().lower()
    for phi_term in ["patient name", "mrn", "ssn", "dob", "john doe", "jane doe"]:
        assert phi_term not in json_str

    # Grounding: HPPD value matches snapshot (staffing_stress reduces HPPD by 0.50 from target)
    hppd_vital = next(v for v in brief.vitals if v.metric_name == "hppd_actual")
    assert "3.80" in hppd_vital.formatted_value


@pytest.mark.asyncio
async def test_fastapi_brief_endpoint_all_facilities() -> None:
    """Test GET /api/agent/facility-brief REST API route across all available facilities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch available facilities list
        fac_resp = await client.get("/api/facilities")
        assert fac_resp.status_code == 200
        facilities = fac_resp.json()
        assert len(facilities) >= 3

        # 2. Check each facility returns valid 200 brief
        valid_statuses = {"HEALTHY", "WATCH", "NEEDS_ATTENTION", "CRITICAL"}
        for fac in facilities:
            fac_id = fac["facility_id"]
            response = await client.get(
                f"/api/agent/facility-brief?facility_id={fac_id}&scenario=baseline"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["header"]["facility_id"] == fac_id
            assert data["header"]["overall_status"] in valid_statuses
            assert len(data["vitals"]) >= 5
            assert len(data["positive_highlights"]) > 0
            assert data["limitations"]["is_simulated_domo"] is True
