"""Typed models for the AdminBot adapter surface."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminBotStatusTarget(str, Enum):
    """Allowed targets for status lookups."""

    DAEMON = "daemon"
    SUMMARY = "summary"


class AdminBotGetStatusInput(BaseModel):
    """Input model for ``adminbot_get_status``."""

    model_config = ConfigDict(extra="forbid")

    target: AdminBotStatusTarget = AdminBotStatusTarget.SUMMARY


class AdminBotGetHealthInput(BaseModel):
    """Input model for ``adminbot_get_health``."""

    model_config = ConfigDict(extra="forbid")

    include_checks: bool = True


class AdminBotGetServiceStatusInput(BaseModel):
    """Input model for ``adminbot_get_service_status``."""

    model_config = ConfigDict(extra="forbid")

    service_name: str = Field(..., min_length=1, max_length=128)
    allow_nonsystem: bool = False

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
    action: Literal["get_status", "get_health", "get_service_status"]
    requested_by: AdminBotRequestedBy
    payload: dict[str, Any]
    run_id: str | None = None
    correlation_id: str | None = None


class AdminBotErrorPayload(BaseModel):
    """Structured error returned by AdminBot."""

    model_config = ConfigDict(extra="forbid")

    error_code: str
    message: str
    details: dict[str, Any] | None = None
    audit_ref: str | None = None
    warnings: list[str] | None = None


class AdminBotSuccessPayload(BaseModel):
    """Structured success payload returned by AdminBot."""

    model_config = ConfigDict(extra="forbid")

    ok: Literal[True] = True
    result: dict[str, Any]
    warnings: list[str] | None = None
    audit_ref: str | None = None
