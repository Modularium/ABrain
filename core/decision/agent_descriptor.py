"""Canonical agent descriptor models for ABrain."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentSourceType(StrEnum):
    """Origin of the agent definition."""

    NATIVE = "native"
    FLOWISE = "flowise"
    N8N = "n8n"
    OPENHANDS = "openhands"
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    ADMINBOT = "adminbot"


class AgentExecutionKind(StrEnum):
    """Execution style for the agent."""

    LOCAL_PROCESS = "local_process"
    HTTP_SERVICE = "http_service"
    CLOUD_AGENT = "cloud_agent"
    WORKFLOW_ENGINE = "workflow_engine"
    SYSTEM_EXECUTOR = "system_executor"


class AgentTrustLevel(StrEnum):
    """Operational trust level."""

    UNKNOWN = "unknown"
    SANDBOXED = "sandboxed"
    TRUSTED = "trusted"
    PRIVILEGED = "privileged"


class AgentCostProfile(StrEnum):
    """Very small V1 cost profile."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VARIABLE = "variable"


class AgentLatencyProfile(StrEnum):
    """Expected latency profile."""

    UNKNOWN = "unknown"
    INTERACTIVE = "interactive"
    BACKGROUND = "background"
    BATCH = "batch"


class AgentAvailability(StrEnum):
    """Current availability expectation."""

    UNKNOWN = "unknown"
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class AgentDescriptor(BaseModel):
    """Canonical ABrain agent descriptor."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    source_type: AgentSourceType = AgentSourceType.NATIVE
    execution_kind: AgentExecutionKind = AgentExecutionKind.HTTP_SERVICE
    capabilities: list[str] = Field(default_factory=list)
    trust_level: AgentTrustLevel = AgentTrustLevel.SANDBOXED
    cost_profile: AgentCostProfile = AgentCostProfile.UNKNOWN
    latency_profile: AgentLatencyProfile = AgentLatencyProfile.UNKNOWN
    availability: AgentAvailability = AgentAvailability.UNKNOWN
    editable_in_flowise: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("agent_id", "display_name")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        """Reject blank values and normalize whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("capabilities")
    @classmethod
    def normalize_capabilities(cls, value: list[str]) -> list[str]:
        """Normalize capability ids while preserving order."""
        seen: set[str] = set()
        normalized_capabilities: list[str] = []
        for capability_id in value:
            normalized = capability_id.strip()
            if not normalized:
                raise ValueError("capabilities must not contain empty values")
            if normalized not in seen:
                seen.add(normalized)
                normalized_capabilities.append(normalized)
        return normalized_capabilities
