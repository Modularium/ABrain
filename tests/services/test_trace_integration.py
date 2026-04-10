import importlib

import pytest

from core.audit import TraceStore
from core.decision import AgentDescriptor, AgentExecutionKind, AgentRegistry, AgentSourceType

pytestmark = pytest.mark.unit


def test_run_task_creates_trace_and_internal_trace_views(monkeypatch, tmp_path):
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
    trace_id = result["trace"]["trace_id"]
    trace_snapshot = core.get_trace(trace_id, trace_store=store)["trace"]
    recent = core.list_recent_traces(limit=3, trace_store=store)["traces"]

    assert result["execution"]["success"] is True
    assert trace_id is not None
    assert [span["name"] for span in trace_snapshot["spans"]] == [
        "routing",
        "policy_check",
        "adapter_execution",
        "feedback_update",
    ]
    assert recent[0]["trace_id"] == trace_id


def test_run_task_survives_trace_store_failures(monkeypatch):
    core = importlib.import_module("services.core")
    registry = AgentRegistry(
        [
            AgentDescriptor(
                agent_id="adminbot-agent",
                display_name="AdminBot",
                source_type=AgentSourceType.ADMINBOT,
                execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
                capabilities=["system.read", "system.status"],
            )
        ]
    )

    class ExplodingTraceStore:
        def create_trace(self, *args, **kwargs):
            raise RuntimeError("trace db offline")

    monkeypatch.setattr(
        "services.core.execute_tool",
        lambda tool_name, payload=None, **kwargs: {"status": "ok", "tool_name": tool_name},
    )

    result = core.run_task(
        {"task_type": "system_status"},
        registry=registry,
        trace_store=ExplodingTraceStore(),
    )

    assert result["execution"]["success"] is True
    assert result["trace"]["enabled"] is False
    assert result["trace"]["warnings"] == ["trace_create_failed:RuntimeError"]
