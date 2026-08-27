"""Mock Domo Model Context Protocol (MCP) Client.

Provides a typed Python interface for AI agents, decision engines, and API endpoints
to invoke Mock Domo MCP tools with machine-verifiable receipt capture.
"""

from __future__ import annotations

from typing import Any

from src.mcp.schemas import (
    DomoConnectionStatus,
    MCPToolCallRequest,
    MCPToolCallResponse,
    MCPToolDefinition,
)
from src.mcp.server import MockDomoMCPServer
from src.models.facility import (
    DailyFacilitySnapshot,
    FacilityHistoricalSeries,
    FacilityMetadata,
)


class MockDomoMCPClient:
    """Client for invoking Mock Domo MCP tools."""

    def __init__(self, server: MockDomoMCPServer | None = None):
        self.server = server or MockDomoMCPServer()
        self._last_receipt: MCPToolCallResponse | None = None

    @property
    def last_receipt(self) -> MCPToolCallResponse | None:
        """Return receipt from most recent tool call."""
        return self._last_receipt

    def get_tools(self) -> list[MCPToolDefinition]:
        """List available MCP tools."""
        return self.server.list_tools()

    def get_connection_status(self) -> DomoConnectionStatus:
        """Retrieve simulated connection status and disclaimers."""
        req = MCPToolCallRequest(tool_name="domo_get_connection_status")
        resp = self.server.call_tool(req)
        self._last_receipt = resp
        if not resp.success:
            raise RuntimeError(f"Failed to fetch connection status: {resp.error}")
        return DomoConnectionStatus.model_validate(resp.data)

    def list_facilities(self) -> list[FacilityMetadata]:
        """Retrieve list of available facilities."""
        req = MCPToolCallRequest(tool_name="domo_list_facilities")
        resp = self.server.call_tool(req)
        self._last_receipt = resp
        if not resp.success:
            raise RuntimeError(f"Failed to list facilities: {resp.error}")
        return [FacilityMetadata.model_validate(f) for f in resp.data]

    def get_facility_snapshot(
        self,
        facility_id: str,
        scenario: str = "baseline",
    ) -> DailyFacilitySnapshot:
        """Retrieve latest daily operational snapshot for a facility."""
        req = MCPToolCallRequest(
            tool_name="domo_get_facility_snapshot",
            arguments={"facility_id": facility_id, "scenario": scenario},
        )
        resp = self.server.call_tool(req)
        self._last_receipt = resp
        if not resp.success:
            raise RuntimeError(
                f"Failed to get snapshot for '{facility_id}': {resp.error}"
            )
        return DailyFacilitySnapshot.model_validate(resp.data)

    def get_facility_history(
        self,
        facility_id: str,
        days_history: int = 30,
        scenario: str = "baseline",
    ) -> FacilityHistoricalSeries:
        """Retrieve facility historical time-series via Mock Domo MCP."""
        req = MCPToolCallRequest(
            tool_name="domo_get_facility_history",
            arguments={
                "facility_id": facility_id,
                "days_history": days_history,
                "scenario": scenario,
            },
        )
        resp = self.server.call_tool(req)
        self._last_receipt = resp
        if not resp.success:
            raise RuntimeError(
                f"Failed to get history for '{facility_id}': {resp.error}"
            )

        return FacilityHistoricalSeries.model_validate(resp.data)

    def get_domain_metrics(
        self,
        facility_id: str,
        domain: str,
        scenario: str = "baseline",
    ) -> dict[str, Any]:
        """Retrieve metrics for a specific operational domain."""
        req = MCPToolCallRequest(
            tool_name="domo_get_domain_metrics",
            arguments={
                "facility_id": facility_id,
                "domain": domain,
                "scenario": scenario,
            },
        )
        resp = self.server.call_tool(req)
        self._last_receipt = resp
        if not resp.success:
            raise RuntimeError(
                f"Failed to get domain '{domain}' for '{facility_id}': {resp.error}"
            )
        return resp.data
