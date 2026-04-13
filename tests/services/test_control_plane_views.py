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
            "execution_capabilities": None,
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


def test_get_control_plane_overview_aggregates_canonical_reads(monkeypatch):
    core = importlib.import_module("services.core")
    monkeypatch.setattr(
        core,
        "list_agent_catalog",
        lambda: {"agents": [{"agent_id": "agent-1", "display_name": "Agent One"}]},
    )
    monkeypatch.setattr(
        core,
        "list_pending_approvals",
        lambda: {"approvals": [{"approval_id": "approval-1"}]},
    )
    monkeypatch.setattr(
        core,
        "list_recent_traces",
        lambda limit=3: {"traces": [{"trace_id": f"trace-{limit}"}]},
    )
    monkeypatch.setattr(
        core,
        "list_recent_plans",
        lambda limit=3: {"plans": [{"plan_id": f"plan-{limit}"}]},
    )
    monkeypatch.setattr(
        core,
        "list_recent_governance_decisions",
        lambda limit=3: {"governance": [{"trace_id": f"governance-{limit}", "effect": "allow"}]},
    )
    monkeypatch.setattr(
        core,
        "get_governance_state",
        lambda: {"engine": "PolicyEngine", "registry": "PolicyRegistry", "policy_path": None},
    )

    overview = core.get_control_plane_overview(
        agent_limit=3,
        approval_limit=3,
        trace_limit=3,
        plan_limit=3,
        governance_limit=3,
    )

    assert overview["summary"] == {
        "agent_count": 1,
        "pending_approvals": 1,
        "recent_traces": 1,
        "recent_plans": 1,
        "recent_governance_events": 1,
    }
    assert overview["system"]["layers"][-1]["name"] == "MCP v2"
    assert overview["recent_governance"][0]["effect"] == "allow"


# ---------------------------------------------------------------------------
# S7 health summary tests
# ---------------------------------------------------------------------------

def _make_overview_patches(monkeypatch, *, agents=None, approvals=None, plans=None):
    """Helper: patch services.core reads with controlled data."""
    core = importlib.import_module("services.core")
    monkeypatch.setattr(core, "list_agent_catalog", lambda: {"agents": agents or []})
    monkeypatch.setattr(core, "list_pending_approvals", lambda: {"approvals": approvals or []})
    monkeypatch.setattr(core, "list_recent_traces", lambda limit=5: {"traces": []})
    monkeypatch.setattr(core, "list_recent_plans", lambda limit=5: {"plans": plans or []})
    monkeypatch.setattr(core, "list_recent_governance_decisions", lambda limit=5: {"governance": []})
    monkeypatch.setattr(core, "get_governance_state", lambda: {"engine": "PolicyEngine", "registry": "R", "policy_path": None})
    return core


def test_health_section_present_in_overview(monkeypatch):
    core = _make_overview_patches(monkeypatch)
    overview = core.get_control_plane_overview()
    assert "health" in overview
    health = overview["health"]
    assert "overall" in health
    assert health["overall"] in {"healthy", "attention", "degraded"}


def test_health_healthy_when_all_clear(monkeypatch):
    core = _make_overview_patches(monkeypatch, agents=[], approvals=[], plans=[])
    overview = core.get_control_plane_overview()
    assert overview["health"]["overall"] == "healthy"
    assert overview["health"]["attention_items"] == []


def test_health_attention_when_pending_approvals(monkeypatch):
    core = _make_overview_patches(
        monkeypatch,
        approvals=[{"approval_id": "ap-1", "status": "pending"}],
    )
    overview = core.get_control_plane_overview()
    health = overview["health"]
    assert health["overall"] == "attention"
    assert health["pending_approval_count"] == 1
    labels = [item["label"] for item in health["attention_items"]]
    assert any("approval" in label.lower() for label in labels)


def test_health_attention_when_paused_plan(monkeypatch):
    core = _make_overview_patches(
        monkeypatch,
        plans=[{"plan_id": "plan-1", "workflow_name": "My Flow", "status": "paused"}],
    )
    overview = core.get_control_plane_overview()
    health = overview["health"]
    assert health["overall"] == "attention"
    assert health["paused_plan_count"] == 1


def test_health_attention_when_failed_plan(monkeypatch):
    core = _make_overview_patches(
        monkeypatch,
        plans=[{"plan_id": "plan-f", "workflow_name": "Bad Flow", "status": "failed"}],
    )
    overview = core.get_control_plane_overview()
    health = overview["health"]
    assert health["overall"] == "attention"
    assert health["failed_plan_count"] == 1


def test_health_attention_when_degraded_agent(monkeypatch):
    core = _make_overview_patches(
        monkeypatch,
        agents=[{"agent_id": "ag-1", "display_name": "Sluggish Agent", "availability": "degraded"}],
    )
    overview = core.get_control_plane_overview()
    health = overview["health"]
    assert health["overall"] == "attention"
    assert health["degraded_agent_count"] == 1


def test_health_degraded_when_offline_agent(monkeypatch):
    core = _make_overview_patches(
        monkeypatch,
        agents=[{"agent_id": "ag-2", "display_name": "Dead Agent", "availability": "offline"}],
    )
    overview = core.get_control_plane_overview()
    health = overview["health"]
    assert health["overall"] == "degraded"
    assert health["offline_agent_count"] == 1


def test_health_layer_statuses_in_overview(monkeypatch):
    core = _make_overview_patches(monkeypatch)
    overview = core.get_control_plane_overview()
    layers = overview["system"]["layers"]
    layer_names = [l["name"] for l in layers]
    assert "Decision" in layer_names
    assert "Governance" in layer_names
    assert "MCP v2" in layer_names
    # All reads succeed in this test — all layers should be available
    for layer in layers:
        assert layer["status"] == "available"


def test_health_warnings_surface_in_has_warnings(monkeypatch):
    core = importlib.import_module("services.core")
    # Simulate a failed read by raising from list_agent_catalog
    monkeypatch.setattr(core, "list_agent_catalog", lambda: (_ for _ in ()).throw(RuntimeError("disk error")))
    monkeypatch.setattr(core, "list_pending_approvals", lambda: {"approvals": []})
    monkeypatch.setattr(core, "list_recent_traces", lambda limit=5: {"traces": []})
    monkeypatch.setattr(core, "list_recent_plans", lambda limit=5: {"plans": []})
    monkeypatch.setattr(core, "list_recent_governance_decisions", lambda limit=5: {"governance": []})
    monkeypatch.setattr(core, "get_governance_state", lambda: {"engine": "E", "registry": "R", "policy_path": None})

    overview = core.get_control_plane_overview()
    assert overview["health"]["has_warnings"] is True
    assert overview["system"]["warnings"]  # at least one warning string captured


def test_compute_health_summary_direct():
    """Unit-test _compute_health_summary in isolation."""
    core = importlib.import_module("services.core")
    summary = core._compute_health_summary(
        agents=[
            {"agent_id": "a1", "availability": "degraded"},
            {"agent_id": "a2", "availability": "online"},
        ],
        approvals=[{"approval_id": "ap-1"}],
        plans=[
            {"plan_id": "p1", "status": "failed"},
            {"plan_id": "p2", "status": "completed"},
        ],
        warnings=[],
        layers=[{"name": "Decision", "status": "available"}],
    )
    assert summary["degraded_agent_count"] == 1
    assert summary["offline_agent_count"] == 0
    assert summary["failed_plan_count"] == 1
    assert summary["pending_approval_count"] == 1
    assert summary["overall"] == "attention"
    assert len(summary["attention_items"]) > 0
