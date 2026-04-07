"""Typed tool request and response models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import CoreErrorCode, CoreExecutionError, StructuredError
from .identity import RequesterIdentity


class BaseToolInput(BaseModel):
    """Base class for validated tool inputs."""

    model_config = ConfigDict(extra="forbid")


class EmptyToolInput(BaseToolInput):
    """Placeholder model for tools without input."""


class InternalTaskType(str, Enum):
    """Fixed internal task types allowed through the hardened tool surface."""

    CHAT = "chat"
    DEV = "dev"
    DOCKER = "docker"
    CONTAINER_OPS = "container_ops"
    SEMANTIC = "semantic"
    QA = "qa"
    SEARCH = "search"


class DispatchTaskToolInput(BaseToolInput):
    """Validated input for task dispatching."""

    task: str = Field(min_length=1)
    task_type: InternalTaskType
    session_id: str | None = None
    task_value: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    priority: int | None = None
    deadline: str | None = None


class ListAgentsToolInput(BaseToolInput):
    """Validated input for listing agents."""


class ToolExecutionRequest(BaseModel):
    """Envelope for a fixed tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: RequesterIdentity
    run_id: str | None = None
    correlation_id: str | None = None

    @classmethod
    def from_raw(cls, **data: Any) -> "ToolExecutionRequest":
        """Validate a raw request and raise a structured error on failure."""
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            tool_name = data.get("tool_name")
            run_id = data.get("run_id")
            correlation_id = data.get("correlation_id")
            raise CoreExecutionError(
                StructuredError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message="Invalid tool execution request",
                    tool_name=tool_name if isinstance(tool_name, str) else None,
                    details={"errors": exc.errors()},
                    run_id=run_id if isinstance(run_id, str) else None,
                    correlation_id=correlation_id if isinstance(correlation_id, str) else None,
                )
            ) from exc


class ToolExecutionResult(BaseModel):
    """Structured execution result."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    ok: bool = True
    output: Any | None = None
    error: StructuredError | None = None
    requested_by: RequesterIdentity
    run_id: str | None = None
    correlation_id: str | None = None
