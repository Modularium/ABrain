"""Tests for canonical execution audit event helpers (Phase 2 — S19).

Covers:
1. canonical_execution_span_attributes() — canonical attribute dict shape
2. CANONICAL_EXECUTION_SPAN_KEYS exhaustiveness
3. ExecutionEngine.execute() — risk_tier in metadata and capability warnings
4. services/core.py path — not tested here (integration-level), relies on
   audit function tests above
"""

from __future__ import annotations

import pytest

from core.execution.adapters import AdminBotExecutionAdapter, FlowiseExecutionAdapter
from core.execution.adapters.base import ExecutionResult
from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.adapters.validation import result_warnings
from core.execution.audit import (
    CANONICAL_EXECUTION_SPAN_KEYS,
    canonical_execution_span_attributes,
)
from core.execution.provider_capabilities import ExecutionCapabilities
from core.models.errors import StructuredError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ok(
    agent_id: str = "agent-1",
    metadata: dict | None = None,
    cost: float | None = None,
    token_count: int | None = None,
    duration_ms: int | None = None,
    warnings: list[str] | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        agent_id=agent_id,
        success=True,
        metadata=metadata or {},
        cost=cost,
        token_count=token_count,
        duration_ms=duration_ms,
        warnings=warnings or [],
    )


def _err(agent_id: str = "agent-1", metadata: dict | None = None) -> ExecutionResult:
    return ExecutionResult(
        agent_id=agent_id,
        success=False,
        error=StructuredError(error_code="execution_error", message="fail"),
        metadata=metadata or {},
    )


def _full_metadata(
    adapter_name: str = "test-adapter",
    risk_tier: str = "low",
    source_type: str = "native",
    execution_kind: str = "http_service",
) -> dict:
    return {
        "adapter_name": adapter_name,
        "risk_tier": risk_tier,
        "source_type": source_type,
        "execution_kind": execution_kind,
        "execution_engine": "v1",
    }


# ---------------------------------------------------------------------------
# 1. canonical_execution_span_attributes() shape and values
# ---------------------------------------------------------------------------


def test_canonical_attributes_keys_match_canonical_keys():
    result = _ok(metadata=_full_metadata())
    attrs = canonical_execution_span_attributes(result, task_type="dev", policy_effect="allow")
    assert set(attrs.keys()) == set(CANONICAL_EXECUTION_SPAN_KEYS)


def test_canonical_attributes_agent_id():
    result = _ok(agent_id="my-agent", metadata=_full_metadata())
    attrs = canonical_execution_span_attributes(result, task_type="dev", policy_effect="allow")
    assert attrs["agent_id"] == "my-agent"


def test_canonical_attributes_adapter_name_from_metadata():
    result = _ok(metadata=_full_metadata(adapter_name="flowise"))
    attrs = canonical_execution_span_attributes(result, task_type="analysis", policy_effect="allow")
    assert attrs["adapter_name"] == "flowise"


def test_canonical_attributes_task_type_from_caller():
    result = _ok(metadata=_full_metadata())
    attrs = canonical_execution_span_attributes(result, task_type="code_review", policy_effect="allow")
    assert attrs["task_type"] == "code_review"


def test_canonical_attributes_risk_tier_from_metadata():
    result = _ok(metadata=_full_metadata(risk_tier="high"))
    attrs = canonical_execution_span_attributes(result, task_type="dev", policy_effect="allow")
    assert attrs["risk_tier"] == "high"


def test_canonical_attributes_source_type_and_execution_kind():
    result = _ok(metadata=_full_metadata(source_type="flowise", execution_kind="workflow_engine"))
    attrs = canonical_execution_span_attributes(result, task_type="workflow", policy_effect="allow")
    assert attrs["source_type"] == "flowise"
    assert attrs["execution_kind"] == "workflow_engine"


def test_canonical_attributes_success_true():
    result = _ok(metadata=_full_metadata())
    attrs = canonical_execution_span_attributes(result, task_type="x", policy_effect="allow")
    assert attrs["success"] is True


def test_canonical_attributes_success_false():
    result = _err(metadata=_full_metadata())
    attrs = canonical_execution_span_attributes(result, task_type="x", policy_effect="allow")
    assert attrs["success"] is False


def test_canonical_attributes_duration_ms():
    result = _ok(metadata=_full_metadata(), duration_ms=1234)
    attrs = canonical_execution_span_attributes(result, task_type="x", policy_effect="allow")
    assert attrs["duration_ms"] == 1234


def test_canonical_attributes_cost_and_token_count():
    result = _ok(metadata=_full_metadata(), cost=0.07, token_count=512)
    attrs = canonical_execution_span_attributes(result, task_type="x", policy_effect="allow")
    assert attrs["cost"] == pytest.approx(0.07)
    assert attrs["token_count"] == 512


def test_canonical_attributes_warning_count():
    result = _ok(metadata=_full_metadata(), warnings=["w1", "w2"])
    attrs = canonical_execution_span_attributes(result, task_type="x", policy_effect="allow")
    assert attrs["warning_count"] == 2


def test_canonical_attributes_policy_effect_from_caller():
    result = _ok(metadata=_full_metadata())
    for effect in ("allow", "deny", "approval_required"):
        attrs = canonical_execution_span_attributes(result, task_type="x", policy_effect=effect)
        assert attrs["policy_effect"] == effect


def test_canonical_attributes_missing_metadata_defaults_to_empty_string():
    result = _ok(metadata={})  # no adapter_name, risk_tier, etc.
    attrs = canonical_execution_span_attributes(result, task_type="x", policy_effect="allow")
    assert attrs["adapter_name"] == ""
    assert attrs["risk_tier"] == ""
    assert attrs["source_type"] == ""
    assert attrs["execution_kind"] == ""


# ---------------------------------------------------------------------------
# 2. CANONICAL_EXECUTION_SPAN_KEYS exhaustiveness
# ---------------------------------------------------------------------------


def test_canonical_keys_are_non_empty_tuple():
    assert isinstance(CANONICAL_EXECUTION_SPAN_KEYS, tuple)
    assert len(CANONICAL_EXECUTION_SPAN_KEYS) > 0


def test_canonical_keys_contain_required_governance_fields():
    required = {"risk_tier", "policy_effect", "agent_id", "adapter_name", "success"}
    assert required.issubset(set(CANONICAL_EXECUTION_SPAN_KEYS))


def test_canonical_keys_no_duplicates():
    assert len(CANONICAL_EXECUTION_SPAN_KEYS) == len(set(CANONICAL_EXECUTION_SPAN_KEYS))


# ---------------------------------------------------------------------------
# 3. ExecutionEngine.execute() — risk_tier in metadata and capability warnings
# ---------------------------------------------------------------------------


def test_execution_engine_sets_risk_tier_in_metadata(monkeypatch):
    from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType, RoutingDecision
    from core.execution.execution_engine import ExecutionEngine
    from core.execution.adapters import AdminBotExecutionAdapter

    # AdminBot imports execute_tool lazily inside execute()
    monkeypatch.setattr(
        "services.core.execute_tool",
        lambda tool_name, payload=None, **kwargs: {"status": "ok"},
    )
    descriptor = AgentDescriptor(
        agent_id="adminbot-1",
        display_name="AdminBot",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
        capabilities=["system.read"],
    )
    decision = RoutingDecision(
        selected_agent_id="adminbot-1",
        task_type="system_status",
        required_capabilities=["system.read"],
        selected_score=1.0,
    )
    engine = ExecutionEngine()
    result = engine.execute({"task_type": "system_status"}, decision, [descriptor])
    assert "risk_tier" in result.metadata
    assert result.metadata["risk_tier"] == AdminBotExecutionAdapter.manifest.risk_tier.value


def test_execution_engine_appends_capability_warnings_for_cost_capable_adapter():
    """An adapter declaring supports_cost_reporting but returning cost=None gets a warning."""
    from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType, RoutingDecision
    from core.execution.adapters.base import BaseExecutionAdapter
    from core.execution.adapters.registry import ExecutionAdapterRegistry
    from core.execution.execution_engine import ExecutionEngine

    class _CostClaimingAdapter(BaseExecutionAdapter):
        adapter_name = "cost-claimant"
        manifest = AdapterManifest(
            adapter_name="cost-claimant",
            description="Claims cost support but never sets it.",
            capabilities=ExecutionCapabilities(
                execution_protocol="http_api",
                requires_network=False,
                requires_local_process=False,
                supports_cost_reporting=True,
                supports_token_reporting=False,
            ),
            risk_tier=RiskTier.LOW,
        )

        def execute(self, task, agent_descriptor):
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=True,
                cost=None,  # declared but not set
            )

    descriptor = AgentDescriptor(
        agent_id="cost-agent",
        display_name="Cost Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=["analysis"],
    )
    decision = RoutingDecision(
        selected_agent_id="cost-agent",
        task_type="analysis",
        required_capabilities=["analysis"],
        selected_score=1.0,
    )
    registry = ExecutionAdapterRegistry()
    # Inject adapter directly into the registry's internal table
    registry._adapters[
        (AgentExecutionKind.HTTP_SERVICE.value, AgentSourceType.NATIVE.value)
    ] = _CostClaimingAdapter()
    engine = ExecutionEngine(adapter_registry=registry)
    result = engine.execute({"task_type": "analysis"}, decision, [descriptor])

    assert any("cost" in w.lower() for w in result.warnings), \
        f"Expected cost warning in {result.warnings}"
    assert result.metadata.get("risk_tier") == "low"
