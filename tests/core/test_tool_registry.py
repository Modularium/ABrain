import pytest

from core.models.tooling import DispatchTaskToolInput, InternalTaskType, ListAgentsToolInput
from core.tools.registry import ToolDefinition, ToolRegistry

pytestmark = pytest.mark.unit


def test_tool_registry_lists_fixed_tools():
    registry = ToolRegistry(
        definitions=[
            ToolDefinition(
                name="dispatch_task",
                description="Dispatch a task",
                input_model=DispatchTaskToolInput,
                handler=lambda _request, payload: payload,
            ),
            ToolDefinition(
                name="list_agents",
                description="List agents",
                input_model=ListAgentsToolInput,
                handler=lambda _request, payload: payload,
            ),
        ]
    )

    assert registry.list_tools() == ["dispatch_task", "list_agents"]


def test_tool_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    definition = ToolDefinition(
        name="dispatch_task",
        description="Dispatch a task",
        input_model=DispatchTaskToolInput,
        handler=lambda _request, payload: payload,
    )

    registry.register(definition)

    try:
        registry.register(definition)
    except ValueError as exc:
        assert "Tool already registered" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Duplicate tool registration should fail")


def test_registry_validates_fixed_task_types():
    registry = ToolRegistry(
        definitions=[
            ToolDefinition(
                name="dispatch_task",
                description="Dispatch a task",
                input_model=DispatchTaskToolInput,
                handler=lambda _request, payload: payload,
            )
        ]
    )

    validated = registry.validate_input(
        "dispatch_task",
        {"task": "Analyse logs", "task_type": InternalTaskType.SEARCH.value},
    )

    assert validated.task_type is InternalTaskType.SEARCH


def test_frozen_registry_rejects_new_registration():
    registry = ToolRegistry(definitions=[], frozen=True)

    with pytest.raises(ValueError) as exc_info:
        registry.register(
            ToolDefinition(
                name="dispatch_task",
                description="Dispatch a task",
                input_model=DispatchTaskToolInput,
                handler=lambda _request, payload: payload,
            )
        )

    assert "frozen" in str(exc_info.value)
