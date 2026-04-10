import pytest

from core.approval import ApprovalDecision, ApprovalPolicy, ApprovalStatus, ApprovalStore
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
from core.orchestration import PlanExecutionOrchestrator, resume_plan

pytestmark = pytest.mark.unit


def build_descriptor(agent_id: str, capability: str, *, source_type, execution_kind) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=source_type,
        execution_kind=execution_kind,
        capabilities=[capability],
        availability=AgentAvailability.ONLINE,
    )


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
            duration_ms=10,
        )


def test_orchestrator_pauses_and_resume_executes_remaining_step_once():
    registry = AgentRegistry(
        [
            build_descriptor(
                "analysis-agent",
                "analysis.general",
                source_type=AgentSourceType.OPENHANDS,
                execution_kind=AgentExecutionKind.HTTP_SERVICE,
            ),
            build_descriptor(
                "workflow-agent",
                "workflow.execute",
                source_type=AgentSourceType.N8N,
                execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
            ),
        ]
    )
    plan = ExecutionPlan(
        task_id="plan-approval",
        original_task={"task_type": "workflow_automation"},
        strategy=PlanStrategy.SEQUENTIAL,
        steps=[
            PlanStep(
                step_id="analyze",
                title="Analyze",
                description="Inspect the workflow request.",
                required_capabilities=["analysis.general"],
                metadata={"task_type": "analysis_general", "domain": "analysis"},
            ),
            PlanStep(
                step_id="deploy",
                title="Deploy",
                description="Trigger the external workflow.",
                required_capabilities=["workflow.execute"],
                inputs_from_steps=["analyze"],
                metadata={
                    "task_type": "workflow_automation",
                    "domain": "workflow",
                    "external_side_effect": True,
                },
            ),
        ],
    )
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)
    engine = RecordingExecutionEngine()
    store = ApprovalStore()
    orchestrator = PlanExecutionOrchestrator()

    paused = orchestrator.execute_plan(
        plan,
        registry,
        routing_engine,
        engine,
        feedback_loop,
        approval_store=store,
        approval_policy=ApprovalPolicy(),
    )

    assert paused.status == "paused"
    assert len(paused.step_results) == 1
    assert engine.calls == ["analysis_general"]
    pending = store.list_pending()
    assert len(pending) == 1

    approved_request = store.record_decision(
        pending[0].approval_id,
        ApprovalDecision(
            approval_id=pending[0].approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by="reviewer",
        ),
    )
    resumed = resume_plan(
        approved_request,
        registry=registry,
        routing_engine=routing_engine,
        execution_engine=engine,
        feedback_loop=feedback_loop,
        approval_store=store,
        approval_policy=ApprovalPolicy(),
        orchestrator=orchestrator,
    )

    assert resumed.status == "completed"
    assert len(resumed.step_results) == 2
    assert engine.calls == ["analysis_general", "workflow_automation"]
