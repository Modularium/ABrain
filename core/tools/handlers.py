"""Handlers for the fixed internal tool set."""

from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace
from typing import Any, Callable

from adapters.adminbot.service import AdminBotService
from core.models.adminbot import (
    AdminBotServiceStatusInput,
    AdminBotSystemHealthInput,
    AdminBotSystemStatusInput,
)
from core.models.tooling import (
    DispatchTaskToolInput,
    EmptyToolInput,
    InternalTaskType,
    ListAgentsToolInput,
    ToolExecutionRequest,
)

from .registry import ToolDefinition, ToolRegistry

_adminbot_service = AdminBotService.from_config()


def _build_context(task: str, session_id: str | None = None):
    """Build a minimal ``ModelContext`` without importing the SDK package."""
    model_context_module = import_module("core.model_context")
    model_context_cls = getattr(model_context_module, "ModelContext", None)
    task_context_cls = getattr(model_context_module, "TaskContext", None)

    if task_context_cls is None:
        task_context = SimpleNamespace(task_type=InternalTaskType.CHAT.value, description=task)
    else:
        task_context = task_context_cls(task_type=InternalTaskType.CHAT.value, description=task)

    if model_context_cls is None:
        return SimpleNamespace(session_id=session_id, task=task, task_context=task_context)

    try:
        return model_context_cls(session_id=session_id, task=task, task_context=task_context)
    except TypeError:
        return SimpleNamespace(session_id=session_id, task=task, task_context=task_context)


def _default_client_factory():
    """Import the SDK client lazily to keep the core layer lightweight."""
    from sdk.client import AgentClient

    return AgentClient()


def dispatch_task_tool(
    _tool_request: ToolExecutionRequest,
    tool_input: DispatchTaskToolInput,
    client_factory: Callable[[], Any] | None = None,
):
    """Dispatch a task using the existing SDK client."""
    context = _build_context(tool_input.task, session_id=tool_input.session_id)
    context.task_context.task_type = tool_input.task_type.value
    context.task_value = tool_input.task_value
    context.max_tokens = tool_input.max_tokens
    context.priority = tool_input.priority
    context.deadline = tool_input.deadline
    # Keep the historical SDK-facing contract stable even when ``TaskContext``
    # normalizes string descriptions into richer wrapper objects internally.
    if hasattr(context.task_context, "description"):
        context.task_context.description = getattr(
            context.task_context.description,
            "text",
            context.task_context.description,
        )
    factory = client_factory or _default_client_factory
    return factory().dispatch_task(context)


def list_agents_tool(
    _tool_request: ToolExecutionRequest,
    _tool_input: ListAgentsToolInput | EmptyToolInput,
    client_factory: Callable[[], Any] | None = None,
):
    """List registered agents using the existing SDK client."""
    factory = client_factory or _default_client_factory
    return factory().list_agents()


def handle_adminbot_system_status(
    tool_request: ToolExecutionRequest,
    payload: AdminBotSystemStatusInput,
):
    """Handle ``adminbot_system_status``."""
    return _adminbot_service.system_status(tool_request, payload)


def handle_adminbot_system_health(
    tool_request: ToolExecutionRequest,
    payload: AdminBotSystemHealthInput,
):
    """Handle ``adminbot_system_health``."""
    return _adminbot_service.system_health(tool_request, payload)


def handle_adminbot_service_status(
    tool_request: ToolExecutionRequest,
    payload: AdminBotServiceStatusInput,
):
    """Handle ``adminbot_service_status``."""
    return _adminbot_service.service_status(tool_request, payload)


def build_default_registry(
    client_factory: Callable[[], Any] | None = None,
) -> ToolRegistry:
    """Return the fixed tool registry used by the execution dispatcher."""
    return ToolRegistry(
        definitions=[
            ToolDefinition(
                name="dispatch_task",
                description="Dispatch a task through the internal task dispatcher.",
                input_model=DispatchTaskToolInput,
                handler=lambda tool_request, tool_input: dispatch_task_tool(
                    tool_request,
                    tool_input,
                    client_factory=client_factory,
                ),
            ),
            ToolDefinition(
                name="list_agents",
                description="List registered agents via the internal registry API.",
                input_model=ListAgentsToolInput,
                handler=lambda tool_request, tool_input: list_agents_tool(
                    tool_request,
                    tool_input,
                    client_factory=client_factory,
                ),
            ),
            ToolDefinition(
                name="adminbot_system_status",
                description="Get system-level status from AdminBot v2.",
                input_model=AdminBotSystemStatusInput,
                handler=handle_adminbot_system_status,
            ),
            ToolDefinition(
                name="adminbot_system_health",
                description="Get system-level health from AdminBot v2.",
                input_model=AdminBotSystemHealthInput,
                handler=handle_adminbot_system_health,
            ),
            ToolDefinition(
                name="adminbot_service_status",
                description="Get validated service status from AdminBot v2.",
                input_model=AdminBotServiceStatusInput,
                handler=handle_adminbot_service_status,
            ),
        ],
        frozen=True,
    )
