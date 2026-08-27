"""FastAPI route handlers for Mock Domo MCP and facility operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.agent.state_agent import FacilityStateAgent, FacilityStateAnalysis
from src.mcp.client import MockDomoMCPClient
from src.mcp.schemas import (
    DomoConnectionStatus,
    MCPToolCallRequest,
    MCPToolCallResponse,
    MCPToolDefinition,
)
from src.mcp.server import MockDomoMCPServer
from src.models.facility import DailyFacilitySnapshot, FacilityMetadata

router = APIRouter(prefix="/api", tags=["Facility Operations & MCP"])

# Singleton server and client instance for API lifecycle
mcp_server = MockDomoMCPServer()
mcp_client = MockDomoMCPClient(server=mcp_server)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for Railway and container orchestration."""
    return {"status": "healthy", "service": "ignite-facility-decision-agent"}


@router.get("/mcp/status", response_model=DomoConnectionStatus)
async def get_mcp_status() -> DomoConnectionStatus:
    """Retrieve Mock Domo MCP connection status, boundary metadata, and disclaimers."""
    return mcp_client.get_connection_status()


@router.get("/mcp/tools", response_model=list[MCPToolDefinition])
async def list_mcp_tools() -> list[MCPToolDefinition]:
    """List all registered MCP tools and JSON parameter schemas."""
    return mcp_client.get_tools()


@router.post("/mcp/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(request: MCPToolCallRequest) -> MCPToolCallResponse:
    """Execute an MCP tool and return structured output with execution receipt."""
    return mcp_server.call_tool(request)


@router.get("/facilities", response_model=list[FacilityMetadata])
async def list_facilities() -> list[FacilityMetadata]:
    """List available medical facilities."""
    return mcp_client.list_facilities()


@router.get("/facilities/{facility_id}/snapshot", response_model=DailyFacilitySnapshot)
async def get_facility_snapshot(
    facility_id: str,
    scenario: str = Query(default="baseline", description="Operational scenario"),
) -> DailyFacilitySnapshot:
    """Retrieve current daily operational snapshot for a facility."""
    try:
        return mcp_client.get_facility_snapshot(
            facility_id=facility_id, scenario=scenario
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/facilities/{facility_id}/history")
async def get_facility_history(
    facility_id: str,
    days: int = Query(
        default=30, ge=1, le=365, description="Number of historical days"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario"),
) -> dict[str, Any]:
    """Retrieve multi-day historical time-series for trend analysis."""
    try:
        history_series = mcp_client.get_facility_history(
            facility_id=facility_id, days_history=days, scenario=scenario
        )
        return history_series.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# Singleton agent instances
state_agent = FacilityStateAgent(mcp_client=mcp_client)
from src.agent.trend_agent import (
    FacilityTrendExplanationAgent,
    FacilityTrendExplanationReport,
)
from src.analytics.trends import MetricDefinition, get_standard_metric_definitions

trend_agent = FacilityTrendExplanationAgent(mcp_client=mcp_client)


@router.get("/agent/facility-state", response_model=FacilityStateAnalysis)
async def analyze_facility_state_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
) -> FacilityStateAnalysis:
    """Analyze current facility operational state using LLM reasoning and verified calculations."""
    try:
        return await state_agent.analyze_facility_state(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/agent/facility-trends", response_model=FacilityTrendExplanationReport)
async def explain_facility_trends_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
) -> FacilityTrendExplanationReport:
    """Explain metrics and 30-day historical trends in plain language for leadership decision support (Story 2.2)."""
    try:
        return await trend_agent.explain_facility_trends(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/agent/metric-definitions", response_model=dict[str, MetricDefinition])
async def get_metric_definitions_endpoint() -> dict[str, MetricDefinition]:
    """Retrieve standard non-technical operational metric definitions (AC-2.2.1)."""
    return get_standard_metric_definitions()


from src.agent.positive_agent import (
    FacilityPositiveHighlightAgent,
    PositivePerformanceReport,
)

positive_agent = FacilityPositiveHighlightAgent(mcp_client=mcp_client)


@router.get("/agent/positive-highlights", response_model=PositivePerformanceReport)
async def get_positive_highlights_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
) -> PositivePerformanceReport:
    """Identify and synthesize operational highlights and positive achievements (Story 2.3)."""
    try:
        return await positive_agent.identify_positive_performance(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


from src.agent.attention_agent import (
    AttentionAnalysisReport,
    FacilityAttentionAgent,
)

attention_agent = FacilityAttentionAgent(mcp_client=mcp_client)


@router.get("/agent/attention-areas", response_model=AttentionAnalysisReport)
async def get_attention_areas_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
) -> AttentionAnalysisReport:
    """Identify, prioritize, and correlate operational conditions requiring attention (Story 2.4)."""
    try:
        return await attention_agent.identify_attention_areas(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


from src.agent.recommendation_agent import (
    FacilityRecommendationAgent,
    RecommendationReport,
)

recommendation_agent = FacilityRecommendationAgent(mcp_client=mcp_client)


@router.get("/agent/recommendations", response_model=RecommendationReport)
async def get_recommendations_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
) -> RecommendationReport:
    """Generate prioritized, data-grounded operational recommendations (Story 2.5)."""
    try:
        return await recommendation_agent.generate_recommendations(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
