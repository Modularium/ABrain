"""Tests for Phase 2 S20: adapter budget limits and isolation declarations.

Coverage:
1. AdapterBudget model — field validation, defaults
2. IsolationRequirements model — field validation, defaults
3. budget_warnings() — cost, duration, token violations; no-violation cases
4. Engine integration — budget warnings flow through ExecutionResult.warnings
5. Concrete adapter manifests — budget and isolation declarations present
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from core.execution.adapters.budget import AdapterBudget, IsolationRequirements
from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.provider_capabilities import ExecutionCapabilities
from core.execution.adapters.validation import budget_warnings
from core.execution.adapters.base import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manifest(
    *,
    max_cost_usd: float | None = None,
    max_duration_ms: int | None = None,
    max_tokens: int | None = None,
) -> AdapterManifest:
    return AdapterManifest(
        adapter_name="test_adapter",
        description="test",
        capabilities=ExecutionCapabilities(
            execution_protocol="tool_dispatch",
            requires_network=False,
            requires_local_process=False,
            supports_cost_reporting=True,
            supports_token_reporting=True,
        ),
        risk_tier=RiskTier.LOW,
        budget=AdapterBudget(
            max_cost_usd=max_cost_usd,
            max_duration_ms=max_duration_ms,
            max_tokens=max_tokens,
        ),
    )


def _result(
    *,
    success: bool = True,
    cost: float | None = None,
    duration_ms: int | None = None,
    token_count: int | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        agent_id="agent-1",
        success=success,
        cost=cost,
        duration_ms=duration_ms,
        token_count=token_count,
    )


# ---------------------------------------------------------------------------
# 1. AdapterBudget model
# ---------------------------------------------------------------------------

class TestAdapterBudget:
    def test_defaults_are_unconstrained(self):
        b = AdapterBudget()
        assert b.max_cost_usd is None
        assert b.max_duration_ms is None
        assert b.max_tokens is None

    def test_valid_values_accepted(self):
        b = AdapterBudget(max_cost_usd=1.5, max_duration_ms=5000, max_tokens=4000)
        assert b.max_cost_usd == 1.5
        assert b.max_duration_ms == 5000
        assert b.max_tokens == 4000

    def test_zero_cost_accepted(self):
        b = AdapterBudget(max_cost_usd=0.0)
        assert b.max_cost_usd == 0.0

    def test_negative_cost_rejected(self):
        with pytest.raises(Exception):
            AdapterBudget(max_cost_usd=-0.01)

    def test_zero_duration_rejected(self):
        with pytest.raises(Exception):
            AdapterBudget(max_duration_ms=0)

    def test_zero_tokens_rejected(self):
        with pytest.raises(Exception):
            AdapterBudget(max_tokens=0)

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            AdapterBudget(max_cost_usd=1.0, unknown_field="x")


# ---------------------------------------------------------------------------
# 2. IsolationRequirements model
# ---------------------------------------------------------------------------

class TestIsolationRequirements:
    def test_defaults_all_false(self):
        iso = IsolationRequirements()
        assert iso.network_access_required is False
        assert iso.filesystem_write_required is False
        assert iso.process_spawn_required is False
        assert iso.privileged_operation is False

    def test_high_risk_profile(self):
        iso = IsolationRequirements(
            network_access_required=True,
            filesystem_write_required=True,
            process_spawn_required=True,
            privileged_operation=False,
        )
        assert iso.network_access_required is True
        assert iso.filesystem_write_required is True
        assert iso.process_spawn_required is True
        assert iso.privileged_operation is False

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            IsolationRequirements(unknown_field=True)


# ---------------------------------------------------------------------------
# 3. budget_warnings() — violation logic
# ---------------------------------------------------------------------------

class TestBudgetWarnings:
    # No violations when limits not set
    def test_no_limits_no_warnings(self):
        m = _manifest()
        r = _result(cost=999.0, duration_ms=999_999, token_count=999_999)
        assert budget_warnings(m, r) == []

    # Cost violations
    def test_cost_exceeded_emits_warning(self):
        m = _manifest(max_cost_usd=1.0)
        r = _result(cost=1.001)
        warns = budget_warnings(m, r)
        assert len(warns) == 1
        assert "max_cost_usd" in warns[0]
        assert "test_adapter" in warns[0]

    def test_cost_exactly_at_limit_no_warning(self):
        m = _manifest(max_cost_usd=1.0)
        r = _result(cost=1.0)
        assert budget_warnings(m, r) == []

    def test_cost_below_limit_no_warning(self):
        m = _manifest(max_cost_usd=1.0)
        r = _result(cost=0.5)
        assert budget_warnings(m, r) == []

    def test_cost_limit_set_but_result_cost_none_no_warning(self):
        m = _manifest(max_cost_usd=1.0)
        r = _result(cost=None)
        assert budget_warnings(m, r) == []

    # Duration violations
    def test_duration_exceeded_emits_warning(self):
        m = _manifest(max_duration_ms=5_000)
        r = _result(duration_ms=5_001)
        warns = budget_warnings(m, r)
        assert len(warns) == 1
        assert "max_duration_ms" in warns[0]

    def test_duration_exactly_at_limit_no_warning(self):
        m = _manifest(max_duration_ms=5_000)
        r = _result(duration_ms=5_000)
        assert budget_warnings(m, r) == []

    def test_duration_limit_set_but_result_none_no_warning(self):
        m = _manifest(max_duration_ms=5_000)
        r = _result(duration_ms=None)
        assert budget_warnings(m, r) == []

    # Token violations
    def test_tokens_exceeded_emits_warning(self):
        m = _manifest(max_tokens=4_000)
        r = _result(token_count=4_001)
        warns = budget_warnings(m, r)
        assert len(warns) == 1
        assert "max_tokens" in warns[0]

    def test_tokens_exactly_at_limit_no_warning(self):
        m = _manifest(max_tokens=4_000)
        r = _result(token_count=4_000)
        assert budget_warnings(m, r) == []

    # Multiple simultaneous violations
    def test_multiple_violations_all_reported(self):
        m = _manifest(max_cost_usd=1.0, max_duration_ms=5_000, max_tokens=4_000)
        r = _result(cost=2.0, duration_ms=10_000, token_count=8_000)
        warns = budget_warnings(m, r)
        assert len(warns) == 3

    # Error results still checked (runaway executions visible in trace)
    def test_error_result_also_checked(self):
        m = _manifest(max_duration_ms=5_000)
        r = _result(success=False, duration_ms=99_999)
        warns = budget_warnings(m, r)
        assert len(warns) == 1
        assert "max_duration_ms" in warns[0]


# ---------------------------------------------------------------------------
# 4. Engine integration — budget_warnings wired into ExecutionResult.warnings
# ---------------------------------------------------------------------------

class TestEngineIntegration:
    """Verify that budget violations surface in result.warnings via the engine."""

    def test_budget_warnings_present_in_result_after_execution(self):
        from unittest.mock import MagicMock, patch
        from core.execution.execution_engine import ExecutionEngine
        from core.decision import RoutingDecision
        from core.execution.adapters.base import ExecutionResult
        from core.execution.adapters.manifest import AdapterManifest, RiskTier
        from core.execution.adapters.budget import AdapterBudget
        from core.execution.provider_capabilities import ExecutionCapabilities

        # Build a mock adapter that returns a result exceeding its own budget
        mock_adapter = MagicMock()
        mock_adapter.adapter_name = "test_budget_adapter"
        mock_adapter.manifest = AdapterManifest(
            adapter_name="test_budget_adapter",
            description="test",
            capabilities=ExecutionCapabilities(
                execution_protocol="tool_dispatch",
                requires_network=False,
                requires_local_process=False,
                supports_cost_reporting=True,
                supports_token_reporting=False,
            ),
            risk_tier=RiskTier.LOW,
            budget=AdapterBudget(max_cost_usd=0.10),
        )
        mock_adapter.validate.return_value = None
        mock_adapter.execute.return_value = ExecutionResult(
            agent_id="agent-budget",
            success=True,
            cost=0.50,  # exceeds budget of 0.10
        )

        mock_registry = MagicMock()
        mock_registry.resolve.return_value = mock_adapter

        engine = ExecutionEngine(adapter_registry=mock_registry)

        from core.decision.agent_descriptor import AgentDescriptor, AgentSourceType, AgentExecutionKind
        descriptor = AgentDescriptor(
            agent_id="agent-budget",
            display_name="Budget Test Agent",
            source_type=AgentSourceType.ADMINBOT,
            execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
        )
        decision = RoutingDecision(
            task_type="test",
            selected_agent_id="agent-budget",
        )

        result = engine.execute({"task_type": "test"}, decision, {"agent-budget": descriptor})
        budget_warns = [w for w in result.warnings if "max_cost_usd" in w]
        assert len(budget_warns) == 1
        assert "0.50" in budget_warns[0] or "0.5" in budget_warns[0]


# ---------------------------------------------------------------------------
# 5. Concrete adapter manifests — budget and isolation present
# ---------------------------------------------------------------------------

class TestConcreteAdapterManifests:
    """Verify every concrete adapter declares budget and isolation."""

    def _adapters(self):
        from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
        from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
        from core.execution.adapters.n8n_adapter import N8NExecutionAdapter
        from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
        from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
        from core.execution.adapters.codex_adapter import CodexExecutionAdapter
        return [
            AdminBotExecutionAdapter,
            FlowiseExecutionAdapter,
            N8NExecutionAdapter,
            OpenHandsExecutionAdapter,
            ClaudeCodeExecutionAdapter,
            CodexExecutionAdapter,
        ]

    def test_all_adapters_have_budget(self):
        for cls in self._adapters():
            assert isinstance(cls.manifest.budget, AdapterBudget), (
                f"{cls.__name__} manifest.budget is not an AdapterBudget"
            )

    def test_all_adapters_have_isolation(self):
        for cls in self._adapters():
            assert isinstance(cls.manifest.isolation, IsolationRequirements), (
                f"{cls.__name__} manifest.isolation is not IsolationRequirements"
            )

    def test_adminbot_has_duration_budget(self):
        from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
        assert AdminBotExecutionAdapter.manifest.budget.max_duration_ms is not None
        assert AdminBotExecutionAdapter.manifest.budget.max_duration_ms <= 10_000

    def test_adminbot_no_network_isolation(self):
        from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
        iso = AdminBotExecutionAdapter.manifest.isolation
        assert iso.network_access_required is False
        assert iso.filesystem_write_required is False
        assert iso.process_spawn_required is False

    def test_high_risk_adapters_have_cost_budget(self):
        from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
        from core.execution.adapters.codex_adapter import CodexExecutionAdapter
        from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
        for cls in [ClaudeCodeExecutionAdapter, CodexExecutionAdapter, OpenHandsExecutionAdapter]:
            assert cls.manifest.budget.max_cost_usd is not None, (
                f"{cls.__name__} HIGH-tier adapter must declare max_cost_usd"
            )

    def test_high_risk_adapters_isolation_requires_process_or_network(self):
        from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
        from core.execution.adapters.codex_adapter import CodexExecutionAdapter
        from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
        for cls in [ClaudeCodeExecutionAdapter, CodexExecutionAdapter, OpenHandsExecutionAdapter]:
            iso = cls.manifest.isolation
            assert iso.filesystem_write_required or iso.process_spawn_required or iso.network_access_required, (
                f"{cls.__name__} HIGH-tier adapter must declare at least one isolation requirement"
            )

    def test_medium_risk_adapters_network_required(self):
        from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
        from core.execution.adapters.n8n_adapter import N8NExecutionAdapter
        for cls in [FlowiseExecutionAdapter, N8NExecutionAdapter]:
            assert cls.manifest.isolation.network_access_required is True, (
                f"{cls.__name__} MEDIUM-tier network adapter must declare network_access_required"
            )

    def test_medium_risk_adapters_have_token_budget(self):
        from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
        from core.execution.adapters.n8n_adapter import N8NExecutionAdapter
        for cls in [FlowiseExecutionAdapter, N8NExecutionAdapter]:
            assert cls.manifest.budget.max_tokens is not None, (
                f"{cls.__name__} MEDIUM-tier adapter should declare max_tokens"
            )
