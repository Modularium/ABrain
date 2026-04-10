import importlib

import pytest

from core.audit import TraceStore
from core.decision import AgentDescriptor, AgentExecutionKind, AgentRegistry, AgentSourceType

pytestmark = pytest.mark.unit


def test_run_task_stores_routing_and_policy_explainability(monkeypatch, tmp_path):
    core = importlib.import_module("services.core")
    store = TraceStore(tmp_path / "trace.sqlite3")
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

    result = core.run_task(
        {"task_type": "system_status"},
        registry=registry,
        trace_store=store,
    )
    explainability = core.get_explainability(result["trace"]["trace_id"], trace_store=store)["explainability"]

    assert len(explainability) == 1
    assert explainability[0]["step_id"] == "execute"
    assert explainability[0]["selected_agent_id"] == "adminbot-agent"
    assert explainability[0]["approval_required"] is False
    assert explainability[0]["metadata"]["routing_decision"]["required_capabilities"] == [
        "system.read",
        "system.status",
    ]
