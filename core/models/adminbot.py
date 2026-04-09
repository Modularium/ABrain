"""Typed models for the AdminBot v2 adapter surface."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


AdminBotAction = Literal["system.status", "system.health", "service.status"]
AdminBotToolName = Literal[
    "adminbot_system_status",
    "adminbot_system_health",
    "adminbot_service_status",
]


class AdminBotSystemStatusInput(BaseModel):
    """Input model for ``adminbot_system_status``."""

    model_config = ConfigDict(extra="forbid")


class AdminBotSystemHealthInput(BaseModel):
    """Input model for ``adminbot_system_health``."""

    model_config = ConfigDict(extra="forbid")


class AdminBotServiceStatusInput(BaseModel):
    """Input model for ``adminbot_service_status``."""

    model_config = ConfigDict(extra="forbid")

    service_name: str = Field(..., min_length=1, max_length=128)

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, value: str) -> str:
        """Reject empty or unsafe service names."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("service_name must not be empty")

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@")
        if any(ch not in allowed for ch in normalized):
            raise ValueError("service_name contains invalid characters")

        return normalized


class AdminBotRequestedBy(BaseModel):
    """Requester envelope sent to AdminBot."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["agent"] = "agent"
    id: str = Field(min_length=1)


class AdminBotRequestEnvelope(BaseModel):
    """Strict wire request envelope for AdminBot IPC."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    correlation_id: str | None = None
    requested_by: AdminBotRequestedBy
    tool_name: AdminBotToolName
    agent_run_id: str | None = None
    action: AdminBotAction
    params: dict[str, Any]
    dry_run: Literal[False] = False
    timeout_ms: int = Field(default=5000, ge=1)


class AdminBotErrorPayload(BaseModel):
    """Structured error body returned by AdminBot v2."""

    model_config = ConfigDict(extra="allow")

    code: str
    message: str
    details: dict[str, Any] | None = None
    retryable: bool | None = None


class AdminBotErrorResponse(BaseModel):
    """Structured error envelope returned by AdminBot v2."""

    model_config = ConfigDict(extra="allow")

    request_id: str | None = None
    status: Literal["error"]
    error: AdminBotErrorPayload


class AdminBotSuccessPayload(BaseModel):
    """Structured non-error envelope returned by AdminBot v2."""

    model_config = ConfigDict(extra="allow")

    request_id: str | None = None
    status: str

    @field_validator("status")
    @classmethod
    def validate_non_error_status(cls, value: str) -> str:
        """Reject error responses in the success model."""
        if value == "error":
            raise ValueError("status must not be error")
        return value
