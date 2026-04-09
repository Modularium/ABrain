import httpx
import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.execution.adapters import OpenHandsExecutionAdapter

pytestmark = pytest.mark.unit


class DummyOpenHandsResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyOpenHandsClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        return DummyOpenHandsResponse(self.payload)


def build_descriptor(**metadata):
    return AgentDescriptor(
        agent_id="openhands-agent",
        display_name="OpenHands",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=["code.generate", "code.refactor", "repo.modify", "tests.run"],
        metadata=metadata,
    )


def test_openhands_adapter_maps_api_response_to_execution_result(monkeypatch):
    dummy = DummyOpenHandsClient(
        {
            "id": "conv-123",
            "assistant_response": {"summary": "Patch prepared"},
            "usage": {"cost_usd": 0.02},
        }
    )
    monkeypatch.setattr("httpx.Client", lambda timeout: dummy)
    adapter = OpenHandsExecutionAdapter(timeout_seconds=1.0)

    result = adapter.execute(
        {"task_type": "code_refactor", "description": "Refactor the worker", "preferences": {}},
        build_descriptor(endpoint_url="http://openhands.local", selected_repository="repo-a", branch="main"),
    )

    assert result.success is True
    assert result.output == {"summary": "Patch prepared"}
    assert result.cost == 0.02
    assert result.metadata["endpoint"] == "http://openhands.local"
    assert dummy.calls[0][0] == "http://openhands.local/api/v1/app-conversations"
    assert dummy.calls[0][1]["selected_repository"] == "repo-a"
    assert dummy.calls[0][1]["branch"] == "main"


def test_openhands_adapter_handles_timeout(monkeypatch):
    class TimeoutClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("httpx.Client", lambda timeout: TimeoutClient())
    adapter = OpenHandsExecutionAdapter(timeout_seconds=0.01)

    result = adapter.execute(
        {"task_type": "code_generate", "description": "Generate tests"},
        build_descriptor(endpoint_url="http://openhands.local"),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "adapter_timeout"
