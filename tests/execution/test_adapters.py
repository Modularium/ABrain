import subprocess

import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.execution.adapters import (
    AdminBotExecutionAdapter,
    ClaudeCodeExecutionAdapter,
    CodexExecutionAdapter,
    OpenHandsExecutionAdapter,
)

pytestmark = pytest.mark.unit


def test_adminbot_adapter_uses_hardened_core(monkeypatch):
    called = {}

    def fake_execute_tool(tool_name, payload=None, **kwargs):
        called["tool_name"] = tool_name
        called["payload"] = payload or {}
        return {"status": "ok"}

    monkeypatch.setattr("services.core.execute_tool", fake_execute_tool)
    adapter = AdminBotExecutionAdapter()
    descriptor = AgentDescriptor(
        agent_id="adminbot-agent",
        display_name="AdminBot",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
        capabilities=["system.read", "system.status"],
    )

    result = adapter.execute({"task_type": "system_status"}, descriptor)

    assert result.success is True
    assert called["tool_name"] == "adminbot_system_status"
    assert called["payload"] == {}


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


def test_openhands_adapter_posts_task_to_app_conversations(monkeypatch):
    dummy = DummyOpenHandsClient({"id": "conv-123", "status": "created"})
    monkeypatch.setattr("httpx.Client", lambda timeout: dummy)
    adapter = OpenHandsExecutionAdapter(timeout_seconds=1.0)
    descriptor = AgentDescriptor(
        agent_id="openhands-agent",
        display_name="OpenHands",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["analysis.code", "code.refactor"],
        metadata={"endpoint_url": "http://openhands.local"},
    )

    result = adapter.execute({"task_type": "code_refactor", "description": "Refactor this module"}, descriptor)

    assert result.success is True
    assert result.output == "conv-123"
    assert dummy.calls[0][0] == "http://openhands.local/api/v1/app-conversations"
    assert dummy.calls[0][1]["initial_message"]["content"][0]["text"] == "Refactor this module"


def test_claude_code_adapter_parses_headless_json(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=["claude"],
        returncode=0,
        stdout='{"result": {"message": "done"}}',
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: completed)
    adapter = ClaudeCodeExecutionAdapter(timeout_seconds=1.0)
    descriptor = AgentDescriptor(
        agent_id="claude-agent",
        display_name="Claude Code",
        source_type=AgentSourceType.CLAUDE_CODE,
        execution_kind=AgentExecutionKind.CLOUD_AGENT,
        capabilities=["analysis.code"],
    )

    result = adapter.execute({"task_type": "code_review", "description": "Review this patch"}, descriptor)

    assert result.success is True
    assert result.output == {"message": "done"}


def test_codex_adapter_returns_structured_error_on_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["codex"], timeout=1)

    monkeypatch.setattr("subprocess.run", raise_timeout)
    adapter = CodexExecutionAdapter(timeout_seconds=1.0)
    descriptor = AgentDescriptor(
        agent_id="codex-agent",
        display_name="Codex",
        source_type=AgentSourceType.CODEX,
        execution_kind=AgentExecutionKind.CLOUD_AGENT,
        capabilities=["analysis.code"],
    )

    result = adapter.execute({"task_type": "code_review", "description": "Review this patch"}, descriptor)

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "adapter_timeout"
