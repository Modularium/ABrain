import importlib

import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentRegistry, AgentSourceType

pytestmark = pytest.mark.unit


def test_run_task_plan_builds_executes_and_aggregates_steps(monkeypatch):
    core = importlib.import_module("services.core")
    registry = AgentRegistry(
        [
            AgentDescriptor(
                agent_id="analyze-agent",
                display_name="Analyze",
                source_type=AgentSourceType.OPENHANDS,
                execution_kind=AgentExecutionKind.HTTP_SERVICE,
                capabilities=["analysis.code"],
            ),
            AgentDescriptor(
                agent_id="implement-agent",
                display_name="Implement",
                source_type=AgentSourceType.OPENHANDS,
                execution_kind=AgentExecutionKind.HTTP_SERVICE,
                capabilities=["code.refactor"],
            ),
            AgentDescriptor(
                agent_id="test-agent",
                display_name="Test",
                source_type=AgentSourceType.OPENHANDS,
                execution_kind=AgentExecutionKind.HTTP_SERVICE,
                capabilities=["tests.run"],
            ),
            AgentDescriptor(
                agent_id="review-agent",
                display_name="Review",
                source_type=AgentSourceType.CLAUDE_CODE,
                execution_kind=AgentExecutionKind.LOCAL_PROCESS,
                capabilities=["review.code"],
            ),
        ]
    )

    class FakeExecutionEngine:
        def execute(self, task, decision, descriptors):
            from core.execution.adapters.base import ExecutionResult

            return ExecutionResult(
                agent_id=decision.selected_agent_id or "",
                success=True,
                output={"task_type": decision.task_type},
                metadata={"adapter": "fake"},
                duration_ms=20,
            )

    result = core.run_task_plan(
        {
            "task_type": "code_refactor",
            "description": "Refactor the worker",
            "preferences": {"execution_hints": {"task_scale": "large"}},
        },
        registry=registry,
        execution_engine=FakeExecutionEngine(),
    )

    assert result["plan"]["strategy"] == "sequential"
    assert len(result["result"]["step_results"]) == 4
    assert result["result"]["success"] is True
