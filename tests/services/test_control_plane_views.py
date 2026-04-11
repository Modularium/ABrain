import importlib

import pytest

from core.approval import ApprovalPolicy, ApprovalStore
from core.audit import TraceStore
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

pytestmark = pytest.mark.unit


class StaticPlanBuilder:
    def __init__(self, plan: ExecutionPlan) -> None:
        self._plan = plan

    def build(self, task, *, planner_result=None):
        del task
        del planner_result
        return self._plan


def _build_workflow_registry() -> AgentRegistry:
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


def _build_sensitive_plan() -> ExecutionPlan:
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


def test_list_recent_plans_surfaces_paused_plan_state(tmp_path):
    core = importlib.import_module("services.core")
    trace_store = TraceStore(tmp_path / "traces.sqlite3")
    approval_store = ApprovalStore()
    approval_policy = ApprovalPolicy()
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)

    result = core.run_task_plan(
        {"task_type": "workflow_automation", "description": "Trigger deployment workflow"},
        registry=_build_workflow_registry(),
        routing_engine=routing_engine,
        feedback_loop=feedback_loop,
        approval_store=approval_store,
        approval_policy=approval_policy,
        plan_builder=StaticPlanBuilder(_build_sensitive_plan()),
        trace_store=trace_store,
    )

    plans = core.list_recent_plans(
        limit=5,
        approval_store=approval_store,
        trace_store=trace_store,
    )["plans"]

    assert result["result"]["status"] == "paused"
    assert plans[0]["trace_id"] == result["trace"]["trace_id"]
    assert plans[0]["pending_approval_id"] == result["result"]["state"]["pending_approval_id"]
    assert plans[0]["state"]["status"] == "paused"


def test_list_recent_governance_decisions_derives_approval_effect(tmp_path):
    core = importlib.import_module("services.core")
    trace_store = TraceStore(tmp_path / "traces.sqlite3")
    approval_store = ApprovalStore()
    approval_policy = ApprovalPolicy()
    routing_engine = RoutingEngine(performance_history=PerformanceHistoryStore())
    feedback_loop = FeedbackLoop(performance_history=routing_engine.performance_history)

    core.run_task_plan(
        {"task_type": "workflow_automation", "description": "Trigger deployment workflow"},
        registry=_build_workflow_registry(),
        routing_engine=routing_engine,
        feedback_loop=feedback_loop,
        approval_store=approval_store,
        approval_policy=approval_policy,
        plan_builder=StaticPlanBuilder(_build_sensitive_plan()),
        trace_store=trace_store,
    )

    governance = core.list_recent_governance_decisions(limit=5, trace_store=trace_store)["governance"]

    assert governance[0]["effect"] == "require_approval"
    assert governance[0]["approval_required"] is True
    assert governance[0]["selected_agent_id"] == "workflow-agent"


def test_list_agent_catalog_projects_existing_agent_listing(monkeypatch):
    core = importlib.import_module("services.core")
    monkeypatch.setattr(
        core,
        "list_agents",
        lambda: {
            "agents": [
                {
                    "id": "agent-1",
                    "name": "Flow Agent",
                    "capabilities": ["workflow.execute"],
                    "version": "1.2.0",
                    "traits": {"availability": "online"},
                }
            ]
        },
    )

    catalog = core.list_agent_catalog()["agents"]

    assert catalog == [
        {
            "agent_id": "agent-1",
            "display_name": "Flow Agent",
            "capabilities": ["workflow.execute"],
            "source_type": None,
            "execution_kind": None,
            "availability": "online",
            "trust_level": None,
            "metadata": {
                "domain": None,
                "role": None,
                "version": "1.2.0",
                "skills": [],
                "estimated_cost_per_token": None,
                "avg_response_time": None,
                "load_factor": None,
                "projection_source": "services.core.list_agents",
                "descriptor_projection_complete": False,
            },
        }
    ]
