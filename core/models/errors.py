"""Structured errors for core execution flows."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CoreErrorCode(str, Enum):
    """Stable error codes for tool execution."""

    UNKNOWN_TOOL = "unknown_tool"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"


class StructuredError(BaseModel):
    """Serializable error payload with execution context."""

    model_config = ConfigDict(extra="forbid")

    error_code: CoreErrorCode | str = Field(
        validation_alias=AliasChoices("error_code", "code"),
        serialization_alias="error_code",
    )
    message: str
    tool_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    audit_ref: str | None = None
    warnings: list[str] | None = None
    run_id: str | None = None
    correlation_id: str | None = None

    @property
    def code(self) -> CoreErrorCode | str:
        """Backward-compatible alias for older call sites."""
        return self.error_code


class CoreExecutionError(Exception):
    """Exception wrapper used by the execution dispatcher."""

    def __init__(self, error: StructuredError) -> None:
        super().__init__(error.message)
        self.error = error
