"""Unit and integration tests for FacilityUnifiedAnalysisAgent (Single Structured LLM Call Architecture)."""

import pytest
from unittest.mock import AsyncMock, patch
from src.agent.unified_agent import (
    FacilityUnifiedAnalysisAgent,
    UnifiedFacilityAnalysisResponse,
)
from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.mcp.client import MockDomoMCPClient
from src.api.main import app
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mcp_client():
    return MockDomoMCPClient()


@pytest.fixture
def mock_llm_client():
    client = LLMClient()
    return client


@pytest.mark.asyncio
async def test_unified_agent_default_model():
    """Verify default model resolves to google/gemini-2.5-flash-lite."""
    client = LLMClient()
    assert "gemini-2.5-flash-lite" in client.model


@pytest.mark.asyncio
async def test_unified_agent_deterministic_fallback_on_llm_failure(mcp_client):
    """Verify that when LLM fails or is unavailable, deterministic fallback is returned."""
    mock_client = LLMClient()
    mock_receipt = LLMExecutionReceipt(
        receipt_id="REC-TEST-FALLBACK",
        provider="mock",
        model="google/gemini-2.5-flash-lite",
        latency_ms=10.0,
        is_live_call=False,
        prompt_chars=500,
        completion_chars=0,
    )
    with patch.object(mock_client, "generate_structured_analysis", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (None, mock_receipt)
        agent = FacilityUnifiedAnalysisAgent(mcp_client=mcp_client, llm_client=mock_client)
        result = await agent.analyze_facility(
            facility_id="ignite-oak-brook",
            scenario="staffing_stress",
        )

        assert isinstance(result, UnifiedFacilityAnalysisResponse)
        assert result.analysis_state == "DETERMINISTIC_FALLBACK"
        assert result.fallback_reason is not None
        assert len(result.vitals) == 5
        assert len(result.findings) >= 1
        assert len(result.suggested_questions) >= 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        "baseline",
        "staffing_stress",
        "auth_cliff",
        "high_census_strain",
        "hospital_transfer_spike",
        "therapy_disruption",
    ],
)
async def test_unified_agent_all_scenarios_deterministic(mcp_client, scenario):
    """Verify analysis executes cleanly across all 6 supported synthetic scenarios."""
    mock_client = LLMClient()
    mock_receipt = LLMExecutionReceipt(
        receipt_id="REC-TEST-ALL",
        provider="mock",
        model="google/gemini-2.5-flash-lite",
        latency_ms=5.0,
        is_live_call=False,
        prompt_chars=1000,
        completion_chars=0,
    )
    with patch.object(mock_client, "generate_structured_analysis", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (None, mock_receipt)
        agent = FacilityUnifiedAnalysisAgent(mcp_client=mcp_client, llm_client=mock_client)
        result = await agent.analyze_facility(
            facility_id="ignite-oak-brook",
            scenario=scenario,
        )

        assert result.facility_id == "ignite-oak-brook"
        assert result.scenario == scenario
        assert result.overall_status in ("HEALTHY", "WATCH", "NEEDS_ATTENTION", "CRITICAL")
        assert len(result.vitals) == 5
        assert len(result.positive_highlights) >= 1
        assert len(result.suggested_questions) >= 1


@pytest.mark.asyncio
async def test_unified_agent_live_grounding_and_reconciliation(mcp_client):
    """Verify that live LLM analysis preserves grounded text and reconciles hallucinated numbers."""
    mock_client = LLMClient()
    mock_receipt = LLMExecutionReceipt(
        receipt_id="REC-TEST-LIVE",
        provider="openrouter",
        model="google/gemini-2.5-flash-lite",
        latency_ms=1200.0,
        is_live_call=True,
        prompt_chars=2500,
        completion_chars=1500,
    )

    # First fetch snapshot to get real grounded numbers
    snapshot = mcp_client.get_facility_snapshot("ignite-oak-brook", "staffing_stress")
    occ = snapshot.census.occupancy_rate_pct
    real_hppd = snapshot.staffing.hppd_actual

    mock_llm_json = {
        "executive_summary": f"Oak Brook is operating at {occ:.1f}% occupancy with active staffing focus.",
        "findings_interpretations": [
            {
                "id": "ATT-staffing-001",
                "whats_happening": f"Direct care nursing hours are at {real_hppd:.1f} HPPD on the floor.",
                "why_it_matters": "Understaffing increases clinical risk and nurse burnout.",
                "whats_driving_it": ["staffing"],
                "what_you_could_consider": "Consider reviewing internal float pool coverage.",
                "why_suggested": "Restores nursing coverage to target."
            }
        ],
        "positive_interpretations": [
            {
                "title": "Exemplary Guest Dining Satisfaction",
                "whats_happening": "Dining score reached 92.4 pts exceeding targets.",
                "why_it_matters": "Drives resident retention.",
                "whats_driving_it": "Consistency in dietary staff coverage.",
                "what_we_could_learn": "Replicate shift handoff practices."
            }
        ],
        "suggested_questions": [
            {
                "question_text": f"What steps can restore nursing hours from {real_hppd:.1f} HPPD to target?",
                "related_domain": "staffing",
                "context_summary": "Staffing deficit observed in direct care hours.",
                "priority": "HIGH"
            }
        ]
    }

    with patch.object(mock_client, "generate_structured_analysis", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (mock_llm_json, mock_receipt)
        agent = FacilityUnifiedAnalysisAgent(mcp_client=mcp_client, llm_client=mock_client)
        result = await agent.analyze_facility(
            facility_id="ignite-oak-brook",
            scenario="staffing_stress",
        )

        # Confirm exactly 1 LLM call occurred
        assert mock_gen.call_count == 1
        assert result.analysis_state == "LLM_ANALYSIS"
        assert result.fallback_reason is None
        assert f"{occ:.1f}%" in result.executive_summary
        assert len(result.findings) >= 1
        finding = result.findings[0]
        assert f"{real_hppd:.1f} HPPD" in finding.whatsHappening
        assert finding.recommendation is not None
        assert finding.recommendation.consider == "Consider reviewing internal float pool coverage."
        assert len(result.suggested_questions) >= 1
        assert result.suggested_questions[0].related_domain == "staffing"


@pytest.mark.asyncio
async def test_api_facility_analysis_endpoint():
    """Verify GET /api/agent/facility-analysis returns 200 and conforms to UnifiedFacilityAnalysisResponse."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/agent/facility-analysis",
            params={"facility_id": "ignite-oak-brook", "scenario": "staffing_stress"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["facility_id"] == "ignite-oak-brook"
        assert data["scenario"] == "staffing_stress"
        assert "executive_summary" in data
        assert "vitals" in data
        assert len(data["vitals"]) == 5
        assert "findings" in data
        assert "positive_highlights" in data
        assert "suggested_questions" in data
        assert "audit_receipt" in data


@pytest.mark.asyncio
async def test_unified_agent_in_memory_caching(mcp_client):
    """Verify that in-memory cache returns cached response without making subsequent LLM calls."""
    mock_client = LLMClient()
    mock_receipt = LLMExecutionReceipt(
        receipt_id="REC-TEST-CACHE",
        provider="mock",
        model="google/gemini-2.5-flash-lite",
        latency_ms=10.0,
        is_live_call=False,
        prompt_chars=500,
        completion_chars=0,
    )
    with patch.object(mock_client, "generate_structured_analysis", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (None, mock_receipt)
        agent = FacilityUnifiedAnalysisAgent(mcp_client=mcp_client, llm_client=mock_client)
        
        # 1. First call triggers generation
        res1 = await agent.analyze_facility("ignite-oak-brook", "baseline")
        assert mock_gen.call_count == 1
        
        # 2. Second identical call returns from in-memory cache without calling LLM again
        res2 = await agent.analyze_facility("ignite-oak-brook", "baseline")
        assert mock_gen.call_count == 1
        assert res1.report_date == res2.report_date
        
        # 3. Force refresh bypasses cache and calls generation
        res3 = await agent.analyze_facility("ignite-oak-brook", "baseline", force_refresh=True)
        assert mock_gen.call_count == 2

