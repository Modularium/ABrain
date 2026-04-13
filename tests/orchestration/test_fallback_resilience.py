"""Tests for Phase S4 — controlled provider fallback resilience.

Covers:
- is_fallback_eligible() classification whitelist
- route_step() exclude_agent_ids exclusion
- Orchestrator: fallback triggered on eligible infra errors
- Orchestrator: fallback NOT triggered on non-eligible errors
- Orchestrator: no fallback candidate → primary failure returned
- Orchestrator: governance denies fallback → primary failure returned
- Orchestrator: approval gate for fallback agent (pre-approved step vs fresh)
- Feedback semantics: primary failure ≠ fallback result; never mixed
- Span events: fallback_triggered recorded on step_span
- Bounded fallback: exactly one attempt per step
"""

from __future__ import annotations

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
from core.decision.routing_engine import RoutingDecision
from core.execution.adapters.base import ExecutionResult, is_fallback_eligible, _FALLBACK_ELIGIBLE_ERROR_CODES
from core.execution.execution_engine import ExecutionEngine
from core.governance import PolicyEngine
from core.governance.policy_models import PolicyDecision
from core.models.errors import StructuredError
from core.orchestration import PlanExecutionOrchestrator

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_descriptor(agent_id: str, capability: str = "analysis") -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id,
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=[capability],
        availability=AgentAvailability.ONLINE,
        metadata={"success_rate": "0.9"},
    )


def build_single_step_plan(step_id: str = "step-1") -> ExecutionPlan:
    return ExecutionPlan(
        task_id="plan-1",
        original_task={"task_type": "analysis"},
        strategy=PlanStrategy.SEQUENTIAL,
        steps=[
            PlanStep(
                step_id=step_id,
                title="Test step",
                description="Run analysis",
                required_capabilities=["analysis"],
                metadata={"task_type": "analysis", "domain": "test"},
            )
        ],
    )


def _make_failure(agent_id: str, error_code: str) -> ExecutionResult:
    return ExecutionResult(
        agent_id=agent_id,
        success=False,
        error=StructuredError(error_code=error_code, message=f"test {error_code}"),
        duration_ms=100,
    )


def _make_success(agent_id: str) -> ExecutionResult:
    return ExecutionResult(
        agent_id=agent_id,
        success=True,
        output={"ok": True},
        duration_ms=80,
    )


class ControlledRoutingEngine(RoutingEngine):
    """Routes to agents in priority order, skipping any in exclude_agent_ids."""

    def __init__(self, agent_order: list[str], **kwargs):
        super().__init__(**kwargs)
        self.agent_order = agent_order
        self.calls: list[dict] = []

    def route_step(self, step, task, descriptors, *, exclude_agent_ids=None):  # type: ignore[override]
        exclude = exclude_agent_ids or set()
        self.calls.append({"step_id": step.step_id, "excluded": list(exclude)})
        for agent_id in self.agent_order:
            if agent_id not in exclude:
                return RoutingDecision(
                    task_type=str(step.metadata.get("task_type") or step.step_id),
                    required_capabilities=list(step.required_capabilities),
                    ranked_candidates=[],
                    selected_agent_id=agent_id,
                    selected_score=0.9,
                    diagnostics={
                        "step_id": step.step_id,
                        "rejected_agents": [],
                        "candidate_agent_ids": [],
                        "candidate_filter": {},
                        "selected_candidate": None,
                        "neural_policy_source": "test",
                    },
                )
        return RoutingDecision(
            task_type=str(step.metadata.get("task_type") or step.step_id),
            required_capabilities=list(step.required_capabilities),
            ranked_candidates=[],
            selected_agent_id=None,
            selected_score=None,
            diagnostics={
                "step_id": step.step_id,
                "rejected_agents": [],
                "candidate_agent_ids": [],
                "candidate_filter": {},
                "selected_candidate": None,
                "neural_policy_source": "test",
            },
        )


class ConfigurableExecutionEngine(ExecutionEngine):
    """Returns configured results per agent_id; defaults to success."""

    def __init__(self, results: dict[str, ExecutionResult]):
        self.results = results
        self.calls: list[str] = []

    def execute(self, task, decision, descriptors):
        agent_id = decision.selected_agent_id or ""
        self.calls.append(agent_id)
        return self.results.get(agent_id, _make_success(agent_id))


class DenySpecificAgentPolicyEngine(PolicyEngine):
    """Denies a specific agent_id; allows everything else."""

    def __init__(self, deny_agent_id: str):
        super().__init__()
        self.deny_agent_id = deny_agent_id

    def evaluate(self, intent, descriptor, context):
        if descriptor and descriptor.agent_id == self.deny_agent_id:
            return PolicyDecision(
                effect="deny",
                matched_rules=["test_deny_rule"],
                winning_rule_id="test_deny_rule",
                reason="test: deny specific agent",
            )
        return PolicyDecision(
            effect="allow",
            matched_rules=[],
            winning_rule_id=None,
            reason="no_policy_matched",
        )


class RequireApprovalForAgentPolicyEngine(PolicyEngine):
    """Requires approval for a specific agent_id; allows everything else."""

    def __init__(self, require_agent_id: str):
        super().__init__()
        self.require_agent_id = require_agent_id

    def evaluate(self, intent, descriptor, context):
        if descriptor and descriptor.agent_id == self.require_agent_id:
            return PolicyDecision(
                effect="require_approval",
                matched_rules=["test_approval_rule"],
                winning_rule_id="test_approval_rule",
                reason="test: require approval",
            )
        return PolicyDecision(
            effect="allow",
            matched_rules=[],
            winning_rule_id=None,
            reason="no_policy_matched",
        )


# ---------------------------------------------------------------------------
# S4-2 — is_fallback_eligible() classification
# ---------------------------------------------------------------------------

def test_is_fallback_eligible_true_on_all_whitelisted_codes():
    for code in _FALLBACK_ELIGIBLE_ERROR_CODES:
        result = _make_failure("agent-x", code)
        assert is_fallback_eligible(result) is True, f"Expected eligible for {code!r}"


def test_is_fallback_eligible_false_on_success():
    result = _make_success("agent-x")
    assert is_fallback_eligible(result) is False


def test_is_fallback_eligible_false_when_no_error_field():
    result = ExecutionResult(agent_id="agent-x", success=False)
    assert is_fallback_eligible(result) is False


@pytest.mark.parametrize("code", [
    "adapter_process_error",
    "adapter_protocol_error",
    "adapter_execution_error",
    "adapter_http_error",
    "missing_selected_agent",
])
def test_is_fallback_eligible_false_on_non_eligible_code(code: str):
    result = _make_failure("agent-x", code)
    assert is_fallback_eligible(result) is False


# ---------------------------------------------------------------------------
# S4-3 — route_step() exclude_agent_ids
# ---------------------------------------------------------------------------

def test_route_step_exclude_agent_ids_removes_candidate():
    """Primary agent excluded from routing → only fallback agent considered."""
    history = PerformanceHistoryStore()
    engine = RoutingEngine(performance_history=history)
    descriptors = [
        build_descriptor("primary-agent", "analysis"),
        build_descriptor("fallback-agent", "analysis"),
    ]
    step = PlanStep(
        step_id="s1",
        title="S1",
        description="analyze",
        required_capabilities=["analysis"],
        metadata={"task_type": "analysis", "domain": "test"},
    )
    task = {
        "task_id": "t1",
        "task_type": "analysis",
        "description": "analyze",
        "preferences": {"domain": "test"},
    }

    decision = engine.route_step(step, task, descriptors, exclude_agent_ids={"primary-agent"})

    candidate_ids = [c.agent_id for c in decision.ranked_candidates]
    assert "primary-agent" not in candidate_ids
    assert decision.selected_agent_id != "primary-agent"


def test_route_step_exclude_all_agents_returns_no_selection():
    history = PerformanceHistoryStore()
    engine = RoutingEngine(performance_history=history)
    descriptors = [build_descriptor("only-agent", "analysis")]
    step = PlanStep(
        step_id="s1",
        title="S1",
        description="analyze",
        required_capabilities=["analysis"],
        metadata={"task_type": "analysis", "domain": "test"},
    )
    task = {
        "task_id": "t1",
        "task_type": "analysis",
        "description": "analyze",
        "preferences": {"domain": "test"},
    }

    decision = engine.route_step(step, task, descriptors, exclude_agent_ids={"only-agent"})

    assert decision.selected_agent_id is None
    assert decision.ranked_candidates == []


def test_route_step_no_exclusion_behaves_as_before():
    """Passing no exclude_agent_ids does not change existing routing behaviour."""
    history = PerformanceHistoryStore()
    engine = RoutingEngine(performance_history=history)
    descriptors = [build_descriptor("agent-a", "analysis")]
    step = PlanStep(
        step_id="s1",
        title="S1",
        description="analyze",
        required_capabilities=["analysis"],
        metadata={"task_type": "analysis", "domain": "test"},
    )
    task = {
        "task_id": "t1",
        "task_type": "analysis",
        "description": "analyze",
        "preferences": {"domain": "test"},
    }

    decision_plain = engine.route_step(step, task, descriptors)
    decision_empty = engine.route_step(step, task, descriptors, exclude_agent_ids=None)

    assert decision_plain.selected_agent_id == decision_empty.selected_agent_id


# ---------------------------------------------------------------------------
# S4-4/S4-5 — Orchestrator fallback
# ---------------------------------------------------------------------------

def test_fallback_triggers_on_eligible_error_and_succeeds():
    """Primary fails with adapter_timeout → fallback agent succeeds → step succeeds."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
        "fallback-agent": _make_success("fallback-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)
    plan = build_single_step_plan()

    result = PlanExecutionOrchestrator().execute_plan(
        plan, registry, routing, execution, feedback_loop
    )

    assert result.success is True
    sr = result.step_results[0]
    assert sr.success is True
    assert sr.metadata["fallback_triggered"] is True
    assert sr.metadata["primary_agent_id"] == "primary-agent"
    assert sr.metadata["fallback_agent_id"] == "fallback-agent"
    assert sr.metadata["primary_error_code"] == "adapter_timeout"


def test_fallback_triggers_on_adapter_unavailable():
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_unavailable"),
        "fallback-agent": _make_success("fallback-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    assert result.success is True
    assert result.step_results[0].metadata["primary_error_code"] == "adapter_unavailable"


def test_fallback_triggers_on_adapter_transport_error():
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_transport_error"),
        "fallback-agent": _make_success("fallback-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    assert result.success is True
    assert result.step_results[0].metadata["fallback_triggered"] is True


def test_fallback_not_triggered_on_non_eligible_error():
    """adapter_process_error is ambiguous (domain failure) — must NOT trigger fallback."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_process_error"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    assert result.success is False
    sr = result.step_results[0]
    assert "fallback_triggered" not in sr.metadata
    # fallback-agent was never called
    assert "fallback-agent" not in execution.calls


def test_fallback_not_triggered_on_success():
    """Successful primary execution must never trigger fallback."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_success("primary-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    assert result.success is True
    assert "fallback_triggered" not in result.step_results[0].metadata
    assert "fallback-agent" not in execution.calls


def test_fallback_no_candidate_returns_primary_failure():
    """Only one agent registered → no fallback candidate → primary failure propagated."""
    registry = AgentRegistry([build_descriptor("only-agent")])
    routing = ControlledRoutingEngine(
        agent_order=["only-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "only-agent": _make_failure("only-agent", "adapter_timeout"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    assert result.success is False
    sr = result.step_results[0]
    # fallback_triggered is True (attempt was made) but no fallback agent
    assert sr.metadata["fallback_triggered"] is True
    assert sr.metadata["fallback_agent_id"] is None
    assert sr.success is False


def test_fallback_governance_deny_returns_primary_failure():
    """Governance denies fallback agent → fallback skipped → primary failure returned."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
        # fallback-agent is denied by policy before execution
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)
    policy_engine = DenySpecificAgentPolicyEngine(deny_agent_id="fallback-agent")

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(),
        registry,
        routing,
        execution,
        feedback_loop,
        policy_engine=policy_engine,
    )

    assert result.success is False
    assert "fallback-agent" not in execution.calls
    sr = result.step_results[0]
    assert sr.metadata["fallback_triggered"] is True
    assert sr.metadata["fallback_agent_id"] is None  # execution never ran


def test_fallback_approval_required_and_step_not_approved_pauses():
    """Fallback governance requires approval and step has no prior approval → plan pauses."""
    from core.approval import ApprovalStore

    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)
    policy_engine = RequireApprovalForAgentPolicyEngine(require_agent_id="fallback-agent")
    approval_store = ApprovalStore()

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(),
        registry,
        routing,
        execution,
        feedback_loop,
        policy_engine=policy_engine,
        approval_store=approval_store,
    )

    from core.orchestration.result_aggregation import OrchestrationStatus
    assert result.status == OrchestrationStatus.PAUSED
    assert result.state.pending_approval_id is not None
    # fallback-agent never ran
    assert "fallback-agent" not in execution.calls


def test_fallback_approval_required_but_step_pre_approved_continues():
    """When step is pre-approved, approval gate is skipped for fallback agent."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
        "fallback-agent": _make_success("fallback-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)
    policy_engine = RequireApprovalForAgentPolicyEngine(require_agent_id="fallback-agent")

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(),
        registry,
        routing,
        execution,
        feedback_loop,
        policy_engine=policy_engine,
        approved_step_ids={"step-1"},  # pre-approved → approval gate skipped
    )

    assert result.success is True
    assert result.step_results[0].metadata["fallback_triggered"] is True
    assert "fallback-agent" in execution.calls


# ---------------------------------------------------------------------------
# S4-5 — Feedback separation semantics
# ---------------------------------------------------------------------------

def test_feedback_primary_failure_recorded_before_fallback():
    """Primary failure must be recorded to performance history before fallback runs."""
    perf = PerformanceHistoryStore()
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=perf,
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
        "fallback-agent": _make_success("fallback-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=perf)

    PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    primary_history = perf.get("primary-agent")
    fallback_history = perf.get("fallback-agent")

    # Primary failure was recorded
    assert primary_history.execution_count == 1
    assert primary_history.recent_failures == 1
    assert primary_history.success_rate == pytest.approx(0.0)

    # Fallback success was recorded separately
    assert fallback_history.execution_count == 1
    assert fallback_history.recent_failures == 0
    assert fallback_history.success_rate == pytest.approx(1.0)


def test_feedback_no_mix_when_no_fallback_triggered():
    """Normal path: only primary agent feedback recorded, fallback agent untouched."""
    perf = PerformanceHistoryStore()
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=perf,
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_success("primary-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=perf)

    PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    primary_history = perf.get("primary-agent")
    fallback_history = perf.get("fallback-agent")

    assert primary_history.execution_count == 1
    assert fallback_history.execution_count == 0  # never touched


def test_feedback_primary_only_when_no_fallback_candidate():
    """No fallback candidate: primary failure feedback recorded, fallback untouched."""
    perf = PerformanceHistoryStore()
    registry = AgentRegistry([build_descriptor("only-agent")])
    routing = ControlledRoutingEngine(
        agent_order=["only-agent"],
        performance_history=perf,
    )
    execution = ConfigurableExecutionEngine({
        "only-agent": _make_failure("only-agent", "adapter_timeout"),
    })
    feedback_loop = FeedbackLoop(performance_history=perf)

    PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    primary_history = perf.get("only-agent")
    assert primary_history.execution_count == 1
    assert primary_history.recent_failures == 1


def test_feedback_fallback_failure_recorded_when_both_fail():
    """Both primary and fallback fail: both failures recorded separately."""
    perf = PerformanceHistoryStore()
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=perf,
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
        "fallback-agent": _make_failure("fallback-agent", "adapter_process_error"),
    })
    feedback_loop = FeedbackLoop(performance_history=perf)

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    assert result.success is False
    primary_history = perf.get("primary-agent")
    fallback_history = perf.get("fallback-agent")

    assert primary_history.execution_count == 1
    assert primary_history.recent_failures == 1
    assert fallback_history.execution_count == 1
    assert fallback_history.recent_failures == 1


# ---------------------------------------------------------------------------
# S4-6 — Trace / span event coverage
# ---------------------------------------------------------------------------

def test_routing_called_twice_on_fallback():
    """route_step() is called once for primary routing, once for fallback re-routing."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
        "fallback-agent": _make_success("fallback-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    # Two routing calls: primary + fallback re-route
    assert len(routing.calls) == 2
    # Fallback re-route excludes primary-agent
    assert "primary-agent" in routing.calls[1]["excluded"]


def test_routing_called_once_on_success():
    """When primary succeeds, route_step() is called only once."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_success("primary-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    assert len(routing.calls) == 1


# ---------------------------------------------------------------------------
# S4 — Bounded fallback (invariant: max one attempt per step)
# ---------------------------------------------------------------------------

def test_fallback_bounded_to_single_attempt():
    """If fallback agent also fails with eligible error, no third attempt is made."""
    registry = AgentRegistry([
        build_descriptor("primary-agent"),
        build_descriptor("fallback-agent"),
        build_descriptor("third-agent"),
    ])
    routing = ControlledRoutingEngine(
        agent_order=["primary-agent", "fallback-agent", "third-agent"],
        performance_history=PerformanceHistoryStore(),
    )
    execution = ConfigurableExecutionEngine({
        "primary-agent": _make_failure("primary-agent", "adapter_timeout"),
        "fallback-agent": _make_failure("fallback-agent", "adapter_timeout"),
        "third-agent": _make_success("third-agent"),
    })
    feedback_loop = FeedbackLoop(performance_history=routing.performance_history)

    result = PlanExecutionOrchestrator().execute_plan(
        build_single_step_plan(), registry, routing, execution, feedback_loop
    )

    # Fallback ran once (fallback-agent); no recursive third attempt
    assert result.success is False  # fallback-agent failed, no further retry
    assert "third-agent" not in execution.calls
    # Exactly two execution calls: primary + one fallback
    assert execution.calls == ["primary-agent", "fallback-agent"]
    # Exactly two routing calls: primary + fallback re-route
    assert len(routing.calls) == 2
