import httpx
import pytest

from adapters.flowise.importer import import_flowise_agent
from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType, FeedbackLoop, OnlineUpdater, PerformanceHistoryStore
from core.execution.adapters import FlowiseExecutionAdapter
from core.execution.adapters.base import ExecutionResult

pytestmark = pytest.mark.unit


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        if self.error is not None:
            raise self.error
        return DummyResponse(self.payload)


def build_flowise_descriptor(**metadata):
    return AgentDescriptor(
        agent_id="flowise-agent",
        display_name="Flowise",
        source_type=AgentSourceType.FLOWISE,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["flow.visual_agent", "flow.tool_orchestration"],
        metadata=metadata,
    )


def test_flowise_adapter_maps_prediction_request(monkeypatch):
    dummy = DummyClient(
        {
            "text": "Workflow completed",
            "cost": 0.02,
            "warnings": ["partial-tool-fallback"],
        }
    )
    monkeypatch.setattr("httpx.Client", lambda timeout: dummy)
    adapter = FlowiseExecutionAdapter(timeout_seconds=1.0)

    result = adapter.execute(
        {
            "task_type": "tool_orchestration_ui",
            "description": "Build an editable orchestration flow",
            "preferences": {"execution_hints": {"editable_in_ui": True}},
        },
        build_flowise_descriptor(
            prediction_url="http://flowise.local/api/v1/prediction/chatflow-123",
            fixed_config={"temperature": 0},
        ),
    )

    assert result.success is True
    assert result.output == "Workflow completed"
    assert result.cost == 0.02
    assert result.warnings == ["partial-tool-fallback"]
    assert result.metadata["runtime_contract"] == "prediction_v1"
    assert dummy.calls[0][0] == "http://flowise.local/api/v1/prediction/chatflow-123"
    assert dummy.calls[0][1]["question"] == "Build an editable orchestration flow"
    assert dummy.calls[0][1]["overrideConfig"]["temperature"] == 0


def test_flowise_adapter_handles_transport_errors(monkeypatch):
    monkeypatch.setattr("httpx.Client", lambda timeout: DummyClient(error=httpx.RequestError("boom")))
    adapter = FlowiseExecutionAdapter(timeout_seconds=0.01)

    result = adapter.execute(
        {"task_type": "visual_agent_editable", "description": "Edit this chatflow"},
        build_flowise_descriptor(prediction_url="http://flowise.local/api/v1/prediction/chatflow-123"),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "adapter_transport_error"


def test_flowise_execution_stays_separate_from_interop_layer():
    descriptor = import_flowise_agent(
        {
            "id": "flow-1",
            "name": "Interop Agent",
            "description": "Imported from Flowise",
            "tools": [],
            "metadata": {"capabilities": ["flow.visual_agent"]},
        }
    )

    assert descriptor.source_type == AgentSourceType.FLOWISE
    assert descriptor.execution_kind == AgentExecutionKind.WORKFLOW_ENGINE
    assert descriptor.metadata["imported_from"] == "flowise"


def test_feedback_loop_accepts_workflow_adapter_results_without_special_paths():
    feedback = FeedbackLoop(
        performance_history=PerformanceHistoryStore(),
        online_updater=OnlineUpdater(train_every=100),
    )

    update = feedback.update_performance(
        "flowise-agent",
        ExecutionResult(
            agent_id="flowise-agent",
            success=True,
            duration_ms=900,
            cost=0.01,
            output={"status": "ok"},
            metadata={"adapter": "flowise"},
        ),
        task={"task_type": "tool_orchestration_ui", "description": "Edit the workflow"},
        agent_descriptor=build_flowise_descriptor(prediction_url="http://flowise.local/api/v1/prediction/chatflow-123"),
    )

    assert update.performance.execution_count == 1
    assert update.dataset_size == 1
    assert update.reward is not None
    assert update.warnings == []
