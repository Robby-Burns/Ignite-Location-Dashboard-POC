"""Unit and integration tests for Technical / How It Works view (Story 3.4, AC-3.4.1, AC-3.4.2, AC-3.4.3)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_ac3_4_1_data_source_explanation() -> None:
    """AC-3.4.1: Verify the technical view explains which information comes from the data source."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent/technical-architecture")
        assert response.status_code == 200
        data = response.json()

        # Data source layer must exist and explain the mock Domo MCP
        data_source = data["data_source"]
        assert (
            "Mock Domo" in data_source["name"] or "mock" in data_source["name"].lower()
        )
        assert len(data_source["description"]) > 50
        assert data_source["is_simulated"] is True

        # Data source must list concrete components
        assert len(data_source["components"]) >= 2
        for comp in data_source["components"]:
            assert len(comp) > 10

        # Data flow must reference the data source
        data_flow = data["data_flow"]
        assert len(data_flow) >= 4
        first_step = data_flow[0]
        assert (
            "Mock" in first_step["source_component"]
            or "MCP" in first_step["source_component"]
        )


@pytest.mark.asyncio
async def test_ac3_4_2_numerical_vs_ai_separation() -> None:
    """AC-3.4.2: Verify the technical view explains the difference between numerical analysis and AI-generated interpretation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent/technical-architecture")
        assert response.status_code == 200
        data = response.json()

        # Numerical analysis layer must exist and explain deterministic calculations
        numerical = data["numerical_analysis"]
        assert (
            "numerical" in numerical["name"].lower()
            or "deterministic" in numerical["name"].lower()
        )
        assert (
            "deterministic" in numerical["description"].lower()
            or "NOT by the language model" in numerical["description"]
        )
        assert numerical["is_simulated"] is False

        # AI interpretation layer must exist and explain language model role
        ai_interp = data["ai_interpretation"]
        assert (
            "ai" in ai_interp["name"].lower()
            or "language model" in ai_interp["name"].lower()
        )
        assert (
            "does NOT perform calculations" in ai_interp["description"]
            or "not perform calculations" in ai_interp["description"].lower()
        )
        assert ai_interp["is_simulated"] is False

        # Separation of responsibilities must explicitly distinguish the two
        separation = data["separation_of_responsibilities"]
        assert len(separation) >= 3
        # Must have entries for both numerical and AI layers
        separation_keys_lower = [k.lower() for k in separation]
        has_numerical = any(
            "numerical" in k or "calculation" in k for k in separation_keys_lower
        )
        has_ai = any("ai" in k or "language model" in k for k in separation_keys_lower)
        assert has_numerical, (
            "Separation of responsibilities must include numerical analysis layer"
        )
        assert has_ai, (
            "Separation of responsibilities must include AI interpretation layer"
        )


@pytest.mark.asyncio
async def test_ac3_4_3_domo_identified_as_simulated() -> None:
    """AC-3.4.3: Verify the technical view clearly identifies the Domo connection as simulated."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent/technical-architecture")
        assert response.status_code == 200
        data = response.json()

        # Data source must be marked as simulated
        assert data["data_source"]["is_simulated"] is True

        # Disclaimers must explicitly state this is not a live Domo connection
        disclaimers = data["disclaimers"]
        assert len(disclaimers) >= 2
        disclaimer_text = " ".join(disclaimers).lower()
        assert (
            "simulated" in disclaimer_text
            or "mock" in disclaimer_text
            or "proof of concept" in disclaimer_text
        )
        assert "no real" in disclaimer_text or "not" in disclaimer_text

        # Limitations must state no live Domo
        limitations_text = " ".join(data["limitations"]).lower()
        assert (
            "simulated" in limitations_text
            or "not a live" in limitations_text
            or "mock" in limitations_text
        )


@pytest.mark.asyncio
async def test_rejection_boundary_no_production_readiness_implication() -> None:
    """Rejection Boundary: The technical view must NOT imply production readiness or live Domo access."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent/technical-architecture")
        assert response.status_code == 200
        data = response.json()

        full_text = (
            data["overview"]
            + " "
            + data["data_source"]["description"]
            + " "
            + data["future_integration"]
            + " "
            + " ".join(data["limitations"])
            + " "
            + " ".join(data["disclaimers"])
        ).lower()

        # Must NOT claim production readiness
        assert "production ready" not in full_text
        assert (
            "live domo" not in full_text
            or "not" in full_text.split("live domo")[0][-20:]
        )

        # Must explicitly state this is a POC / simulation
        assert (
            "proof-of-concept" in full_text
            or "proof of concept" in full_text
            or "poc" in full_text
        )


@pytest.mark.asyncio
async def test_technical_architecture_endpoint_structure() -> None:
    """Verify the /api/agent/technical-architecture endpoint returns a well-structured response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent/technical-architecture")
        assert response.status_code == 200
        data = response.json()

        # Required top-level fields
        assert "report_title" in data
        assert "overview" in data
        assert "data_source" in data
        assert "numerical_analysis" in data
        assert "ai_interpretation" in data
        assert "evidence_grounding" in data
        assert "data_flow" in data
        assert "separation_of_responsibilities" in data
        assert "limitations" in data
        assert "future_integration" in data
        assert "disclaimers" in data

        # Each layer must have required fields
        for layer_key in [
            "data_source",
            "numerical_analysis",
            "ai_interpretation",
            "evidence_grounding",
        ]:
            layer = data[layer_key]
            assert "name" in layer
            assert "description" in layer
            assert "components" in layer
            assert "is_simulated" in layer

        # Data flow steps must be ordered
        steps = data["data_flow"]
        assert len(steps) >= 4
        for i, step in enumerate(steps):
            assert step["step"] == i + 1
            assert "name" in step
            assert "description" in step
            assert "source_component" in step
            assert "output_component" in step

        # Future integration must explain the replacement path
        assert (
            "MockDomoMCPServer" in data["future_integration"]
            or "mock" in data["future_integration"].lower()
        )
        assert len(data["future_integration"]) > 100


@pytest.mark.asyncio
async def test_evidence_grounding_layer_present() -> None:
    """Verify the evidence grounding layer explains the reconciliation mechanism."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent/technical-architecture")
        assert response.status_code == 200
        data = response.json()

        grounding = data["evidence_grounding"]
        assert (
            "grounding" in grounding["name"].lower()
            or "reconciliation" in grounding["name"].lower()
        )
        assert "NumericalGroundingReconciler" in " ".join(grounding["components"])
        assert grounding["is_simulated"] is False
