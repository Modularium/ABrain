"""Execution dispatcher for fixed internal tools."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from pydantic import ValidationError

from core.models.errors import CoreErrorCode, CoreExecutionError, StructuredError
from core.models.tooling import ToolExecutionRequest, ToolExecutionResult
from core.tools.registry import ToolRegistry


async def maybe_await(value: Any) -> Any:
    """Await ``value`` when needed and return it unchanged otherwise."""
    if inspect.isawaitable(value):
        return await value
    return value


def run_sync(value: Any) -> Any:
    """Synchronously resolve possibly awaitable values."""
    if inspect.isawaitable(value):
        return asyncio.run(value)
    return value


class ExecutionDispatcher:
    """Validate tool calls and dispatch them to fixed handlers."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute a validated tool request."""
        try:
            definition = self.registry.get(request.tool_name)
        except KeyError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code=CoreErrorCode.UNKNOWN_TOOL,
                    message=f"Unknown tool: {request.tool_name}",
                    tool_name=request.tool_name,
                    run_id=request.run_id,
                    correlation_id=request.correlation_id,
                )
            ) from exc

        try:
            tool_input = definition.input_model.model_validate(request.payload)
        except ValidationError as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid input for tool: {request.tool_name}",
                    tool_name=request.tool_name,
                    details={"errors": exc.errors()},
                    run_id=request.run_id,
                    correlation_id=request.correlation_id,
                )
            ) from exc

        try:
            output = await maybe_await(definition.handler(request, tool_input))
        except CoreExecutionError:
            raise
        except Exception as exc:
            raise CoreExecutionError(
                StructuredError(
                    error_code=CoreErrorCode.EXECUTION_ERROR,
                    message=f"Tool execution failed: {request.tool_name}",
                    tool_name=request.tool_name,
                    details={"exception": str(exc)},
                    run_id=request.run_id,
                    correlation_id=request.correlation_id,
                )
            ) from exc

        return ToolExecutionResult(
            tool_name=request.tool_name,
            ok=True,
            output=output,
            requested_by=request.requested_by,
            run_id=request.run_id,
            correlation_id=request.correlation_id,
        )

    def execute_sync(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Synchronously execute a tool request."""
        return run_sync(self.execute(request))
