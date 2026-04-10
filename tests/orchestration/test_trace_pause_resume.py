import importlib

import pytest

from core.audit import TraceStore
from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentRegistry,
    AgentSourceType,
)
from core.decision.plan_models import ExecutionPlan, PlanStep, PlanStrategy
from core.execution.adapters.base import ExecutionResult

pytestmark = pytest.mark.unit


class StaticPlanBuilder:
    def __init__(self, plan: ExecutionPlan) -> None:
        self._plan = plan

    def build(self, task, *, planner_result=None):
        del task
        del planner_result
        return self._plan


class RecordingExecutionEngine:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, task, decision, descriptors):
        self.calls.append(decision.task_type)
        return ExecutionResult(
            agent_id=decision.selected_agent_id or "",
            success=True,
            output={"task_type": decision.task_type},
            metadata={"adapter": "fake"},
            duration_ms=15,
        )


def test_trace_records_approval_pause_and_resume_events(tmp_path):
    core = importlib.import_module("services.core")
    store = TraceStore(tmp_path / "trace.sqlite3")
    registry = AgentRegistry(
        [
            AgentDescriptor(
                agent_id="workflow-agent",
                display_name="Workflow Agent",
                source_type=AgentSourceType.N8N,
                execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
                capabilities=["workflow.execute"],
                availability=AgentAvailability.ONLINE,
            )
        ]
    )
    plan = ExecutionPlan(
        task_id="plan-trace-approval",
        original_task={"task_type": "workflow_automation"},
        strategy=PlanStrategy.SINGLE,
        steps=[
            PlanStep(
                step_id="deploy",
                title="Deploy",
                description="Trigger the external workflow.",
                required_capabilities=["workflow.execute"],
                metadata={
                    "task_type": "workflow_automation",
                    "domain": "workflow",
                    "external_side_effect": True,
                },
            )
        ],
    )
    engine = RecordingExecutionEngine()

    paused = core.run_task_plan(
        {"task_type": "workflow_automation"},
        registry=registry,
        execution_engine=engine,
        plan_builder=StaticPlanBuilder(plan),
        trace_store=store,
    )

    assert paused["result"]["status"] == "paused"
    assert engine.calls == []

    resumed = core.approve_plan_step(
        paused["result"]["state"]["pending_approval_id"],
        registry=registry,
        execution_engine=engine,
        trace_store=store,
    )
    trace_id = paused["trace"]["trace_id"]
    snapshot = core.get_trace(trace_id, trace_store=store)["trace"]
    events = [
        event["event_type"]
        for span in snapshot["spans"]
        for event in span["events"]
    ]

    assert resumed["result"]["status"] == "completed"
    assert engine.calls == ["workflow_automation"]
    assert "approval_requested" in events
    assert "approval_pending" in events
    assert "approval_approved" in events
    assert "plan_resumed" in events
