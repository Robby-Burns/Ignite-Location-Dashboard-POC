"""Dynamic Follow-Up Question Generation Agent for Story 4.3.

Generates context-specific suggested questions from the current facility analysis.
Questions are derived from attention areas, recommendations, and trends — never hard-coded.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.analytics.attention_areas import evaluate_attention_areas
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.recommendations import generate_deterministic_recommendations
from src.analytics.trends import calculate_historical_trends
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient


class FollowUpQuestion(BaseModel):
    """A single dynamically generated follow-up question."""

    question_id: str = Field(..., description="Unique question identifier")
    question_text: str = Field(
        ..., description="The suggested question a facility leader might ask"
    )
    related_domain: str = Field(
        ..., description="Primary operational domain this question relates to"
    )
    context_summary: str = Field(
        ...,
        description="Brief context about why this question is relevant to the current analysis",
    )
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ..., description="Priority based on severity of the underlying finding"
    )


class FollowUpQuestionReport(BaseModel):
    """Report containing dynamically generated follow-up questions."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Human-friendly facility name")
    scenario: str = Field(..., description="Evaluated scenario")
    analysis_state: Literal["ANALYSIS_COMPLETE", "AI_ANALYSIS_UNAVAILABLE"] = Field(
        default="ANALYSIS_COMPLETE",
        description="Whether questions were generated with AI or deterministically",
    )
    questions: list[FollowUpQuestion] = Field(
        default_factory=list,
        description="Dynamically generated follow-up questions",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of generation",
    )
    audit_receipt: LLMExecutionReceipt = Field(..., description="LLM execution receipt")


QUESTION_SYSTEM_PROMPT = """You are an operational intelligence assistant helping facility leaders investigate their facility data.

Given the current facility analysis (attention areas, recommendations, trends, and positive highlights), generate 4-6 follow-up questions a facility leader would naturally want to ask to dig deeper.

CRITICAL RULES:
1. Questions MUST be derived from the specific findings, attention areas, and recommendations provided.
2. Do NOT generate generic questions that could apply to any facility or scenario.
3. Questions should help the leader understand ROOT CAUSES, SPECIFIC METRICS, and ACTIONABLE DETAILS.
4. Vary the question types: some about root causes, some about specific data, some about trends, some about positive performance.
5. Every question must reference a specific metric, finding, or recommendation from the analysis.
6. Do NOT invent concerns that are not present in the data.

Return JSON:
{
  "questions": [
    {
      "question_text": "What is driving the decline in therapy completion this week?",
      "related_domain": "therapy",
      "context_summary": "Therapy completion dropped to 78%, below the 90% threshold.",
      "priority": "HIGH"
    }
  ]
}"""


class FacilityQuestionAgent:
    """Agent that generates dynamic follow-up questions from facility analysis."""

    def __init__(
        self,
        mcp_client: MockDomoMCPClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.mcp_client = mcp_client or MockDomoMCPClient()
        self.llm_client = llm_client or LLMClient()

    async def generate_questions(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
        days_history: int = 30,
    ) -> FollowUpQuestionReport:
        """Generate dynamic follow-up questions from the current facility analysis."""
        facility_name = facility_id.replace("-", " ").title()

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
                    f"Cannot generate questions for facility '{facility_id}': data unavailable."
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

        user_prompt = self._build_prompt(
            facility_name, snapshot, attention_summary, rec_summary, trends
        )

        llm_output, receipt = await self.llm_client.generate_structured_analysis(
            system_prompt=QUESTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema_name="FollowUpQuestionReport",
        )

        if llm_output is None or not receipt.is_live_call:
            questions = self._generate_deterministic_questions(
                attention_summary, rec_summary, facility_id
            )
            analysis_state = "AI_ANALYSIS_UNAVAILABLE"
        else:
            questions = self._parse_llm_questions(
                llm_output, attention_summary, facility_id
            )
            analysis_state = "ANALYSIS_COMPLETE"

        return FollowUpQuestionReport(
            facility_id=facility_id,
            facility_name=facility_name,
            scenario=scenario,
            analysis_state=analysis_state,
            questions=questions,
            audit_receipt=receipt,
        )

    def _generate_deterministic_questions(
        self,
        attention_summary,
        rec_summary,
        facility_id: str,
    ) -> list[FollowUpQuestion]:
        """Generate questions directly from attention items when LLM is unavailable."""
        questions: list[FollowUpQuestion] = []
        q_counter = 1

        for item in attention_summary.attention_items[:4]:
            questions.append(
                FollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-{q_counter:02d}",
                    question_text=f"What is driving the {item.title.lower()}?",
                    related_domain=item.domain,
                    context_summary=item.evidence_statement,
                    priority="HIGH"
                    if item.severity in ("CRITICAL", "HIGH")
                    else "MEDIUM",
                )
            )
            q_counter += 1

        for rec in rec_summary.recommendations[:2]:
            questions.append(
                FollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-{q_counter:02d}",
                    question_text=f"What data supports the recommendation: {rec.action_title}?",
                    related_domain=rec.domain,
                    context_summary=rec.rationale,
                    priority=rec.priority,
                )
            )
            q_counter += 1

        if not questions:
            questions.append(
                FollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-01",
                    question_text="What is going well right now?",
                    related_domain="census",
                    context_summary="No active deficit conditions detected.",
                    priority="LOW",
                )
            )

        return questions

    def _parse_llm_questions(
        self,
        llm_output: dict,
        attention_summary,
        facility_id: str,
    ) -> list[FollowUpQuestion]:
        """Parse and validate LLM-generated questions."""
        raw_questions = llm_output.get("questions", [])
        active_domains = {item.domain for item in attention_summary.attention_items}
        active_domains.update(item.domain for item in attention_summary.attention_items)

        questions: list[FollowUpQuestion] = []
        for i, q in enumerate(raw_questions[:6]):
            q_text = q.get("question_text", "")
            if not q_text:
                continue

            related = q.get("related_domain", "general")
            context = q.get("context_summary", "")
            priority = q.get("priority", "MEDIUM")

            questions.append(
                FollowUpQuestion(
                    question_id=f"Q-{facility_id[:6]}-{i + 1:02d}",
                    question_text=q_text,
                    related_domain=related,
                    context_summary=context,
                    priority=priority
                    if priority in ("HIGH", "MEDIUM", "LOW")
                    else "MEDIUM",
                )
            )

        if not questions:
            return self._generate_deterministic_questions(
                attention_summary, None, facility_id
            )

        return questions

    def _build_prompt(
        self,
        facility_name: str,
        snapshot,
        attention_summary,
        rec_summary,
        trends,
    ) -> str:
        """Build grounded prompt with verified facts for question generation."""
        attention_lines = []
        for item in attention_summary.attention_items:
            attention_lines.append(
                f"- [{item.severity}] {item.domain_display_name}: {item.title} — {item.evidence_statement}"
            )

        rec_lines = []
        for rec in rec_summary.recommendations:
            rec_lines.append(f"- [{rec.priority}] {rec.action_title}: {rec.rationale}")

        positive_lines = []
        for shift in trends.meaningful_shifts[:5]:
            positive_lines.append(f"- {shift}")

        prompt_dict = {
            "facility_name": facility_name,
            "scenario": attention_summary.scenario,
            "total_attention_items": attention_summary.total_attention_count,
            "critical_count": attention_summary.critical_count,
            "high_count": attention_summary.high_count,
            "attention_areas": attention_lines,
            "total_recommendations": rec_summary.total_recommendations_count,
            "recommendations": rec_lines,
            "meaningful_trends": positive_lines,
            "top_risk_domains": attention_summary.top_risk_domains,
        }
        return (
            "Based on the following verified facility analysis, generate follow-up questions "
            "a facility leader would want to ask to investigate further:\n\n"
            + json.dumps(prompt_dict, indent=2)
        )
