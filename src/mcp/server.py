"""Mock Domo Model Context Protocol (MCP) Server.

Exposes an MCP-style tool interface for retrieving facility operational data.
Satisfies Story 1.2 acceptance criteria:
- AC-1.2.1: The agent can retrieve required facility datasets through the mock interface.
- AC-1.2.2: The application explicitly identifies the interface as simulated and does not claim a live Domo connection.
- Rejection / Boundary: No real Domo credentials required, no PHI leaked, tools reject invalid arguments.
- Failure Behavior: Unavailable mock data produces explicit DATA_UNAVAILABLE response.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from src.data.loader import (
    DatasetUnavailableError,
    DatasetValidationError,
    FacilityDataLoader,
)
from src.mcp.schemas import (
    DomoConnectionStatus,
    MCPToolCallRequest,
    MCPToolCallResponse,
    MCPToolDefinition,
    MCPToolParameterSchema,
)

SUPPORTED_SCENARIOS = {
    "baseline",
    "staffing_stress",
    "auth_cliff",
    "hospital_transfer_spike",
    "therapy_disruption",
    "high_census_strain",
}


def _validate_scenario(scenario: Any) -> str:
    """Validate that scenario name is recognized."""
    if scenario is None:
        return "baseline"
    scenario_str = str(scenario).strip().lower()
    if scenario_str not in SUPPORTED_SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. Supported scenarios: {sorted(SUPPORTED_SCENARIOS)}"
        )
    return scenario_str


class MockDomoMCPServer:
    """In-process MCP Server implementing Mock Domo facility data tools."""

    def __init__(self, data_loader: FacilityDataLoader | None = None):
        self.data_loader = data_loader or FacilityDataLoader()
        self.connection_status = DomoConnectionStatus(
            supported_facilities_count=len(self.data_loader.get_supported_facilities())
        )
        self._tools: dict[str, MCPToolDefinition] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default bounded MCP tools for facility operational decision support."""
        # 1. domo_list_facilities
        self.register_tool(
            definition=MCPToolDefinition(
                name="domo_list_facilities",
                description="List all available medical facilities with bed capacities, active wings, and metadata.",
                category="facility_discovery",
                is_read_only=True,
                parameters=MCPToolParameterSchema(
                    type="object",
                    properties={},
                    required=[],
                ),
            ),
            handler=self._handle_list_facilities,
        )

        # 2. domo_get_facility_snapshot
        self.register_tool(
            definition=MCPToolDefinition(
                name="domo_get_facility_snapshot",
                description="Retrieve the latest daily operational snapshot covering all 8 operational domains for a facility.",
                category="facility_data",
                is_read_only=True,
                parameters=MCPToolParameterSchema(
                    type="object",
                    properties={
                        "facility_id": {
                            "type": "string",
                            "description": "Unique facility ID (e.g. 'ignite-oak-brook', 'ignite-mokena', 'ignite-kansas-city')",
                        },
                        "scenario": {
                            "type": "string",
                            "description": "Operational scenario (e.g. 'baseline', 'staffing_stress', 'auth_cliff', 'hospital_transfer_spike')",
                            "default": "baseline",
                        },
                    },
                    required=["facility_id"],
                ),
            ),
            handler=self._handle_get_snapshot,
        )

        # 3. domo_get_facility_history
        self.register_tool(
            definition=MCPToolDefinition(
                name="domo_get_facility_history",
                description="Retrieve chronologically sorted daily historical snapshots for multi-day trend and change analysis.",
                category="facility_data",
                is_read_only=True,
                parameters=MCPToolParameterSchema(
                    type="object",
                    properties={
                        "facility_id": {
                            "type": "string",
                            "description": "Unique facility ID",
                        },
                        "days_history": {
                            "type": "integer",
                            "description": "Number of daily observations to retrieve (e.g. 7, 14, 30, 90)",
                            "default": 90,
                        },
                        "scenario": {
                            "type": "string",
                            "description": "Operational scenario name",
                            "default": "baseline",
                        },
                    },
                    required=["facility_id"],
                ),
            ),
            handler=self._handle_get_history,
        )

        # 4. domo_get_domain_metrics
        self.register_tool(
            definition=MCPToolDefinition(
                name="domo_get_domain_metrics",
                description="Retrieve targeted operational metrics for a specific domain (census, staffing, therapy, payer_auth, hospitality, hospital_transfers, length_of_stay, admissions_discharges).",
                category="facility_data",
                is_read_only=True,
                parameters=MCPToolParameterSchema(
                    type="object",
                    properties={
                        "facility_id": {
                            "type": "string",
                            "description": "Unique facility ID",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Operational domain name (e.g. 'census', 'staffing', 'therapy', 'payer_auth', 'hospitality', 'hospital_transfers', 'length_of_stay', 'admissions_discharges')",
                        },
                        "scenario": {
                            "type": "string",
                            "description": "Operational scenario name",
                            "default": "baseline",
                        },
                    },
                    required=["facility_id", "domain"],
                ),
            ),
            handler=self._handle_get_domain_metrics,
        )

        # 5. domo_get_connection_status
        self.register_tool(
            definition=MCPToolDefinition(
                name="domo_get_connection_status",
                description="Retrieve integration metadata, mock connection status, and transparency disclaimers for the Domo boundary.",
                category="system_observability",
                is_read_only=True,
                parameters=MCPToolParameterSchema(
                    type="object",
                    properties={},
                    required=[],
                ),
            ),
            handler=self._handle_get_connection_status,
        )

    def register_tool(
        self, definition: MCPToolDefinition, handler: Callable[[dict[str, Any]], Any]
    ) -> None:
        """Register an MCP tool definition and execution handler."""
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def list_tools(self) -> list[MCPToolDefinition]:
        """Return list of all registered MCP tools."""
        return list(self._tools.values())

    def get_tool_definition(self, tool_name: str) -> MCPToolDefinition | None:
        """Get definition for a specific MCP tool."""
        return self._tools.get(tool_name)

    def call_tool(self, request: MCPToolCallRequest) -> MCPToolCallResponse:
        """Execute an MCP tool and return a machine-verifiable execution receipt."""
        start_time = time.perf_counter()
        receipt_id = f"REC-DOMO-{int(time.time())}-{uuid.uuid4().hex[:6]}"

        if request.tool_name not in self._handlers:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return MCPToolCallResponse(
                receipt_id=receipt_id,
                request_id=request.request_id,
                tool_name=request.tool_name,
                success=False,
                data=None,
                error=f"Tool '{request.tool_name}' not found. Available tools: {list(self._tools.keys())}",
                error_code="UNKNOWN_TOOL",
                execution_time_ms=elapsed_ms,
                connection_info=self.connection_status,
            )

        handler = self._handlers[request.tool_name]
        try:
            result_data = handler(request.arguments)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return MCPToolCallResponse(
                receipt_id=receipt_id,
                request_id=request.request_id,
                tool_name=request.tool_name,
                success=True,
                data=result_data,
                error=None,
                error_code=None,
                execution_time_ms=elapsed_ms,
                connection_info=self.connection_status,
            )
        except DatasetUnavailableError as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return MCPToolCallResponse(
                receipt_id=receipt_id,
                request_id=request.request_id,
                tool_name=request.tool_name,
                success=False,
                data=None,
                error=str(e),
                error_code="DATA_UNAVAILABLE",
                execution_time_ms=elapsed_ms,
                connection_info=self.connection_status,
            )
        except (DatasetValidationError, ValueError, TypeError) as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return MCPToolCallResponse(
                receipt_id=receipt_id,
                request_id=request.request_id,
                tool_name=request.tool_name,
                success=False,
                data=None,
                error=str(e),
                error_code="INVALID_ARGUMENT",
                execution_time_ms=elapsed_ms,
                connection_info=self.connection_status,
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return MCPToolCallResponse(
                receipt_id=receipt_id,
                request_id=request.request_id,
                tool_name=request.tool_name,
                success=False,
                data=None,
                error=f"Unexpected internal MCP error: {e!s}",
                error_code="INTERNAL_ERROR",
                execution_time_ms=elapsed_ms,
                connection_info=self.connection_status,
            )

    # ------------------ Tool Handlers ------------------

    def _handle_list_facilities(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        facilities = self.data_loader.get_supported_facilities()
        return [f.model_dump() for f in facilities]

    def _handle_get_snapshot(self, args: dict[str, Any]) -> dict[str, Any]:
        facility_id = args.get("facility_id")
        if not facility_id:
            raise ValueError("Argument 'facility_id' is required")
        scenario = _validate_scenario(args.get("scenario", "baseline"))
        snapshot = self.data_loader.get_snapshot(
            facility_id=facility_id, scenario=scenario
        )
        return snapshot.model_dump(mode="json")

    def _handle_get_history(self, args: dict[str, Any]) -> dict[str, Any]:
        facility_id = args.get("facility_id")
        if not facility_id:
            raise ValueError("Argument 'facility_id' is required")

        raw_days = args.get("days_history", 30)
        if raw_days is None:
            raise ValueError(
                "Argument 'days_history' cannot be None; must be an integer between 1 and 365"
            )
        try:
            days = int(raw_days)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Argument 'days_history' must be a valid integer, got {raw_days!r}"
            ) from e

        if days < 1 or days > 365:
            raise ValueError(
                f"Argument 'days_history' must be between 1 and 365, got {days}"
            )
        scenario = _validate_scenario(args.get("scenario", "baseline"))
        dataset = self.data_loader.load_dataset(
            facility_id=facility_id, scenario=scenario, days_history=days
        )
        return dataset.history.model_dump(mode="json")

    def _handle_get_domain_metrics(self, args: dict[str, Any]) -> dict[str, Any]:
        facility_id = args.get("facility_id")
        domain = args.get("domain")
        if not facility_id:
            raise ValueError("Argument 'facility_id' is required")
        if not domain:
            raise ValueError("Argument 'domain' is required")

        scenario = _validate_scenario(args.get("scenario", "baseline"))
        snapshot = self.data_loader.get_snapshot(
            facility_id=facility_id, scenario=scenario
        )

        domain_attr_map = {
            "census": snapshot.census,
            "occupancy": snapshot.census,
            "admissions_discharges": snapshot.admissions_discharges,
            "length_of_stay": snapshot.length_of_stay,
            "los": snapshot.length_of_stay,
            "therapy": snapshot.therapy,
            "staffing": snapshot.staffing,
            "payer_auth": snapshot.payer_auth,
            "payer": snapshot.payer_auth,
            "hospitality": snapshot.hospitality,
            "hospital_transfers": snapshot.hospital_transfers,
            "transfers": snapshot.hospital_transfers,
        }

        domain_key = domain.lower().strip()
        if domain_key not in domain_attr_map:
            raise ValueError(
                f"Unknown domain '{domain}'. Supported domains: "
                f"{['census', 'admissions_discharges', 'length_of_stay', 'therapy', 'staffing', 'payer_auth', 'hospitality', 'hospital_transfers']}"
            )

        domain_obj = domain_attr_map[domain_key]
        return {
            "facility_id": facility_id,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "domain": domain_key,
            "metrics": domain_obj.model_dump(mode="json"),
        }

    def _handle_get_connection_status(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.connection_status.model_dump(mode="json")
