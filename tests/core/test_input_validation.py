import pytest
from pydantic import ValidationError

from core.models import (
    CoreExecutionError,
    DispatchTaskToolInput,
    InternalTaskType,
    RequesterIdentity,
    RequesterType,
    ToolExecutionRequest,
)

pytestmark = pytest.mark.unit


def test_dispatch_task_input_requires_non_empty_task():
    with pytest.raises(ValidationError):
        DispatchTaskToolInput(task="", task_type=InternalTaskType.CHAT.value)


def test_tool_execution_request_requires_identity():
    request = ToolExecutionRequest.from_raw(
        tool_name="dispatch_task",
        payload={"task": "Analyse logs", "task_type": InternalTaskType.DEV.value},
        requested_by=RequesterIdentity(type=RequesterType.HUMAN, id="alice"),
        run_id="run-1",
        correlation_id="corr-1",
    )

    assert request.requested_by.type is RequesterType.HUMAN
    assert request.requested_by.id == "alice"
    assert request.run_id == "run-1"
    assert request.correlation_id == "corr-1"


def test_dispatch_task_input_rejects_generic_task_type():
    with pytest.raises(ValidationError):
        DispatchTaskToolInput(task="Analyse logs", task_type="generic")


def test_tool_execution_request_rejects_missing_identity_id_with_structured_error():
    with pytest.raises(CoreExecutionError) as exc_info:
        ToolExecutionRequest.from_raw(
            tool_name="dispatch_task",
            payload={"task": "Analyse logs", "task_type": InternalTaskType.DEV.value},
            requested_by={"type": "human", "id": ""},
            run_id="run-2",
            correlation_id="corr-2",
        )

    assert exc_info.value.error.error_code.value == "validation_error"
    assert exc_info.value.error.message == "Invalid tool execution request"
    assert exc_info.value.error.details["errors"]
