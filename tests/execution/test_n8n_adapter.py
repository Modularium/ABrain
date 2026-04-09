import httpx
import pytest

from core.decision import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    FeedbackLoop,
    OnlineUpdater,
    PerformanceHistoryStore,
)
from core.execution.adapters import ExecutionAdapterRegistry, FlowiseExecutionAdapter, N8NExecutionAdapter
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


def build_n8n_descriptor(**metadata):
    return AgentDescriptor(
        agent_id="n8n-agent",
        display_name="n8n",
        source_type=AgentSourceType.N8N,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["workflow.execute", "workflow.automation", "data.transform"],
        metadata=metadata,
    )


def test_n8n_adapter_maps_controlled_webhook_request(monkeypatch):
    dummy = DummyClient(
        {
            "success": True,
            "result": {"status": "queued"},
            "metrics": {"cost_usd": 0.01},
        }
    )
    monkeypatch.setattr("httpx.Client", lambda timeout: dummy)
    adapter = N8NExecutionAdapter(timeout_seconds=1.0)

    result = adapter.execute(
        {
            "task_type": "workflow_automation",
            "description": "Create a release workflow",
            "preferences": {"execution_hints": {"integration_heavy": True}},
        },
        build_n8n_descriptor(
            webhook_url="http://n8n.local/webhook/abrain-release",
            workflow_id="release-flow",
            headers={"X-ABrain": "1"},
        ),
    )

    assert result.success is True
    assert result.output == {"status": "queued"}
    assert result.cost == 0.01
    assert result.metadata["workflow_contract"] == "webhook_v1"
    assert dummy.calls[0][0] == "http://n8n.local/webhook/abrain-release"
    assert dummy.calls[0][1]["task"]["task_type"] == "workflow_automation"
    assert dummy.calls[0][1]["agent"]["source_type"] == "n8n"
    assert dummy.calls[0][2]["X-ABrain"] == "1"


def test_n8n_adapter_handles_timeout(monkeypatch):
    monkeypatch.setattr("httpx.Client", lambda timeout: DummyClient(error=httpx.TimeoutException("timeout")))
    adapter = N8NExecutionAdapter(timeout_seconds=0.01)

    result = adapter.execute(
        {"task_type": "backend_automation", "description": "Run this pipeline"},
        build_n8n_descriptor(webhook_url="http://n8n.local/webhook/abrain"),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "adapter_timeout"


def test_execution_adapter_registry_maps_workflow_adapters():
    registry = ExecutionAdapterRegistry()

    n8n = registry.resolve(build_n8n_descriptor(webhook_url="http://n8n.local/webhook/abrain"))
    flowise = registry.resolve(
        AgentDescriptor(
            agent_id="flowise-agent",
            display_name="Flowise",
            source_type=AgentSourceType.FLOWISE,
            execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
            capabilities=["flow.visual_agent"],
            metadata={"prediction_url": "http://flowise.local/api/v1/prediction/chatflow"},
        )
    )

    assert isinstance(n8n, N8NExecutionAdapter)
    assert isinstance(flowise, FlowiseExecutionAdapter)


def test_feedback_loop_accepts_n8n_results_without_special_paths():
    feedback = FeedbackLoop(
        performance_history=PerformanceHistoryStore(),
        online_updater=OnlineUpdater(train_every=100),
    )

    update = feedback.update_performance(
        "n8n-agent",
        ExecutionResult(
            agent_id="n8n-agent",
            success=True,
            duration_ms=600,
            cost=0.005,
            output={"status": "ok"},
            metadata={"adapter": "n8n"},
        ),
        task={"task_type": "workflow_automation", "description": "Automate this backend flow"},
        agent_descriptor=build_n8n_descriptor(webhook_url="http://n8n.local/webhook/abrain"),
    )

    assert update.performance.execution_count == 1
    assert update.dataset_size == 1
    assert update.reward is not None
    assert update.warnings == []
