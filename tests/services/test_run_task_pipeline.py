import importlib

import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentRegistry, AgentSourceType

pytestmark = pytest.mark.unit


def test_run_task_decides_executes_and_updates_feedback(monkeypatch):
    core = importlib.import_module("services.core")
    registry = AgentRegistry(
        [
            AgentDescriptor(
                agent_id="adminbot-agent",
                display_name="AdminBot",
                source_type=AgentSourceType.ADMINBOT,
                execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
                capabilities=["system.read", "system.status"],
                metadata={"success_rate": 0.9},
            )
        ]
    )
    monkeypatch.setattr(
        "services.core.execute_tool",
        lambda tool_name, payload=None, **kwargs: {"status": "ok", "tool_name": tool_name},
    )

    result = core.run_task({"task_type": "system_status"}, registry=registry)

    assert result["decision"]["selected_agent_id"] == "adminbot-agent"
    assert result["execution"]["success"] is True
    assert result["feedback"]["performance"]["execution_count"] == 1


def test_run_task_creates_agent_when_no_candidate_is_good_enough():
    core = importlib.import_module("services.core")
    registry = AgentRegistry()

    result = core.run_task({"task_type": "code_refactor"}, registry=registry)

    assert result["created_agent"] is not None
    assert result["created_agent"]["source_type"] == "openhands"
