import pytest

from core.execution import ExecutionDispatcher
from core.models import (
    CoreExecutionError,
    DispatchTaskToolInput,
    InternalTaskType,
    RequesterIdentity,
    RequesterType,
    ToolExecutionRequest,
)
from core.tools.registry import ToolDefinition, ToolRegistry

pytestmark = pytest.mark.unit


def _build_request(payload: dict | None = None, tool_name: str = "dispatch_task") -> ToolExecutionRequest:
    return ToolExecutionRequest.from_raw(
        tool_name=tool_name,
        payload=payload or {"task": "Stabilisiere ABrain", "task_type": InternalTaskType.CHAT.value},
        requested_by=RequesterIdentity(type=RequesterType.AGENT, id="tester"),
        run_id="run-42",
        correlation_id="corr-42",
    )


def test_execution_dispatcher_executes_sync_handler():
    registry = ToolRegistry(
        definitions=[
            ToolDefinition(
                name="dispatch_task",
                description="Dispatch a task",
                input_model=DispatchTaskToolInput,
                handler=lambda _request, payload: {"task": payload.task, "task_type": payload.task_type},
            )
        ]
    )
    dispatcher = ExecutionDispatcher(registry)

    result = dispatcher.execute_sync(_build_request())

    assert result.ok is True
    assert result.output == {"task": "Stabilisiere ABrain", "task_type": InternalTaskType.CHAT}
    assert result.requested_by.id == "tester"


def test_execution_dispatcher_rejects_unknown_tool():
    dispatcher = ExecutionDispatcher(ToolRegistry())

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(_build_request(tool_name="missing_tool"))

    assert exc_info.value.error.error_code.value == "unknown_tool"
    assert exc_info.value.error.tool_name == "missing_tool"


def test_execution_dispatcher_surfaces_validation_context():
    registry = ToolRegistry(
        definitions=[
            ToolDefinition(
                name="dispatch_task",
                description="Dispatch a task",
                input_model=DispatchTaskToolInput,
                handler=lambda _request, payload: payload.task,
            )
        ]
    )
    dispatcher = ExecutionDispatcher(registry)

    with pytest.raises(CoreExecutionError) as exc_info:
        dispatcher.execute_sync(_build_request(payload={"task": "", "task_type": InternalTaskType.CHAT.value}))

    assert exc_info.value.error.error_code.value == "validation_error"
    assert exc_info.value.error.run_id == "run-42"
    assert exc_info.value.error.correlation_id == "corr-42"
