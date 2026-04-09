import pytest

from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentRegistry,
    AgentSourceType,
    RoutingDecision,
)
from core.execution import ExecutionEngine

pytestmark = pytest.mark.unit


def build_descriptor() -> AgentDescriptor:
    return AgentDescriptor(
        agent_id="adminbot-agent",
        display_name="AdminBot",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
        capabilities=["system.read", "system.status"],
        availability=AgentAvailability.ONLINE,
    )


def test_execution_engine_selects_adapter_from_routing_decision(monkeypatch):
    monkeypatch.setattr(
        "services.core.execute_tool",
        lambda tool_name, payload=None, **kwargs: {"status": "ok", "tool_name": tool_name},
    )
    registry = AgentRegistry([build_descriptor()])
    decision = RoutingDecision(
        task_type="system_status",
        required_capabilities=["system.read", "system.status"],
        selected_agent_id="adminbot-agent",
        selected_score=0.9,
    )

    result = ExecutionEngine().execute({"task_type": "system_status"}, decision, registry)

    assert result.success is True
    assert result.output["tool_name"] == "adminbot_system_status"
    assert result.metadata["selected_agent_id"] == "adminbot-agent"


def test_execution_engine_returns_error_when_no_agent_selected():
    decision = RoutingDecision(
        task_type="system_status",
        required_capabilities=["system.read"],
    )

    result = ExecutionEngine().execute({"task_type": "system_status"}, decision, [])

    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "missing_selected_agent"
