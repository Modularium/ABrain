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
from core.execution.execution_engine import ExecutionEngine
from core.orchestration import PlanExecutionOrchestrator

pytestmark = pytest.mark.unit


def build_descriptor(agent_id: str, capability: str) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=[capability],
        availability=AgentAvailability.ONLINE,
        metadata={"success_rate": 0.9},
    )


class RecordingRoutingEngine(RoutingEngine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.step_calls: list[str] = []

    def route_step(self, step, task, descriptors):
        self.step_calls.append(step.step_id)
        return super().route_step(step, task, descriptors)


class FakeExecutionEngine(ExecutionEngine):
    def __init__(self):
        self.calls: list[str] = []

    def execute(self, task, decision, descriptors):
        self.calls.append(decision.task_type)
        return ExecutionResult(
            agent_id=decision.selected_agent_id or "",
            success=True,
            output={"task_type": decision.task_type, "description": task.get("description")},
            metadata={"adapter": "fake"},
            duration_ms=50,
        )


def test_orchestrator_executes_steps_in_order_and_routes_each_step():
    registry = AgentRegistry(
        [
            build_descriptor("analyze-agent", "analysis.code"),
            build_descriptor("implement-agent", "code.refactor"),
        ]
    )
    plan = ExecutionPlan(
        task_id="plan-1",
        original_task={"task_type": "code_refactor"},
        strategy=PlanStrategy.SEQUENTIAL,
        steps=[
            PlanStep(
                step_id="analyze",
                title="Analyze",
                description="Analyze the task",
                required_capabilities=["analysis.code"],
                metadata={"task_type": "code_analyze", "domain": "code"},
            ),
            PlanStep(
                step_id="implement",
                title="Implement",
                description="Implement the change",
                required_capabilities=["code.refactor"],
                inputs_from_steps=["analyze"],
                metadata={"task_type": "code_refactor", "domain": "code"},
            ),
        ],
    )
    routing_engine = RecordingRoutingEngine(performance_history=PerformanceHistoryStore())
    execution_engine = FakeExecutionEngine()
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        plan,
        registry,
        routing_engine,
        execution_engine,
        feedback_loop,
    )

    assert routing_engine.step_calls == ["analyze", "implement"]
    assert execution_engine.calls == ["code_analyze", "code_refactor"]
    assert result.success is True
    assert result.step_results[1].metadata["routing_decision"]["selected_agent_id"] == "implement-agent"


def test_step_level_routing_keeps_candidate_filter_as_hard_boundary():
    registry = [
        build_descriptor("allowed-agent", "analysis.code"),
        AgentDescriptor(
            agent_id="rejected-agent",
            display_name="rejected-agent",
            source_type=AgentSourceType.OPENHANDS,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=["code.refactor"],
            availability=AgentAvailability.ONLINE,
        ),
    ]
    routing_engine = RecordingRoutingEngine(performance_history=PerformanceHistoryStore())
    step = PlanStep(
        step_id="analyze",
        title="Analyze",
        description="Analyze the task",
        required_capabilities=["analysis.code"],
        metadata={"task_type": "code_analyze", "domain": "code"},
    )

    decision = routing_engine.route_step(step, {"task_type": "code_analyze"}, registry)

    assert decision.selected_agent_id == "allowed-agent"
    assert decision.diagnostics["neural_policy_source"] in {"deterministic_init", "loaded_weights", "trained_runtime"}
    rejected_ids = [item["agent_id"] for item in decision.diagnostics["rejected_agents"]]
    assert rejected_ids == ["rejected-agent"]


def test_orchestrator_can_create_agent_for_uncovered_step():
    registry = AgentRegistry()
    plan = ExecutionPlan(
        task_id="plan-2",
        original_task={"task_type": "code_refactor"},
        strategy=PlanStrategy.SINGLE,
        steps=[
            PlanStep(
                step_id="implement",
                title="Implement",
                description="Implement the requested change",
                required_capabilities=["code.refactor"],
                metadata={"task_type": "code_refactor", "domain": "code"},
            )
        ],
    )
    routing_engine = RecordingRoutingEngine(performance_history=PerformanceHistoryStore())
    execution_engine = FakeExecutionEngine()
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        plan,
        registry,
        routing_engine,
        execution_engine,
        feedback_loop,
    )

    assert result.success is True
    assert result.step_results[0].metadata["created_agent"] is not None
    assert registry.list_descriptors()[0].source_type == AgentSourceType.OPENHANDS
