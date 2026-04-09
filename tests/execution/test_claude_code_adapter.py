import subprocess

import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.execution.adapters import ClaudeCodeExecutionAdapter

pytestmark = pytest.mark.unit


def build_descriptor(**metadata):
    return AgentDescriptor(
        agent_id="claude-agent",
        display_name="Claude Code",
        source_type=AgentSourceType.CLAUDE_CODE,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["code.analyze", "repo.modify", "tests.run", "docs.write"],
        metadata=metadata,
    )


def test_claude_code_adapter_parses_headless_json_and_respects_config(monkeypatch):
    captured = {}
    completed = subprocess.CompletedProcess(
        args=["claude"],
        returncode=0,
        stdout='{"result": {"message": "done"}, "usage": {"cost_usd": 0.04}}',
        stderr="",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        return completed

    monkeypatch.setattr("subprocess.run", fake_run)
    adapter = ClaudeCodeExecutionAdapter(timeout_seconds=1.0)

    result = adapter.execute(
        {"task_type": "code_review", "description": "Review this patch"},
        build_descriptor(
            command="claude",
            cwd="/workspace/repo",
            allowed_tools=["Read", "Edit"],
            permission_mode="acceptEdits",
        ),
    )

    assert result.success is True
    assert result.output == {"message": "done"}
    assert result.cost == 0.04
    assert captured["cwd"] == "/workspace/repo"
    assert captured["command"][:4] == ["claude", "-p", "Review this patch", "--output"]
    assert "--allowedTools" in captured["command"]
    assert "--permission-mode" in captured["command"]


def test_claude_code_adapter_handles_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["claude"], timeout=1)

    monkeypatch.setattr("subprocess.run", raise_timeout)
    adapter = ClaudeCodeExecutionAdapter(timeout_seconds=0.01)

    result = adapter.execute(
        {"task_type": "code_review", "description": "Review this patch"},
        build_descriptor(),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "adapter_timeout"
