import pytest

from core.decision import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentRegistry,
    AgentSourceType,
    FeedbackLoop,
    OnlineUpdater,
    PerformanceHistoryStore,
    RoutingEngine,
)
from core.decision.plan_builder import PlanBuilder
from core.execution.adapters.base import ExecutionResult
from core.execution.execution_engine import ExecutionEngine
from core.orchestration import PlanExecutionOrchestrator
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


def build_descriptor(agent_id: str, capability: str) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=[capability],
        availability=AgentAvailability.ONLINE,
    )


class FakeExecutionEngine(ExecutionEngine):
    def execute(self, task, decision, descriptors):
        return ExecutionResult(
            agent_id=decision.selected_agent_id or "",
            success=True,
            output={"task_type": decision.task_type},
            metadata={"adapter": "fake"},
            duration_ms=40,
            cost=0.001,
        )


def test_multi_step_feedback_updates_learning_for_each_step():
    registry = AgentRegistry(
        [
            build_descriptor("analyze-agent", "analysis.code"),
            build_descriptor("implement-agent", "code.refactor"),
            build_descriptor("test-agent", "tests.run"),
            build_descriptor("review-agent", "review.code"),
        ]
    )
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(
        performance_history=routing_engine.performance_history,
        online_updater=OnlineUpdater(train_every=100),
    )
    plan = PlanBuilder().build(
        TaskContext(
            task_type="code_refactor",
            description="Refactor the router",
            preferences={"execution_hints": {"task_scale": "large"}},
        )
    )

    result = PlanExecutionOrchestrator().execute_plan(
        plan,
        registry,
        routing_engine,
        FakeExecutionEngine(),
        feedback_loop,
    )

    assert result.success is True
    assert len(result.step_results) == 4
    assert feedback_loop.online_updater is not None
    assert feedback_loop.online_updater.dataset.size() == 4
