"""Tests for manifest-driven output validation (Phase 2 — S18).

Covers:
1. missing_result_metadata_keys() — pure helper function
2. validate_result() — structural invariants + required result metadata keys
3. result_warnings() — capability-based soft warnings
4. BaseExecutionAdapter.validate_result() — delegation to pure function
5. Integration: manifest.required_result_metadata_keys on Flowise adapter
"""

from __future__ import annotations

import pytest

from core.execution.adapters import (
    AdminBotExecutionAdapter,
    FlowiseExecutionAdapter,
    missing_result_metadata_keys,
    result_warnings,
    validate_result,
)
from core.execution.adapters.base import BaseExecutionAdapter, ExecutionResult
from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.provider_capabilities import ExecutionCapabilities
from core.models.errors import StructuredError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _manifest(
    required_result_keys: list[str] = (),
    name: str = "test-adapter",
    supports_cost: bool = False,
    supports_tokens: bool = False,
) -> AdapterManifest:
    return AdapterManifest(
        adapter_name=name,
        description="Test manifest.",
        capabilities=ExecutionCapabilities(
            execution_protocol="http_api",
            requires_network=True,
            requires_local_process=False,
            supports_cost_reporting=supports_cost,
            supports_token_reporting=supports_tokens,
        ),
        risk_tier=RiskTier.LOW,
        required_result_metadata_keys=list(required_result_keys),
    )


def _ok(agent_id: str = "agent-1", metadata: dict | None = None, **kwargs) -> ExecutionResult:
    return ExecutionResult(agent_id=agent_id, success=True, metadata=metadata or {}, **kwargs)


def _err(
    agent_id: str = "agent-1",
    error_code: str = "execution_error",
    metadata: dict | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        agent_id=agent_id,
        success=False,
        error=StructuredError(error_code=error_code, message="error"),
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 1. missing_result_metadata_keys()
# ---------------------------------------------------------------------------


def test_missing_result_metadata_keys_empty_when_all_present():
    manifest = _manifest(["runtime_contract", "session_id"])
    result = _ok(metadata={"runtime_contract": "v1", "session_id": "s-1"})
    assert missing_result_metadata_keys(manifest, result) == []


def test_missing_result_metadata_keys_returns_absent_keys():
    manifest = _manifest(["runtime_contract", "session_id"])
    result = _ok(metadata={"runtime_contract": "v1"})
    assert missing_result_metadata_keys(manifest, result) == ["session_id"]


def test_missing_result_metadata_keys_exempt_on_error_result():
    """Error results are not checked for required result metadata keys."""
    manifest = _manifest(["runtime_contract"])
    result = _err(metadata={})  # missing runtime_contract but success=False
    assert missing_result_metadata_keys(manifest, result) == []


def test_missing_result_metadata_keys_no_requirements_always_empty():
    manifest = _manifest([])
    result = _ok(metadata={})
    assert missing_result_metadata_keys(manifest, result) == []


def test_missing_result_metadata_keys_extra_keys_not_flagged():
    manifest = _manifest(["runtime_contract"])
    result = _ok(metadata={"runtime_contract": "v1", "extra": "ignored"})
    assert missing_result_metadata_keys(manifest, result) == []


# ---------------------------------------------------------------------------
# 2. validate_result() — structural invariants
# ---------------------------------------------------------------------------


def test_validate_result_passes_for_clean_success():
    manifest = _manifest()
    validate_result(manifest, _ok())  # must not raise


def test_validate_result_passes_for_clean_error():
    manifest = _manifest()
    validate_result(manifest, _err())  # must not raise


def test_validate_result_raises_on_empty_agent_id():
    manifest = _manifest(name="my-adapter")
    result = _ok(agent_id="")
    with pytest.raises(ValueError) as exc_info:
        validate_result(manifest, result)
    assert "agent_id" in str(exc_info.value)


def test_validate_result_raises_when_success_with_error_set():
    manifest = _manifest(name="bad-adapter")
    result = ExecutionResult(
        agent_id="a",
        success=True,
        error=StructuredError(error_code="execution_error", message="oops"),
    )
    with pytest.raises(ValueError) as exc_info:
        validate_result(manifest, result)
    assert "success=True" in str(exc_info.value)
    assert "error" in str(exc_info.value)


def test_validate_result_raises_when_failure_without_error():
    manifest = _manifest(name="bad-adapter")
    result = ExecutionResult(agent_id="a", success=False)
    with pytest.raises(ValueError) as exc_info:
        validate_result(manifest, result)
    assert "success=False" in str(exc_info.value)
    assert "error" in str(exc_info.value)


def test_validate_result_raises_when_failure_with_empty_error_code():
    manifest = _manifest(name="bad-adapter")
    result = ExecutionResult(
        agent_id="a",
        success=False,
        error=StructuredError(error_code="   ", message="empty code"),
    )
    with pytest.raises(ValueError) as exc_info:
        validate_result(manifest, result)
    assert "error_code" in str(exc_info.value)


def test_validate_result_raises_on_missing_required_result_metadata():
    manifest = _manifest(["runtime_contract"], name="flowise")
    result = _ok(metadata={})  # missing runtime_contract
    with pytest.raises(ValueError) as exc_info:
        validate_result(manifest, result)
    assert "runtime_contract" in str(exc_info.value)
    assert "flowise" in str(exc_info.value)


def test_validate_result_required_result_metadata_passes_when_present():
    manifest = _manifest(["runtime_contract"], name="flowise")
    result = _ok(metadata={"runtime_contract": "prediction_v1"})
    validate_result(manifest, result)  # must not raise


def test_validate_result_error_message_names_adapter():
    manifest = _manifest(name="my-named-adapter")
    result = _ok(agent_id="")  # triggers empty agent_id error
    with pytest.raises(ValueError) as exc_info:
        validate_result(manifest, result)
    assert "my-named-adapter" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. result_warnings()
# ---------------------------------------------------------------------------


def test_result_warnings_empty_when_no_capabilities_declared():
    manifest = _manifest(supports_cost=False, supports_tokens=False)
    assert result_warnings(manifest, _ok()) == []


def test_result_warnings_empty_when_cost_present():
    manifest = _manifest(supports_cost=True)
    result = _ok(cost=0.05)
    assert result_warnings(manifest, result) == []


def test_result_warnings_warns_when_cost_missing():
    manifest = _manifest(supports_cost=True, name="flowise")
    result = _ok(cost=None)
    warnings = result_warnings(manifest, result)
    assert len(warnings) == 1
    assert "cost" in warnings[0]
    assert "flowise" in warnings[0]


def test_result_warnings_warns_when_token_count_missing():
    manifest = _manifest(supports_tokens=True, name="claude-code")
    result = _ok(token_count=None)
    warnings = result_warnings(manifest, result)
    assert len(warnings) == 1
    assert "token_count" in warnings[0]


def test_result_warnings_both_when_both_missing():
    manifest = _manifest(supports_cost=True, supports_tokens=True, name="codex")
    result = _ok()
    warnings = result_warnings(manifest, result)
    assert len(warnings) == 2


def test_result_warnings_empty_for_error_results():
    """Capability warnings are only emitted for success results."""
    manifest = _manifest(supports_cost=True, supports_tokens=True)
    assert result_warnings(manifest, _err()) == []


def test_result_warnings_zero_cost_is_not_a_warning():
    """A cost of 0.0 is a valid reported cost, not a missing value."""
    manifest = _manifest(supports_cost=True)
    result = _ok(cost=0.0)
    assert result_warnings(manifest, result) == []


# ---------------------------------------------------------------------------
# 4. BaseExecutionAdapter.validate_result()
# ---------------------------------------------------------------------------


class _ConcreteAdapter(BaseExecutionAdapter):
    adapter_name = "concrete-out"
    manifest = _manifest(required_result_keys=["contract_key"], name="concrete-out")

    def execute(self, task, agent_descriptor):
        raise NotImplementedError


def test_base_adapter_validate_result_passes_clean_success():
    adapter = _ConcreteAdapter()
    result = _ok(metadata={"contract_key": "ok"})
    adapter.validate_result(result)  # must not raise


def test_base_adapter_validate_result_raises_on_missing_required_key():
    adapter = _ConcreteAdapter()
    result = _ok(metadata={})  # missing contract_key
    with pytest.raises(ValueError) as exc_info:
        adapter.validate_result(result)
    assert "contract_key" in str(exc_info.value)


def test_base_adapter_validate_result_raises_on_success_with_error():
    adapter = _ConcreteAdapter()
    result = ExecutionResult(
        agent_id="a",
        success=True,
        metadata={"contract_key": "ok"},
        error=StructuredError(error_code="x", message="bad"),
    )
    with pytest.raises(ValueError):
        adapter.validate_result(result)


def test_base_adapter_validate_result_passes_error_result():
    adapter = _ConcreteAdapter()
    result = _err()  # error results exempt from required_result_metadata_keys
    adapter.validate_result(result)  # must not raise


# ---------------------------------------------------------------------------
# 5. Integration: Flowise manifest.required_result_metadata_keys
# ---------------------------------------------------------------------------


def test_flowise_manifest_declares_required_result_metadata():
    assert "runtime_contract" in FlowiseExecutionAdapter.manifest.required_result_metadata_keys


def test_flowise_validate_result_passes_with_runtime_contract(monkeypatch):
    from core.execution.adapters import FlowiseExecutionAdapter

    dummy_result = _ok(
        agent_id="flowise-1",
        metadata={
            "runtime_contract": "prediction_v1",
            "chatflow_id": "cf-1",
        },
    )
    adapter = FlowiseExecutionAdapter()
    adapter.validate_result(dummy_result)  # must not raise


def test_flowise_validate_result_raises_without_runtime_contract():
    adapter = FlowiseExecutionAdapter()
    result = _ok(agent_id="flowise-1", metadata={"chatflow_id": "cf-1"})
    with pytest.raises(ValueError) as exc_info:
        adapter.validate_result(result)
    assert "runtime_contract" in str(exc_info.value)


def test_adminbot_manifest_requires_no_result_metadata():
    assert AdminBotExecutionAdapter.manifest.required_result_metadata_keys == []
