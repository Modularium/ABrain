import importlib

import pytest

from core.approval import ApprovalPolicy, ApprovalStore
from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentRegistry,
    AgentSourceType,
    FeedbackLoop,
    PerformanceHistoryStore,
    RoutingEngine,
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


def build_workflow_registry() -> AgentRegistry:
    return AgentRegistry(
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


def build_sensitive_plan() -> ExecutionPlan:
    return ExecutionPlan(
        task_id="plan-hitl",
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


def test_run_task_plan_can_pause_and_approve_resume():
    core = importlib.import_module("services.core")
    registry = build_workflow_registry()
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)
    approval_store = ApprovalStore()
    approval_policy = ApprovalPolicy()
    engine = RecordingExecutionEngine()

    initial = core.run_task_plan(
        {"task_type": "workflow_automation"},
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        plan_builder=StaticPlanBuilder(build_sensitive_plan()),
        approval_store=approval_store,
        approval_policy=approval_policy,
    )

    assert initial["result"]["status"] == "paused"
    assert engine.calls == []

    pending = core.list_pending_approvals(approval_store=approval_store)["approvals"]
    assert len(pending) == 1

    approved = core.approve_plan_step(
        pending[0]["approval_id"],
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        approval_store=approval_store,
        approval_policy=approval_policy,
    )

    assert approved["result"]["status"] == "completed"
    assert engine.calls == ["workflow_automation"]
    assert feedback_loop.performance_history.get("workflow-agent").execution_count == 1


def test_reject_plan_step_finishes_without_learning_as_failure():
    core = importlib.import_module("services.core")
    registry = build_workflow_registry()
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)
    approval_store = ApprovalStore()
    approval_policy = ApprovalPolicy()
    engine = RecordingExecutionEngine()

    initial = core.run_task_plan(
        {"task_type": "workflow_automation"},
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        plan_builder=StaticPlanBuilder(build_sensitive_plan()),
        approval_store=approval_store,
        approval_policy=approval_policy,
    )

    approval_id = initial["result"]["state"]["pending_approval_id"]
    rejected = core.reject_plan_step(
        approval_id,
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        approval_store=approval_store,
        approval_policy=approval_policy,
    )

    assert rejected["result"]["status"] == "rejected"
    assert rejected["result"]["step_results"][0]["metadata"]["approval_status"] == "rejected"
    assert engine.calls == []
    assert feedback_loop.performance_history.get("workflow-agent").execution_count == 0
