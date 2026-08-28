"""Interactive Facility Chat Agent for Story 4.3.

Provides data-grounded Q&A responses to user questions about facility operations.
Uses the same deterministic analytics pipeline and grounding reconciliation as all other agents.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.agent.state_agent import NumericalGroundingReconciler
from src.analytics.attention_areas import evaluate_attention_areas
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.recommendations import generate_deterministic_recommendations
from src.analytics.trends import calculate_historical_trends
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: Literal["user", "assistant"] = Field(..., description="Message sender role")
    content: str = Field(..., description="Message content")


class ChatResponse(BaseModel):
    """Response from the facility chat agent."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Human-friendly facility name")
    answer: str = Field(..., description="Data-grounded answer to the user's question")
    supporting_data: list[str] = Field(
        default_factory=list,
        description="Verified data points supporting the answer",
    )
    data_sources_used: list[str] = Field(
        default_factory=list,
        description="Domains and data sources consulted",
    )
    analysis_state: Literal[
        "ANALYSIS_COMPLETE", "AI_ANALYSIS_UNAVAILABLE", "INSUFFICIENT_DATA"
    ] = Field(
        default="ANALYSIS_COMPLETE",
        description="Analysis state reflecting LLM availability and data sufficiency",
    )
    disclaimer: str = Field(
        default=(
            "This response is decision-support information for facility leadership review. "
            "It does not execute actions or replace human clinical or administrative judgment."
        ),
        description="Decision-support disclaimer",
    )
    audit_receipt: LLMExecutionReceipt = Field(..., description="LLM execution receipt")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of response",
    )


CHAT_SYSTEM_PROMPT = """You are the Ignite Facility Decision Support Agent answering a facility leader's question about operational data.

VOICE AND TONE:
- Direct, plainspoken, and conversational. Talk like a real operational partner, not a generic AI or corporate consultant.
- Practical and grounded in what the numbers actually show and what they mean on the floor.
- Confident without trying to sound impressive.
- Skeptical of buzzwords, corporate language, and marketing-speak (never use "leverage", "optimize", "synergize", "holistic", "transformative", "empower", etc.).
- Short and punchy when the idea calls for it. Mix short sentences with natural explanations.
- If the question is simple, give a direct answer first before adding context.

RULES:
1. STRICT NUMERICAL GROUNDING (INV-002): Only cite numbers from the verified facts provided. NEVER invent metrics.
2. EVIDENCE-BASED: Explain what the data shows and cite specific metrics. Distinguish between what the data shows and what you infer.
3. HUMAN AUTHORITY (FR-009): Frame responses as decision support. Never claim an action was executed.
4. UNCERTAINTY (INV-005): If the available data is insufficient to answer reliably, say so plainly.
5. ZERO PHI (INV-008): Never reference patient names or identifiers.
6. NO FABRICATION (INV-004): If you cannot answer from the available data, state that limitation directly.

Return JSON:
{
  "answer": "Your direct, data-grounded answer here.",
  "supporting_data": ["Specific data point 1", "Specific data point 2"],
  "data_sources_used": ["census", "staffing", "therapy"],
  "is_sufficient": true
}

If the data is insufficient to answer:
{
  "answer": "I don't have enough data to answer that accurately. The facility snapshot covers [domains] but doesn't include [missing info].",
  "supporting_data": [],
  "data_sources_used": [],
  "is_sufficient": false
}"""


class FacilityChatAgent:
    """Agent that answers user questions about facility operations using grounded data."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def answer_question(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
        question: str = "",
        conversation_history: list[ChatMessage] | None = None,
        days_history: int = 30,
    ) -> ChatResponse:
        """Answer a user question using available facility data."""
        facility_name = facility_id.replace("-", " ").title()

        if not question.strip():
            return ChatResponse(
                facility_id=facility_id,
                facility_name=facility_name,
                answer="Please ask a question about the facility operations.",
                analysis_state="INSUFFICIENT_DATA",
                audit_receipt=LLMExecutionReceipt(
                    receipt_id="REC-EMPTY-000",
                    provider="deterministic-fallback",
                    model="none",
                    latency_ms=0.0,
                    is_live_call=False,
                ),
            )

        try:
            snapshot = self.mcp_client.get_facility_snapshot(
                facility_id=facility_id, scenario=scenario
            )
            history = self.mcp_client.get_facility_history(
                facility_id=facility_id, days_history=days_history, scenario=scenario
            )
        except Exception as e:
            if "not found" in str(e).lower() or "unavailable" in str(e).lower():
                raise DatasetUnavailableError(
                    f"Cannot answer questions for facility '{facility_id}': data unavailable."
                ) from e
            raise

        calcs = calculate_facility_metrics(snapshot, scenario=scenario)
        trends = calculate_historical_trends(snapshot, history, scenario=scenario)
        attention_summary = evaluate_attention_areas(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            calculations=calcs,
            trends=trends,
        )
        rec_summary = generate_deterministic_recommendations(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            calculations=calcs,
            trends=trends,
            attention_summary=attention_summary,
        )

        ground_truth = NumericalGroundingReconciler.build_ground_truth_set(
            snapshot, calcs
        )

        user_prompt = self._build_prompt(
            facility_name,
            snapshot,
            calcs,
            attention_summary,
            rec_summary,
            trends,
            question,
            conversation_history,
        )

        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=CHAT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema_name="ChatResponse",
        )

        if llm_output is None or not receipt.is_live_call:
            answer = self._generate_deterministic_answer(
                question, snapshot, calcs, attention_summary, rec_summary, facility_name
            )
            supporting_data = self._extract_supporting_data(snapshot, attention_summary)
            analysis_state = "AI_ANALYSIS_UNAVAILABLE"
        else:
            raw_answer = llm_output.get("answer", "")
            is_sufficient = llm_output.get("is_sufficient", True)

            if not is_sufficient:
                answer = raw_answer
                analysis_state = "INSUFFICIENT_DATA"
            else:
                reconciled_answer, is_valid = (
                    NumericalGroundingReconciler.reconcile_text(
                        raw_answer, ground_truth, ""
                    )
                )
                if is_valid and reconciled_answer:
                    answer = reconciled_answer
                else:
                    answer = self._generate_deterministic_answer(
                        question,
                        snapshot,
                        calcs,
                        attention_summary,
                        rec_summary,
                        facility_name,
                    )
                analysis_state = "ANALYSIS_COMPLETE"

            supporting_data = llm_output.get("supporting_data", [])
            if not supporting_data:
                supporting_data = self._extract_supporting_data(
                    snapshot, attention_summary
                )

        data_sources_used = list(
            {item.domain for item in attention_summary.attention_items}
        )
        if not data_sources_used:
            data_sources_used = ["census", "staffing", "therapy"]

        return ChatResponse(
            facility_id=facility_id,
            facility_name=facility_name,
            answer=answer,
            supporting_data=supporting_data,
            data_sources_used=data_sources_used,
            analysis_state=analysis_state,
            audit_receipt=receipt,
        )

    def _generate_deterministic_answer(
        self,
        question: str,
        snapshot,
        calcs,
        attention_summary,
        rec_summary,
        facility_name: str,
    ) -> str:
        """Generate a deterministic answer when LLM is unavailable."""
        q_lower = question.lower()
        c = snapshot.census
        st = snapshot.staffing

        for item in attention_summary.attention_items:
            if item.domain in q_lower or item.metric_name.replace("_", " ") in q_lower:
                return (
                    f"Based on the current facility data: {item.evidence_statement} "
                    f"{item.operational_risk_summary} "
                    f"(AI interpretation is offline; displaying verified data per Spec §8)."
                )

        if any(word in q_lower for word in ("staffing", "nursing", "hppd", "shift")):
            return (
                f"Current nursing staffing: {st.hppd_actual} HPPD vs {st.hppd_budgeted_target} target. "
                f"{st.open_shifts_count} open shifts, {st.agency_staff_pct}% agency utilization. "
                f"{st.call_in_absences_count} call-ins today. "
                f"(AI interpretation is offline; displaying verified data per Spec §8)."
            )

        if any(word in q_lower for word in ("census", "occupancy", "bed")):
            return (
                f"Current census: {c.current_census}/{c.total_capacity} beds ({c.occupancy_rate_pct}% occupancy). "
                f"{c.available_beds} beds available. "
                f"(AI interpretation is offline; displaying verified data per Spec §8)."
            )

        if (
            any(word in q_lower for word in ("well", "positive", "good"))
            and attention_summary.total_attention_count == 0
        ):
            return (
                f"{facility_name} is operating with no active deficit conditions across all monitored domains. "
                f"Census is at {c.occupancy_rate_pct}%. "
                f"(AI interpretation is offline; displaying verified data per Spec §8)."
            )

        if attention_summary.attention_items:
            top = attention_summary.attention_items[0]
            return (
                f"The primary area of attention is {top.title}: {top.evidence_statement} "
                f"(AI interpretation is offline; displaying verified data per Spec §8)."
            )

        return (
            f"{facility_name} is operating within normal parameters. "
            f"Census: {c.occupancy_rate_pct}%, Staffing: {st.hppd_actual} HPPD. "
            f"(AI interpretation is offline; displaying verified data per Spec §8)."
        )

    def _extract_supporting_data(self, snapshot, attention_summary) -> list[str]:
        """Extract key data points for the response."""
        data = []
        c = snapshot.census
        st = snapshot.staffing
        data.append(
            f"Census: {c.current_census}/{c.total_capacity} ({c.occupancy_rate_pct}%)"
        )
        data.append(
            f"Staffing: {st.hppd_actual} HPPD vs {st.hppd_budgeted_target} target"
        )

        for item in attention_summary.attention_items[:3]:
            data.append(item.evidence_statement)

        return data

    def _build_prompt(
        self,
        facility_name: str,
        snapshot,
        calcs,
        attention_summary,
        rec_summary,
        trends,
        question: str,
        conversation_history: list[ChatMessage] | None,
    ) -> str:
        """Build grounded prompt with all verified facts for answering the question."""
        attention_lines = []
        for item in attention_summary.attention_items:
            attention_lines.append(
                f"- [{item.severity}] {item.domain_display_name}: {item.title} — {item.evidence_statement}"
            )

        rec_lines = []
        for rec in rec_summary.recommendations[:5]:
            rec_lines.append(f"- [{rec.priority}] {rec.action_title}: {rec.rationale}")

        metrics_summary = {}
        for domain_name, summary in calcs.domains.items():
            metrics_summary[domain_name] = {
                "risk_level": summary.risk_level,
                "key_findings": summary.key_findings,
                "metrics": {
                    m_name: {
                        "value": m.value,
                        "target": m.target_or_budget,
                        "status": m.status,
                    }
                    for m_name, m in summary.metrics.items()
                },
            }

        history_lines = []
        if conversation_history:
            for msg in conversation_history[-4:]:
                history_lines.append(f"{msg.role}: {msg.content}")

        prompt_dict = {
            "facility_name": facility_name,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "scenario": attention_summary.scenario,
            "attention_areas": attention_lines,
            "recommendations": rec_lines,
            "domain_metrics": metrics_summary,
            "meaningful_trends": trends.meaningful_shifts[:5],
            "conversation_history": history_lines,
            "user_question": question,
        }
        return (
            "Answer the following facility leader question using ONLY the verified data below. "
            "If the data is insufficient to answer, say so explicitly.\n\n"
            + json.dumps(prompt_dict, indent=2)
        )
