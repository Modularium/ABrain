from __future__ import annotations

"""Shared service helpers for CLI and API."""

import asyncio
from typing import Any, Dict

from agentnn.deployment.agent_registry import AgentRegistry
from core.execution import ExecutionDispatcher
from core.models import RequesterIdentity, RequesterType, ToolExecutionRequest
from core.model_context import ModelContext
from core.tools import build_default_registry
from managers.agent_optimizer import AgentOptimizer
from managers.model_manager import ModelManager
from sdk.client import AgentClient

__all__ = [
    "create_agent",
    "dispatch_task",
    "evaluate_agent",
    "execute_tool",
    "list_agents",
    "load_model",
    "train_model",
]

DEFAULT_REQUESTER = RequesterIdentity(
    type=RequesterType.AGENT,
    id="services.core",
)


def _build_dispatcher() -> ExecutionDispatcher:
    """Create the fixed execution dispatcher used by service helpers."""
    return ExecutionDispatcher(build_default_registry(client_factory=AgentClient))


def execute_tool(
    tool_name: str,
    payload: Dict[str, Any] | None = None,
    *,
    requested_by: RequesterIdentity | None = None,
    run_id: str | None = None,
    correlation_id: str | None = None,
) -> Dict[str, Any]:
    """Execute a fixed internal tool with typed validation."""
    request = ToolExecutionRequest.from_raw(
        tool_name=tool_name,
        payload=payload or {},
        requested_by=requested_by or DEFAULT_REQUESTER,
        run_id=run_id,
        correlation_id=correlation_id,
    )
    result = _build_dispatcher().execute_sync(request)
    return result.output


def create_agent(
    config: Dict[str, Any], endpoint: str = "http://localhost:8090"
) -> Dict[str, Any]:
    """Register ``config`` with the MCP agent registry."""
    registry = AgentRegistry(endpoint)
    return registry.deploy(config)


def dispatch_task(ctx: ModelContext) -> Dict[str, Any]:
    """Dispatch ``ctx`` through the fixed tool execution layer."""
    description = None
    if ctx.task_context is not None:
        description = getattr(ctx.task_context.description, "text", ctx.task_context.description)
    payload = {
        "task": description or getattr(ctx, "task", "") or "",
        "task_type": getattr(ctx.task_context, "task_type", None)
        if ctx.task_context
        else None,
        "session_id": getattr(ctx, "session_id", None),
        "task_value": getattr(ctx, "task_value", None),
        "max_tokens": getattr(ctx, "max_tokens", None),
        "priority": getattr(ctx, "priority", None),
        "deadline": getattr(ctx, "deadline", None),
    }
    return execute_tool("dispatch_task", payload)


def list_agents() -> Dict[str, Any]:
    """List agents through the fixed tool execution layer."""
    return execute_tool("list_agents", {})


def evaluate_agent(agent_id: str) -> Dict[str, Any]:
    """Return evaluation metrics for ``agent_id``."""
    optimizer = AgentOptimizer()
    return asyncio.run(optimizer.evaluate_agent(agent_id))


def load_model(
    name: str,
    type: str,
    source: str,
    config: Dict[str, Any],
    version: str | None = None,
) -> Dict[str, Any]:
    """Load a model using :class:`ModelManager`."""
    manager = ModelManager()
    return asyncio.run(manager.load_model(name, type, source, config, version))


def train_model(args: Any) -> Any:
    """Run the training routine with ``args``."""
    from training.train import train

    return train(args)
