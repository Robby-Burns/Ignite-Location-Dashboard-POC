"""Pydantic schemas for Model Context Protocol (MCP) tool server and client."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class MCPToolParameterSchema(BaseModel):
    """JSON Schema definition for MCP tool parameters."""

    type: str = "object"
    properties: dict[str, dict[str, Any]] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class MCPToolDefinition(BaseModel):
    """Definition of an MCP tool exposed by the Mock Domo MCP server."""

    name: str = Field(
        ..., description="Unique tool identifier, e.g. 'domo_get_facility_snapshot'"
    )
    description: str = Field(
        ..., description="Detailed description of tool purpose and behavior"
    )
    category: str = Field(
        default="facility_data", description="Tool category classification"
    )
    is_read_only: bool = Field(
        default=True, description="Whether tool performs read-only operations"
    )
    parameters: MCPToolParameterSchema = Field(
        default_factory=MCPToolParameterSchema,
        description="JSON schema describing tool arguments",
    )


class MCPToolCallRequest(BaseModel):
    """Request payload to execute an MCP tool."""

    tool_name: str = Field(..., description="Name of the MCP tool to execute")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Key-value tool input arguments"
    )
    request_id: str | None = Field(
        None, description="Optional client-provided correlation ID"
    )


class DomoConnectionStatus(BaseModel):
    """Connection status and boundary information for Mock Domo MCP."""

    is_live_connection: bool = Field(
        default=False, description="Whether this is a live production Domo connection"
    )
    connection_type: str = Field(
        default="SIMULATED_MOCK_DOMO_MCP", description="Integration boundary type"
    )
    provider: str = Field(
        default="Ignite Domo Gateway Simulation", description="Provider description"
    )
    data_source: str = Field(
        default="Synthetic Facility Operations Dataset",
        description="Underlying data generator/source",
    )
    version: str = Field(default="1.0.0-mock", description="Mock adapter version")
    supported_facilities_count: int = Field(
        default=3, description="Number of configured facilities"
    )
    disclaimers: list[str] = Field(
        default_factory=lambda: [
            "Proof of Concept simulation: Live Domo MCP access is not active.",
            "All facility metrics, census numbers, and operational records are synthetic.",
            "No real patient identifiers, protected health information (PHI), or production API credentials are used.",
        ],
        description="Mandatory transparency disclaimers",
    )


class MCPToolCallResponse(BaseModel):
    """Authoritative execution response and receipt for an MCP tool call."""

    receipt_id: str = Field(
        ...,
        description="Unique deterministic execution receipt ID, e.g. 'REC-DOMO-20260827-001'",
    )
    request_id: str | None = Field(None, description="Client correlation ID")
    tool_name: str = Field(..., description="Executed tool name")
    success: bool = Field(..., description="Whether tool execution succeeded")
    data: Any | None = Field(None, description="Structured output payload on success")
    error: str | None = Field(None, description="Normalized error message on failure")
    error_code: str | None = Field(
        None, description="Machine-readable error category, e.g. 'DATA_UNAVAILABLE'"
    )
    execution_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of execution",
    )
    execution_time_ms: float = Field(
        ..., ge=0.0, description="Execution duration in milliseconds"
    )
    connection_info: DomoConnectionStatus = Field(
        default_factory=DomoConnectionStatus,
        description="Mock connection status metadata",
    )
