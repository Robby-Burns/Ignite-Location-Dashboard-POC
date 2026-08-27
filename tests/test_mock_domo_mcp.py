"""Unit and integration tests for Story 1.2 — Create Mock Domo MCP.

Verifies:
- AC-1.2.1: The agent can retrieve required facility datasets through the mock MCP interface.
- AC-1.2.2: The application explicitly states that the connection is simulated (no live Domo claim).
- Rejection / Boundary Conditions: No credentials required, argument validation, receipt IDs generated.
- Failure Behavior: Unavailable data produces explicit DATA_UNAVAILABLE response.
"""

from __future__ import annotations

import pytest

from src.mcp.client import MockDomoMCPClient
from src.mcp.schemas import MCPToolCallRequest
from src.mcp.server import MockDomoMCPServer


@pytest.fixture
def mcp_server() -> MockDomoMCPServer:
    return MockDomoMCPServer()


@pytest.fixture
def mcp_client(mcp_server: MockDomoMCPServer) -> MockDomoMCPClient:
    return MockDomoMCPClient(server=mcp_server)


def test_ac1_2_1_mcp_tool_retrieval_all_tools(mcp_server: MockDomoMCPServer) -> None:
    """AC-1.2.1: Verify the agent can retrieve required facility datasets via MCP tools."""
    # 1. Tool listing
    tools = mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    assert "domo_list_facilities" in tool_names
    assert "domo_get_facility_snapshot" in tool_names
    assert "domo_get_facility_history" in tool_names
    assert "domo_get_domain_metrics" in tool_names
    assert "domo_get_connection_status" in tool_names

    # 2. domo_list_facilities call
    resp_fac = mcp_server.call_tool(
        MCPToolCallRequest(tool_name="domo_list_facilities")
    )
    assert resp_fac.success is True
    assert resp_fac.receipt_id.startswith("REC-DOMO-")
    assert len(resp_fac.data) == 3
    fac_ids = [f["facility_id"] for f in resp_fac.data]
    assert "ignite-oak-brook" in fac_ids

    # 3. domo_get_facility_snapshot call
    resp_snap = mcp_server.call_tool(
        MCPToolCallRequest(
            tool_name="domo_get_facility_snapshot",
            arguments={"facility_id": "ignite-oak-brook", "scenario": "baseline"},
        )
    )
    assert resp_snap.success is True
    assert resp_snap.data["facility_id"] == "ignite-oak-brook"
    assert "census" in resp_snap.data
    assert "staffing" in resp_snap.data
    assert "therapy" in resp_snap.data
    assert "payer_auth" in resp_snap.data
    assert "hospitality" in resp_snap.data
    assert "hospital_transfers" in resp_snap.data

    # 4. domo_get_facility_history call
    resp_hist = mcp_server.call_tool(
        MCPToolCallRequest(
            tool_name="domo_get_facility_history",
            arguments={"facility_id": "ignite-oak-brook", "days_history": 14},
        )
    )
    assert resp_hist.success is True
    assert len(resp_hist.data["snapshots"]) == 14

    # 5. domo_get_domain_metrics call
    for domain in [
        "census",
        "staffing",
        "therapy",
        "payer_auth",
        "hospitality",
        "hospital_transfers",
    ]:
        resp_dom = mcp_server.call_tool(
            MCPToolCallRequest(
                tool_name="domo_get_domain_metrics",
                arguments={"facility_id": "ignite-oak-brook", "domain": domain},
            )
        )
        assert resp_dom.success is True
        assert resp_dom.data["domain"] == domain
        assert "metrics" in resp_dom.data


def test_ac1_2_2_connection_status_explicit_simulation_transparency(
    mcp_server: MockDomoMCPServer,
) -> None:
    """AC-1.2.2: Verify the mock interface explicitly identifies itself as simulated and disclaims live Domo connectivity."""
    resp = mcp_server.call_tool(
        MCPToolCallRequest(tool_name="domo_get_connection_status")
    )
    assert resp.success is True
    conn_info = resp.data

    # Explicit simulation checks
    assert conn_info["is_live_connection"] is False
    assert conn_info["connection_type"] == "SIMULATED_MOCK_DOMO_MCP"
    assert "Synthetic" in conn_info["data_source"]
    assert len(conn_info["disclaimers"]) >= 2
    disclaimer_text = " ".join(conn_info["disclaimers"]).lower()
    assert "proof of concept" in disclaimer_text or "simulation" in disclaimer_text
    assert "live domo" in disclaimer_text
    assert "not active" in disclaimer_text or "synthetic" in disclaimer_text


def test_rejection_boundary_invalid_arguments(mcp_server: MockDomoMCPServer) -> None:
    """Rejection / Boundary: Tool execution rejects missing required arguments and invalid domains."""
    # Missing facility_id
    resp1 = mcp_server.call_tool(
        MCPToolCallRequest(tool_name="domo_get_facility_snapshot", arguments={})
    )
    assert resp1.success is False
    assert resp1.error_code == "INVALID_ARGUMENT"
    assert "facility_id" in resp1.error

    # Unknown tool
    resp2 = mcp_server.call_tool(
        MCPToolCallRequest(tool_name="non_existent_tool", arguments={})
    )
    assert resp2.success is False
    assert resp2.error_code == "UNKNOWN_TOOL"

    # Invalid domain
    resp3 = mcp_server.call_tool(
        MCPToolCallRequest(
            tool_name="domo_get_domain_metrics",
            arguments={
                "facility_id": "ignite-oak-brook",
                "domain": "invalid_domain_xyz",
            },
        )
    )
    assert resp3.success is False
    assert resp3.error_code == "INVALID_ARGUMENT"
    assert "Unknown domain" in resp3.error

    # Invalid days_history
    resp4 = mcp_server.call_tool(
        MCPToolCallRequest(
            tool_name="domo_get_facility_history",
            arguments={"facility_id": "ignite-oak-brook", "days_history": 500},
        )
    )
    assert resp4.success is False
    assert resp4.error_code == "INVALID_ARGUMENT"

    # None days_history
    resp5 = mcp_server.call_tool(
        MCPToolCallRequest(
            tool_name="domo_get_facility_history",
            arguments={"facility_id": "ignite-oak-brook", "days_history": None},
        )
    )
    assert resp5.success is False
    assert resp5.error_code == "INVALID_ARGUMENT"

    # Invalid scenario
    resp6 = mcp_server.call_tool(
        MCPToolCallRequest(
            tool_name="domo_get_facility_snapshot",
            arguments={
                "facility_id": "ignite-oak-brook",
                "scenario": "invalid_scenario_123",
            },
        )
    )
    assert resp6.success is False
    assert resp6.error_code == "INVALID_ARGUMENT"
    assert "Unknown scenario" in resp6.error


def test_failure_behavior_unavailable_facility_returns_typed_error(
    mcp_server: MockDomoMCPServer,
) -> None:
    """Failure behavior: Querying non-existent facility produces normalized DATA_UNAVAILABLE receipt."""
    resp = mcp_server.call_tool(
        MCPToolCallRequest(
            tool_name="domo_get_facility_snapshot",
            arguments={"facility_id": "unknown-facility-id"},
        )
    )
    assert resp.success is False
    assert resp.error_code == "DATA_UNAVAILABLE"
    assert "not found" in resp.error.lower() or "not configured" in resp.error.lower()
    assert resp.receipt_id.startswith("REC-DOMO-")
    assert resp.connection_info.is_live_connection is False


def test_mcp_client_integration(mcp_client: MockDomoMCPClient) -> None:
    """Verify MockDomoMCPClient wrapper provides high-level typed access with receipts."""
    # Status
    status = mcp_client.get_connection_status()
    assert status.is_live_connection is False
    assert mcp_client.last_receipt is not None
    assert mcp_client.last_receipt.success is True

    # List facilities
    facilities = mcp_client.list_facilities()
    assert len(facilities) == 3
    assert facilities[0].facility_id == "ignite-oak-brook"

    # Snapshot
    snapshot = mcp_client.get_facility_snapshot("ignite-oak-brook", scenario="baseline")
    assert snapshot.facility_id == "ignite-oak-brook"
    assert snapshot.census.current_census > 0

    # History
    history_series = mcp_client.get_facility_history("ignite-oak-brook", days_history=7)
    assert len(history_series.snapshots) == 7

    # Domain metrics
    staffing_metrics = mcp_client.get_domain_metrics("ignite-oak-brook", "staffing")
    assert "hppd_actual" in staffing_metrics["metrics"]


@pytest.mark.asyncio
async def test_fastapi_rest_endpoints() -> None:
    """Verify FastAPI routes for MCP status, tools, tool execution, and facility data."""
    import httpx

    from src.api.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Health check
        resp_health = await client.get("/api/health")
        assert resp_health.status_code == 200
        assert resp_health.json()["status"] == "healthy"

        # MCP Status
        resp_status = await client.get("/api/mcp/status")
        assert resp_status.status_code == 200
        status_data = resp_status.json()
        assert status_data["is_live_connection"] is False
        assert status_data["connection_type"] == "SIMULATED_MOCK_DOMO_MCP"

        # MCP Tools list
        resp_tools = await client.get("/api/mcp/tools")
        assert resp_tools.status_code == 200
        tools_list = resp_tools.json()
        assert len(tools_list) == 5

        # MCP Tool Call endpoint
        resp_call = await client.post(
            "/api/mcp/call",
            json={"tool_name": "domo_list_facilities", "arguments": {}},
        )
        assert resp_call.status_code == 200
        call_result = resp_call.json()
        assert call_result["success"] is True
        assert call_result["receipt_id"].startswith("REC-DOMO-")
        assert len(call_result["data"]) == 3

        # Facilities REST list
        resp_fac = await client.get("/api/facilities")
        assert resp_fac.status_code == 200
        assert len(resp_fac.json()) == 3

        # Facility Snapshot
        resp_snap = await client.get("/api/facilities/ignite-oak-brook/snapshot")
        assert resp_snap.status_code == 200
        assert resp_snap.json()["facility_id"] == "ignite-oak-brook"

        # Facility History
        resp_hist = await client.get("/api/facilities/ignite-oak-brook/history?days=7")
        assert resp_hist.status_code == 200
        assert len(resp_hist.json()["snapshots"]) == 7
