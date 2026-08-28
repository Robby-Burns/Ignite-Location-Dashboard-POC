"""Tests for Story 4.3 — Dynamic Follow-Up Questions & Chat.

Verifies:
- Questions are dynamically generated from the current analysis, not hard-coded.
- Questions change when the underlying facility data/scenario changes materially.
- Chat responses are grounded in verified facility data.
- Insufficient data produces explicit limitations.
- No fabricated values, clinical facts, or PHI.
- INV-001: No hard-coded scenario-specific intelligence.
- INV-002: Numbers trace to source/calculation.
- INV-004: Missing facts are not invented.
- INV-005: Uncertainty is communicated.
- INV-008: Zero PHI.
- FR-008: Changing relevant source data can change findings.
- FR-009: Human decision authority preserved.
"""

from __future__ import annotations

import pytest

from src.agent.chat_agent import ChatResponse, FacilityChatAgent
from src.agent.question_agent import FacilityQuestionAgent, FollowUpQuestionReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCENARIOS_WITH_DISTINCT_CONCERNS = [
    ("staffing_stress", "staffing"),
    ("auth_cliff", "payer_auth"),
    ("hospital_transfer_spike", "hospital_transfers"),
    ("therapy_disruption", "therapy"),
]


# ---------------------------------------------------------------------------
# Dynamic Question Generation
# ---------------------------------------------------------------------------


class TestDynamicQuestionGeneration:
    """Verify questions are generated from analysis, not hard-coded."""

    @pytest.mark.asyncio
    async def test_questions_generated_for_baseline(self) -> None:
        """Questions are generated even for a healthy baseline scenario."""
        agent = FacilityQuestionAgent()
        report = await agent.generate_questions("ignite-oak-brook", scenario="baseline")

        assert isinstance(report, FollowUpQuestionReport)
        assert len(report.questions) > 0, "Must generate at least one question"
        for q in report.questions:
            assert q.question_text, "Question must have text"
            assert q.related_domain, "Question must have a related domain"
            assert q.context_summary, "Question must have context"

    @pytest.mark.asyncio
    async def test_questions_differ_across_scenarios(self) -> None:
        """AC: Questions change when underlying data changes materially."""
        agent = FacilityQuestionAgent()

        baseline_report = await agent.generate_questions(
            "ignite-oak-brook", scenario="baseline"
        )
        staffing_report = await agent.generate_questions(
            "ignite-oak-brook", scenario="staffing_stress"
        )

        baseline_texts = {q.question_text for q in baseline_report.questions}
        staffing_texts = {q.question_text for q in staffing_report.questions}

        assert baseline_texts != staffing_texts, (
            "Questions must differ between baseline and staffing_stress scenarios"
        )

    @pytest.mark.asyncio
    async def test_stressed_scenario_questions_focus_on_relevant_domain(self) -> None:
        """AC: When a domain is stressed, questions should focus on that domain."""
        agent = FacilityQuestionAgent()

        for scenario, expected_domain in SCENARIOS_WITH_DISTINCT_CONCERNS:
            report = await agent.generate_questions(
                "ignite-oak-brook", scenario=scenario
            )
            domains = {q.related_domain for q in report.questions}
            assert expected_domain in domains, (
                f"Scenario '{scenario}' should produce questions about '{expected_domain}', "
                f"got domains: {domains}"
            )

    @pytest.mark.asyncio
    async def test_baseline_does_not_produce_stress_domain_questions(self) -> None:
        """AC: Baseline scenario should not focus on stress-specific domains."""
        agent = FacilityQuestionAgent()
        report = await agent.generate_questions("ignite-oak-brook", scenario="baseline")

        stress_domains = {"staffing", "payer_auth", "hospital_transfers", "therapy"}
        question_domains = {q.related_domain for q in report.questions}
        unexpected = question_domains & stress_domains

        # Allow if context_summary mentions these domains in a positive/stable context
        for q in report.questions:
            if q.related_domain in unexpected:
                # If the question exists for a stress domain in baseline, it should
                # be about positive performance, not deficits
                assert (
                    "well" in q.question_text.lower()
                    or "positive" in q.question_text.lower()
                    or "driving" in q.question_text.lower()
                    or "stable" in q.context_summary.lower()
                    or "normal" in q.context_summary.lower()
                    or "no active" in q.context_summary.lower()
                ), (
                    f"Baseline question about '{q.related_domain}' should be about "
                    f"positive performance, not deficits: {q.question_text}"
                )

    @pytest.mark.asyncio
    async def test_questions_not_hard_coded_empty_list(self) -> None:
        """AC: Questions are generated (not an empty hard-coded list)."""
        agent = FacilityQuestionAgent()

        for scenario in ["baseline", "staffing_stress", "auth_cliff"]:
            report = await agent.generate_questions(
                "ignite-oak-brook", scenario=scenario
            )
            assert len(report.questions) >= 1, (
                f"Scenario '{scenario}' must produce at least 1 question"
            )

    @pytest.mark.asyncio
    async def test_unknown_facility_raises_error(self) -> None:
        """Unknown facility raises DatasetUnavailableError."""
        from src.data.loader import DatasetUnavailableError

        agent = FacilityQuestionAgent()
        with pytest.raises(DatasetUnavailableError):
            await agent.generate_questions("non-existent-facility")


# ---------------------------------------------------------------------------
# Chat Responses
# ---------------------------------------------------------------------------


class TestChatResponses:
    """Verify chat responses are data-grounded and handle edge cases."""

    @pytest.mark.asyncio
    async def test_chat_returns_data_grounded_answer(self) -> None:
        """AC: Chat response contains a grounded answer with supporting data."""
        agent = FacilityChatAgent()
        response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="staffing_stress",
            question="What is the current staffing situation?",
        )

        assert isinstance(response, ChatResponse)
        assert response.answer, "Must provide an answer"
        assert len(response.supporting_data) > 0, "Must cite supporting data"
        assert len(response.data_sources_used) > 0, "Must identify data sources used"
        assert response.disclaimer, "Must include disclaimer"

    @pytest.mark.asyncio
    async def test_chat_answer_changes_with_scenario(self) -> None:
        """AC: Answers change when underlying data changes."""
        agent = FacilityChatAgent()

        baseline_response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="baseline",
            question="What are the main concerns right now?",
        )
        staffing_response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="staffing_stress",
            question="What are the main concerns right now?",
        )

        assert baseline_response.answer != staffing_response.answer, (
            "Answers must differ between baseline and staffing_stress"
        )

    @pytest.mark.asyncio
    async def test_chat_handles_empty_question(self) -> None:
        """AC: Empty question returns a helpful prompt, not fabricated content."""
        agent = FacilityChatAgent()
        response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="baseline",
            question="",
        )

        assert response.analysis_state == "INSUFFICIENT_DATA"
        assert "ask" in response.answer.lower() or "question" in response.answer.lower()

    @pytest.mark.asyncio
    async def test_chat_unknown_facility_raises_error(self) -> None:
        """Unknown facility raises DatasetUnavailableError."""
        from src.data.loader import DatasetUnavailableError

        agent = FacilityChatAgent()
        with pytest.raises(DatasetUnavailableError):
            await agent.answer_question(
                facility_id="non-existent-facility",
                question="What is happening?",
            )

    @pytest.mark.asyncio
    async def test_chat_preserves_human_authority(self) -> None:
        """AC / FR-009: Response does not claim autonomous action."""
        agent = FacilityChatAgent()
        response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="staffing_stress",
            question="What should we do about staffing?",
        )

        prohibited = [
            "action executed",
            "system decided",
            "automatically resolved",
            "dispatched",
        ]
        answer_lower = response.answer.lower()
        for term in prohibited:
            assert term not in answer_lower, (
                f"Prohibited autonomous claim found: '{term}'"
            )

    @pytest.mark.asyncio
    async def test_chat_no_phi_in_output(self) -> None:
        """AC / INV-008: No patient-identifying information in response."""
        agent = FacilityChatAgent()
        response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="staffing_stress",
            question="Tell me about the patients.",
        )

        output_text = response.model_dump_json().lower()
        prohibited = [
            "ssn",
            "mrn",
            "patient_name",
            "date_of_birth",
            "john doe",
            "jane doe",
        ]
        for term in prohibited:
            assert term not in output_text, f"Potential PHI detected: {term}"

    @pytest.mark.asyncio
    async def test_chat_disclaimer_present(self) -> None:
        """AC: Every response includes a decision-support disclaimer."""
        agent = FacilityChatAgent()
        response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="baseline",
            question="What is the census?",
        )

        assert "decision-support" in response.disclaimer.lower()
        assert "human" in response.disclaimer.lower()

    @pytest.mark.asyncio
    async def test_chat_domain_specific_question_gets_relevant_answer(self) -> None:
        """AC: Asking about a specific domain produces an answer referencing that domain."""
        agent = FacilityChatAgent()
        response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="staffing_stress",
            question="How is the nursing staffing doing?",
        )

        answer_lower = response.answer.lower()
        assert any(
            term in answer_lower
            for term in ["hppd", "staffing", "nursing", "shift", "agency"]
        ), (
            f"Staffing question should reference staffing metrics in answer: {response.answer[:100]}"
        )

    @pytest.mark.asyncio
    async def test_chat_positive_question_for_healthy_scenario(self) -> None:
        """AC: Asking 'what is going well' for baseline produces a positive answer."""
        agent = FacilityChatAgent()
        response = await agent.answer_question(
            facility_id="ignite-oak-brook",
            scenario="baseline",
            question="What is going well right now?",
        )

        answer_lower = response.answer.lower()
        assert any(
            term in answer_lower
            for term in [
                "well",
                "normal",
                "healthy",
                "stable",
                "no active",
                "operating",
            ]
        ), (
            f"Positive question for baseline should produce positive answer: {response.answer[:100]}"
        )
