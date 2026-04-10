import importlib

import pytest

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
from core.governance import PolicyEngine, PolicyRegistry, PolicyRule

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


def test_run_task_denies_execution_when_governance_blocks(monkeypatch):
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
    policy_engine = PolicyEngine(
        policy_registry=PolicyRegistry(
            rules=[
                PolicyRule(
                    id="deny-system-status",
                    description="Deny direct system status execution.",
                    capability="system.status",
                    source_type="adminbot",
                    effect="deny",
                    priority=10,
                )
            ]
        )
    )
    called = {"executed": False}

    def fail_if_called(*args, **kwargs):
        called["executed"] = True
        return {"status": "should_not_happen"}

    monkeypatch.setattr("services.core.execute_tool", fail_if_called)

    result = core.run_task(
        {"task_type": "system_status"},
        registry=registry,
        policy_engine=policy_engine,
    )

    assert result["status"] == "denied"
    assert result["governance"]["effect"] == "deny"
    assert result["execution"]["error"]["error_code"] == "policy_denied"
    assert called["executed"] is False


def test_run_task_can_pause_for_governance_approval_and_resume():
    core = importlib.import_module("services.core")
    registry = AgentRegistry(
        [
            AgentDescriptor(
                agent_id="claude-reviewer",
                display_name="Claude Reviewer",
                source_type=AgentSourceType.CLAUDE_CODE,
                execution_kind=AgentExecutionKind.LOCAL_PROCESS,
                capabilities=["analysis.code", "review.code"],
                availability=AgentAvailability.ONLINE,
            )
        ]
    )
    policy_engine = PolicyEngine(
        policy_registry=PolicyRegistry(
            rules=[
                PolicyRule(
                    id="review-claude-review",
                    description="Require approval for Claude review steps.",
                    capability="review.code",
                    source_type="claude_code",
                    effect="require_approval",
                    priority=10,
                )
            ]
        )
    )
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)
    engine = RecordingExecutionEngine()

    initial = core.run_task(
        {"task_type": "code_review", "description": "Review the patch"},
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        policy_engine=policy_engine,
    )

    assert initial["status"] == "paused"
    assert initial["governance"]["effect"] == "require_approval"
    assert engine.calls == []

    resumed = core.approve_plan_step(
        initial["approval"]["approval_id"],
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        policy_engine=policy_engine,
    )

    assert resumed["result"]["status"] == "completed"
    assert engine.calls == ["code_review"]


def test_run_task_plan_pauses_for_governance_and_resumes_cleanly():
    core = importlib.import_module("services.core")
    registry = AgentRegistry(
        [
            AgentDescriptor(
                agent_id="claude-reviewer",
                display_name="Claude Reviewer",
                source_type=AgentSourceType.CLAUDE_CODE,
                execution_kind=AgentExecutionKind.LOCAL_PROCESS,
                capabilities=["review.code"],
                availability=AgentAvailability.ONLINE,
            )
        ]
    )
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)
    engine = RecordingExecutionEngine()
    policy_engine = PolicyEngine(
        policy_registry=PolicyRegistry(
            rules=[
                PolicyRule(
                    id="review-claude-review",
                    description="Require approval for Claude review steps.",
                    capability="review.code",
                    source_type="claude_code",
                    effect="require_approval",
                    priority=10,
                )
            ]
        )
    )
    plan = ExecutionPlan(
        task_id="plan-policy-review",
        original_task={"task_type": "code_review"},
        strategy=PlanStrategy.SINGLE,
        steps=[
            PlanStep(
                step_id="review",
                title="Review",
                description="Review the patch.",
                required_capabilities=["review.code"],
                metadata={"task_type": "code_review", "domain": "code"},
            )
        ],
    )

    initial = core.run_task_plan(
        {"task_type": "code_review"},
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        plan_builder=StaticPlanBuilder(plan),
        policy_engine=policy_engine,
    )

    assert initial["result"]["status"] == "paused"
    assert initial["result"]["state"]["metadata"]["approval_request"]["metadata"]["approval_origin"] == "governance"
    assert engine.calls == []

    resumed = core.approve_plan_step(
        initial["result"]["state"]["pending_approval_id"],
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        policy_engine=policy_engine,
    )

    assert resumed["result"]["status"] == "completed"
    assert engine.calls == ["code_review"]
