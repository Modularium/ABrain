import subprocess

import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.execution.adapters import ClaudeCodeExecutionAdapter, CodexExecutionAdapter, ExecutionAdapterRegistry, OpenHandsExecutionAdapter

pytestmark = pytest.mark.unit


def build_codex_descriptor(**metadata):
    return AgentDescriptor(
        agent_id="codex-agent",
        display_name="Codex",
        source_type=AgentSourceType.CODEX,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["code.generate", "code.refactor", "code.analyze", "repo.modify", "tests.run"],
        metadata=metadata,
    )


def test_codex_adapter_uses_honest_cli_v1_path(monkeypatch):
    captured = {}
    completed = subprocess.CompletedProcess(
        args=["codex"],
        returncode=0,
        stdout='{"result": {"summary": "changes ready"}, "usage": {"total_cost": 0.12}}',
        stderr="",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        return completed

    monkeypatch.setattr("subprocess.run", fake_run)
    adapter = CodexExecutionAdapter(timeout_seconds=1.0)

    result = adapter.execute(
        {"task_type": "code_refactor", "description": "Refactor the routing module"},
        build_codex_descriptor(
            command="codex",
            cwd="/workspace/repo",
            model="gpt-5-codex",
            sandbox_mode="workspace-write",
            approval_mode="on-failure",
        ),
    )

    assert result.success is True
    assert result.output == {"summary": "changes ready"}
    assert result.cost == 0.12
    assert result.metadata["command_mode"] == "cli_v1"
    assert result.metadata["preferred_future_transport"] == "app_server_json_rpc"
    assert captured["cwd"] == "/workspace/repo"
    assert captured["command"][:4] == ["codex", "exec", "--json", "Refactor the routing module"]
    assert "--model" in captured["command"]
    assert "--sandbox" in captured["command"]
    assert "--approval-mode" in captured["command"]


def test_codex_adapter_rejects_invalid_json(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=["codex"],
        returncode=0,
        stdout="not-json",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: completed)
    adapter = CodexExecutionAdapter(timeout_seconds=1.0)

    result = adapter.execute(
        {"task_type": "code_review", "description": "Review this patch"},
        build_codex_descriptor(),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "adapter_protocol_error"


def test_execution_adapter_registry_maps_native_dev_agents():
    registry = ExecutionAdapterRegistry()

    openhands = registry.resolve(
        AgentDescriptor(
            agent_id="openhands-agent",
            display_name="OpenHands",
            source_type=AgentSourceType.OPENHANDS,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=["code.refactor"],
        )
    )
    claude = registry.resolve(
        AgentDescriptor(
            agent_id="claude-agent",
            display_name="Claude Code",
            source_type=AgentSourceType.CLAUDE_CODE,
            execution_kind=AgentExecutionKind.LOCAL_PROCESS,
            capabilities=["code.analyze"],
        )
    )
    codex = registry.resolve(build_codex_descriptor())

    assert isinstance(openhands, OpenHandsExecutionAdapter)
    assert isinstance(claude, ClaudeCodeExecutionAdapter)
    assert isinstance(codex, CodexExecutionAdapter)
