"""FastAPI route handlers for Mock Domo MCP and facility operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

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


from src.agent.unified_agent import (
    FacilityUnifiedAnalysisAgent,
    UnifiedFacilityAnalysisResponse,
)

unified_agent = FacilityUnifiedAnalysisAgent(mcp_client=mcp_client)


@router.get("/agent/facility-analysis", response_model=UnifiedFacilityAnalysisResponse)
async def analyze_facility_unified_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
    force_refresh: bool = Query(
        default=False, description="Whether to bypass in-memory cache"
    ),
) -> UnifiedFacilityAnalysisResponse:
    """Perform complete facility operational analysis with single unified structured LLM reasoning."""
    try:
        return await unified_agent.analyze_facility(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
            force_refresh=force_refresh,
        )
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
@router.get("/agent/explain-trends", response_model=FacilityTrendExplanationReport)
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


from src.agent.brief_agent import FacilityBriefAgent
from src.analytics.briefing import FacilityBriefReport

brief_agent = FacilityBriefAgent(mcp_client=mcp_client)


@router.get("/agent/facility-brief", response_model=FacilityBriefReport)
async def get_facility_brief_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
) -> FacilityBriefReport:
    """Generate concise, human-readable Facility Brief for facility leaders (Story 3.1, AC-3.1.1)."""
    try:
        return await brief_agent.generate_facility_brief(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- Story 4.3: Dynamic Follow-Up Questions & Chat ---

from src.agent.chat_agent import ChatMessage, ChatResponse, FacilityChatAgent
from src.agent.question_agent import FacilityQuestionAgent, FollowUpQuestionReport

question_agent = FacilityQuestionAgent(mcp_client=mcp_client)
chat_agent = FacilityChatAgent(mcp_client=mcp_client)


@router.get("/agent/follow-up-questions", response_model=FollowUpQuestionReport)
async def get_follow_up_questions_endpoint(
    facility_id: str = Query(
        default="ignite-oak-brook", description="Facility identifier"
    ),
    scenario: str = Query(default="baseline", description="Operational scenario name"),
    days_history: int = Query(
        default=30, ge=1, le=365, description="Historical observation days"
    ),
) -> FollowUpQuestionReport:
    """Generate dynamic follow-up questions from the current facility analysis (Story 4.3)."""
    try:
        return await question_agent.generate_questions(
            facility_id=facility_id,
            scenario=scenario,
            days_history=days_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


class ChatRequest(BaseModel):
    """Request body for the facility chat endpoint."""

    facility_id: str = Field(
        default="ignite-oak-brook", description="Facility identifier"
    )
    scenario: str = Field(default="baseline", description="Operational scenario name")
    question: str = Field(..., description="User's question about facility operations")
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation for context",
    )


@router.post("/agent/chat", response_model=ChatResponse)
async def chat_with_facility_endpoint(
    request: ChatRequest,
) -> ChatResponse:
    """Answer a user question about facility operations using grounded data (Story 4.3)."""
    try:
        return await chat_agent.answer_question(
            facility_id=request.facility_id,
            scenario=request.scenario,
            question=request.question,
            conversation_history=request.conversation_history,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- Story 3.4: Technical / How It Works ---


class ArchitectureLayer(BaseModel):
    """Single layer in the technical architecture explanation."""

    name: str = Field(..., description="Layer name")
    description: str = Field(..., description="What this layer does")
    components: list[str] = Field(
        default_factory=list, description="Key components in this layer"
    )
    is_simulated: bool = Field(
        default=False, description="Whether this layer is simulated for the POC"
    )


class DataFlowStep(BaseModel):
    """Single step in the data flow pipeline."""

    step: int = Field(..., description="Step number in the pipeline")
    name: str = Field(..., description="Step name")
    description: str = Field(..., description="What happens at this step")
    source_component: str = Field(
        ..., description="Source component (e.g. 'Mock Domo MCP')"
    )
    output_component: str = Field(
        ..., description="Output component (e.g. 'Analytics Engine')"
    )


class TechnicalArchitectureReport(BaseModel):
    """Complete technical architecture explanation for CIO review (Story 3.4, AC-3.4.1, AC-3.4.2, AC-3.4.3)."""

    report_title: str = Field(
        default="Technical Architecture — How It Works",
        description="Report title",
    )
    overview: str = Field(
        ..., description="High-level overview of the POC architecture"
    )
    data_source: ArchitectureLayer = Field(
        ..., description="Data source layer explanation (AC-3.4.1)"
    )
    numerical_analysis: ArchitectureLayer = Field(
        ..., description="Numerical analysis layer explanation (AC-3.4.2)"
    )
    ai_interpretation: ArchitectureLayer = Field(
        ..., description="AI interpretation layer explanation (AC-3.4.2)"
    )
    evidence_grounding: ArchitectureLayer = Field(
        ..., description="Evidence grounding and reconciliation layer"
    )
    data_flow: list[DataFlowStep] = Field(
        ..., description="End-to-end data flow pipeline steps"
    )
    separation_of_responsibilities: dict[str, str] = Field(
        ...,
        description="Clear mapping of what each layer is responsible for vs. what it does NOT do",
    )
    limitations: list[str] = Field(
        ..., description="Explicit POC limitations and boundaries"
    )
    future_integration: str = Field(
        ...,
        description="How a real Domo MCP connection would replace the mock source",
    )
    disclaimers: list[str] = Field(
        ..., description="Mandatory transparency disclaimers (AC-3.4.3)"
    )


@router.get("/agent/technical-architecture", response_model=TechnicalArchitectureReport)
async def get_technical_architecture_endpoint() -> TechnicalArchitectureReport:
    """Explain the POC's data flow, numerical analysis, AI reasoning, and limitations for CIO review (Story 3.4, AC-3.4.1, AC-3.4.2, AC-3.4.3)."""
    connection_status = mcp_client.get_connection_status()

    return TechnicalArchitectureReport(
        report_title="Technical Architecture — How It Works",
        overview=(
            "This proof-of-concept demonstrates an operational decision-support agent for Ignite Medical Resorts. "
            "The system retrieves synthetic facility data through a simulated Domo MCP interface, performs deterministic "
            "numerical analysis across 8 operational domains, and uses an AI language model to generate plain-language "
            "interpretations and recommendations. The architecture deliberately separates numerical calculations from "
            "AI-generated prose to ensure traceability and accuracy."
        ),
        data_source=ArchitectureLayer(
            name="Data Source — Mock Domo MCP",
            description=(
                "The POC uses a simulated Domo Model Context Protocol (MCP) interface to provide facility data. "
                "This is NOT a live Domo connection. The mock server generates synthetic operational data for a single "
                "flagship facility (Ignite Medical Resort Oak Brook) across 6 operational scenarios. "
                "All data is synthetic and contains no real patient PHI."
            ),
            components=[
                "MockDomoMCPServer — In-process MCP tool server with 5 registered tools",
                "MockDomoMCPClient — Typed Python client for agent and API consumption",
                "FacilityDataLoader — Synthetic dataset loader with caching and validation",
                "Synthetic Data Generator — 180 snapshot records (30 days × 6 scenarios)",
            ],
            is_simulated=True,
        ),
        numerical_analysis=ArchitectureLayer(
            name="Numerical Analysis — Deterministic Calculations",
            description=(
                "All numerical metrics, variances, percentages, trends, and comparisons are computed by deterministic "
                "Python code — NOT by the language model. This ensures that numbers shown to the user are accurate, "
                "traceable to source data, and reproducible. The calculation engine covers all 8 operational domains: "
                "census, admissions/discharges, length of stay, therapy, staffing, payer authorizations, hospitality, "
                "and hospital transfers."
            ),
            components=[
                "calculate_facility_metrics() — Variance vs. targets, cross-domain correlations",
                "calculate_historical_trends() — Rolling averages, deltas, meaningful shift detection",
                "evaluate_attention_areas() — Threshold breach detection, severity classification",
                "generate_deterministic_recommendations() — Priority-sorted action items from attention areas",
                "NumericalGroundingReconciler — Eliminates hallucinated numbers from AI output",
            ],
            is_simulated=False,
        ),
        ai_interpretation=ArchitectureLayer(
            name="AI Interpretation — Language Model Reasoning",
            description=(
                "The AI language model generates plain-language explanations, executive summaries, and narrative "
                "interpretations. It does NOT perform calculations or invent numbers. The model receives pre-computed "
                "verified facts as input and produces human-readable analysis. When no API key is configured, the "
                "system falls back to deterministic templates (Spec §8 offline safety)."
            ),
            components=[
                "LLMClient — Multi-provider async client (OpenRouter, Gemini, OpenAI, custom endpoints)",
                "FacilityStateAgent — Current-state analysis with grounding reconciliation",
                "FacilityTrendExplanationAgent — Metric and trend plain-language explanations",
                "FacilityPositiveHighlightAgent — Positive performance identification",
                "FacilityAttentionAgent — Attention area prioritization and correlation",
                "FacilityRecommendationAgent — Data-grounded recommendation synthesis",
                "FacilityBriefAgent — Executive briefing generation",
                "FacilityQuestionAgent — Dynamic follow-up question generation from analysis",
                "FacilityChatAgent — Data-grounded conversational Q&A with reconciliation",
            ],
            is_simulated=False,
        ),
        evidence_grounding=ArchitectureLayer(
            name="Evidence Grounding & Reconciliation",
            description=(
                "Every finding, recommendation, and explanation must be traceable to source data or documented "
                "calculations. The NumericalGroundingReconciler compares AI-generated text against the set of verified "
                "numbers and removes or replaces any figures that cannot be traced. This prevents hallucinated metrics "
                "from reaching the user."
            ),
            components=[
                "NumericalGroundingReconciler.reconcile_text() — Validates AI prose against ground truth numbers",
                "LLMExecutionReceipt — Audit trail for every AI call (provider, model, latency, live/fallback)",
                "MCPToolCallResponse — Execution receipt for every data retrieval call",
                "supporting_evidence_metrics — Every recommendation cites verifiable metric evidence",
            ],
            is_simulated=False,
        ),
        data_flow=[
            DataFlowStep(
                step=1,
                name="Data Retrieval",
                description="Agent or API endpoint requests facility snapshot and history through the MCP client.",
                source_component="Mock Domo MCP Server",
                output_component="MockDomoMCPClient",
            ),
            DataFlowStep(
                step=2,
                name="Deterministic Calculations",
                description="Raw data is processed through the calculation engine to compute metrics, variances, trends, and attention areas.",
                source_component="MockDomoMCPClient",
                output_component="Analytics Engine (calculations.py, trends.py, attention_areas.py, recommendations.py)",
            ),
            DataFlowStep(
                step=3,
                name="AI Prompt Construction",
                description="Verified numerical facts are assembled into a structured prompt for the language model.",
                source_component="Analytics Engine",
                output_component="Agent Prompt Builder",
            ),
            DataFlowStep(
                step=4,
                name="AI Interpretation",
                description="The language model generates plain-language analysis from the verified facts. If unavailable, deterministic fallback templates are used.",
                source_component="Agent Prompt Builder",
                output_component="LLMClient / Deterministic Fallback",
            ),
            DataFlowStep(
                step=5,
                name="Grounding Reconciliation",
                description="AI-generated text is reconciled against the set of verified numbers. Hallucinated figures are removed or replaced.",
                source_component="LLMClient Output",
                output_component="NumericalGroundingReconciler",
            ),
            DataFlowStep(
                step=6,
                name="Response Assembly",
                description="Reconciled analysis, verified calculations, evidence metrics, and audit receipts are assembled into the final report.",
                source_component="NumericalGroundingReconciler",
                output_component="API Response / Frontend",
            ),
            DataFlowStep(
                step=7,
                name="Dynamic Follow-Up & Chat",
                description="The agent generates context-specific follow-up questions from the current analysis. Users can ask questions and receive data-grounded answers verified against numerical ground truth.",
                source_component="Analytics Engine + LLMClient",
                output_component="FacilityQuestionAgent / FacilityChatAgent",
            ),
        ],
        separation_of_responsibilities={
            "Data Source (Mock Domo MCP)": "Provides raw synthetic facility data. Does NOT perform calculations or generate interpretations.",
            "Numerical Analysis Engine": "Computes all metrics, variances, trends, and thresholds. Does NOT generate prose or narrative.",
            "AI Language Model": "Generates plain-language explanations from verified facts. Does NOT perform calculations or invent numbers.",
            "Evidence Grounding Reconciler": "Validates AI output against verified numbers. Does NOT generate new content.",
            "Frontend Presentation": "Renders structured data for human review. Does NOT modify or re-derive calculations.",
            "Dynamic Follow-Up & Chat": "Generates context-specific questions and data-grounded answers. Questions are derived from current analysis, not hard-coded. All responses are reconciled against verified numbers.",
        },
        limitations=[
            "This is a proof-of-concept using synthetic data. It is NOT a production clinical decision-support system.",
            "The Domo data source is simulated — there is no live Domo MCP connection.",
            "All facility metrics, census numbers, and operational records are synthetic and contain no real patient PHI.",
            "AI interpretation quality depends on the configured language model and may vary.",
            "When no LLM API key is configured, the system uses deterministic fallback templates instead of AI-generated analysis.",
            "The POC demonstrates a single flagship facility (Ignite Medical Resort Oak Brook) across 6 predefined scenarios.",
            "Recommendations are decision-support suggestions for human review — they are NOT autonomous actions.",
            "The system does not have access to real clinical data, EHR systems, or production Domo credentials.",
            "The Ask the Facility chat generates dynamic follow-up questions from the current analysis — questions are NOT hard-coded.",
            "Chat responses are grounded in verified facility data and reconciled against numerical ground truth.",
        ],
        future_integration=(
            "To connect to a real Domo data source, the MockDomoMCPServer would be replaced with a production Domo MCP "
            "adapter that implements the same 5 tool interfaces (domo_list_facilities, domo_get_facility_snapshot, "
            "domo_get_facility_history, domo_get_domain_metrics, domo_get_connection_status). The agent, analytics engine, "
            "and frontend would remain unchanged because they consume data through the MCP client abstraction — not directly "
            "from the mock implementation. This separation ensures the POC can transition to production without rewriting "
            "the decision-support logic."
        ),
        disclaimers=connection_status.disclaimers,
    )
