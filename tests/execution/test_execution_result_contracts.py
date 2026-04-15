"""Adapter output schema contracts for regression detection.

These tests define and enforce the canonical shape of :class:`ExecutionResult`
across all adapter types.  They act as snapshot-level contracts: if the output
schema changes unexpectedly, these tests catch it before merge.

No network calls are made — adapters are exercised via monkeypatching or by
constructing `ExecutionResult` instances directly and asserting field invariants.

Sections
--------
1. ExecutionResult model field constraints
2. is_fallback_eligible() contract — all eligible + non-eligible codes
3. StructuredError field contracts
4. Per-adapter success/error output shape (monkeypatched network)
5. Fallback-eligible error code exhaustiveness
"""

from __future__ import annotations

from typing import Any

import pytest

from core.decision import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.execution.adapters.base import (
    ExecutionResult,
    _FALLBACK_ELIGIBLE_ERROR_CODES,
    is_fallback_eligible,
)
from core.models.errors import StructuredError

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(agent_id: str = "agent-1", **kwargs) -> ExecutionResult:
    return ExecutionResult(agent_id=agent_id, success=True, **kwargs)


def _err(agent_id: str = "agent-1", error_code: str = "execution_error", **kwargs) -> ExecutionResult:
    return ExecutionResult(
        agent_id=agent_id,
        success=False,
        error=StructuredError(error_code=error_code, message="error"),
        **kwargs,
    )


def _make_descriptor(
    agent_id: str = "agent-1",
    source_type: AgentSourceType = AgentSourceType.NATIVE,
    execution_kind: AgentExecutionKind = AgentExecutionKind.HTTP_SERVICE,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        source_type=source_type,
        execution_kind=execution_kind,
        capabilities=["analysis"],
    )


# ---------------------------------------------------------------------------
# 1. ExecutionResult model field constraints
# ---------------------------------------------------------------------------


def test_execution_result_requires_agent_id_and_success():
    result = _ok()
    assert result.agent_id == "agent-1"
    assert result.success is True


def test_execution_result_rejects_extra_fields():
    with pytest.raises(Exception):
        ExecutionResult(agent_id="x", success=True, unknown_field="bad")  # type: ignore[call-arg]


def test_execution_result_success_defaults():
    result = _ok()
    assert result.output is None
    assert result.raw_output is None
    assert result.metadata == {}
    assert result.warnings == []
    assert result.error is None
    assert result.duration_ms is None
    assert result.cost is None
    assert result.token_count is None


def test_execution_result_success_with_all_optional_fields():
    result = ExecutionResult(
        agent_id="agent-2",
        success=True,
        output={"status": "done", "files": ["a.py"]},
        raw_output="raw text",
        metadata={"model": "gpt-4", "session_id": "s-123"},
        warnings=["partial result"],
        duration_ms=1234,
        cost=0.05,
        token_count=512,
    )
    assert result.success is True
    assert result.output == {"status": "done", "files": ["a.py"]}
    assert result.duration_ms == 1234
    assert result.cost == pytest.approx(0.05)
    assert result.token_count == 512
    assert result.warnings == ["partial result"]


def test_execution_result_error_shape():
    result = _err(error_code="adapter_unavailable")
    assert result.success is False
    assert result.error is not None
    assert result.error.error_code == "adapter_unavailable"
    assert result.error.message == "error"
    assert result.output is None


def test_execution_result_serializes_to_json():
    result = _ok(output={"key": "val"}, cost=0.01)
    payload = result.model_dump(mode="json")
    assert payload["success"] is True
    assert payload["output"] == {"key": "val"}
    assert payload["cost"] == pytest.approx(0.01)
    assert "error" in payload  # field always present in dump


# ---------------------------------------------------------------------------
# 2. is_fallback_eligible() contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error_code",
    sorted(_FALLBACK_ELIGIBLE_ERROR_CODES),
)
def test_fallback_eligible_codes_are_recognized(error_code):
    """Every code in _FALLBACK_ELIGIBLE_ERROR_CODES triggers fallback."""
    result = _err(error_code=error_code)
    assert is_fallback_eligible(result) is True


@pytest.mark.parametrize(
    "error_code",
    [
        "execution_error",
        "validation_error",
        "unknown_tool",
        "policy_denied",
        "approval_required",
        "process_error",
        "domain_error",
        "",
        "unknown_code_xyz",
    ],
)
def test_non_fallback_codes_not_eligible(error_code):
    """Domain errors, policy decisions, and unknown codes do not trigger fallback."""
    result = _err(error_code=error_code)
    assert is_fallback_eligible(result) is False


def test_success_result_never_fallback_eligible():
    assert is_fallback_eligible(_ok()) is False


def test_error_result_with_none_error_not_eligible():
    """A result with success=False but no error object is not eligible."""
    result = ExecutionResult(agent_id="a", success=False)
    assert is_fallback_eligible(result) is False


# ---------------------------------------------------------------------------
# 3. StructuredError field contracts
# ---------------------------------------------------------------------------


def test_structured_error_requires_error_code_and_message():
    err = StructuredError(error_code="execution_error", message="something failed")
    assert err.error_code == "execution_error"
    assert err.message == "something failed"


def test_structured_error_code_alias():
    """error_code and code property return the same value."""
    err = StructuredError(error_code="adapter_unavailable", message="unreachable")
    assert err.code == err.error_code


def test_structured_error_accepts_string_code():
    """Non-enum strings are accepted as error_code (open extension point)."""
    err = StructuredError(error_code="custom_adapter_error", message="custom")
    assert err.error_code == "custom_adapter_error"


def test_structured_error_optional_fields_default_none():
    err = StructuredError(error_code="execution_error", message="fail")
    assert err.tool_name is None
    assert err.details == {}
    assert err.audit_ref is None
    assert err.warnings is None
    assert err.run_id is None
    assert err.correlation_id is None


def test_structured_error_rejects_extra_fields():
    with pytest.raises(Exception):
        StructuredError(error_code="x", message="y", unknown="bad")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 4. Per-adapter success/error output shape (monkeypatched network calls)
# ---------------------------------------------------------------------------


class _DummyHTTPResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyHTTPClient:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def __enter__(self) -> "_DummyHTTPClient":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def post(self, url: str, json: Any = None, headers: Any = None) -> _DummyHTTPResponse:
        return _DummyHTTPResponse(self.payload)


def test_openhands_adapter_success_result_shape(monkeypatch):
    from core.execution.adapters import OpenHandsExecutionAdapter

    dummy = _DummyHTTPClient(
        {
            "id": "conv-abc",
            "assistant_response": {"summary": "Done"},
            "usage": {"cost_usd": 0.03},
        }
    )
    monkeypatch.setattr("httpx.Client", lambda timeout: dummy)
    adapter = OpenHandsExecutionAdapter(timeout_seconds=1.0)
    descriptor = _make_descriptor(
        agent_id="openhands-1",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
    )

    result = adapter.execute({"task_type": "code_refactor", "description": "Refactor", "preferences": {}}, descriptor)

    # Contract: success result fields
    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.error is None
    assert result.agent_id == "openhands-1"
    assert result.cost is not None and result.cost >= 0.0
    assert result.output is not None


def test_openhands_adapter_error_result_shape(monkeypatch):
    import httpx

    from core.execution.adapters import OpenHandsExecutionAdapter

    monkeypatch.setattr(
        "httpx.Client",
        lambda timeout: (_ for _ in ()).throw(ConnectionError("network error")),
    )

    # Use a client that raises on enter
    class _ErrorClient:
        def __enter__(self):
            raise httpx.ConnectError("unreachable")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("httpx.Client", lambda timeout: _ErrorClient())
    adapter = OpenHandsExecutionAdapter(timeout_seconds=1.0)
    descriptor = _make_descriptor(
        agent_id="openhands-err",
        source_type=AgentSourceType.OPENHANDS,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
    )

    result = adapter.execute({"task_type": "code_refactor", "description": "Refactor", "preferences": {}}, descriptor)

    # Contract: error result fields
    assert isinstance(result, ExecutionResult)
    assert result.success is False
    assert result.error is not None
    assert isinstance(result.error.error_code, str)
    assert result.error.message  # non-empty


def test_adminbot_adapter_success_result_shape(monkeypatch):
    from core.execution.adapters import AdminBotExecutionAdapter

    monkeypatch.setattr(
        "services.core.execute_tool",
        lambda tool_name, payload=None, **kwargs: {"status": "ok", "data": {"uptime": 42}},
    )
    adapter = AdminBotExecutionAdapter()
    descriptor = _make_descriptor(
        agent_id="adminbot-1",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
    )

    result = adapter.execute({"task_type": "system_status"}, descriptor)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.error is None
    assert result.agent_id == "adminbot-1"
    assert result.output is not None


def test_adminbot_adapter_error_result_shape(monkeypatch):
    from core.execution.adapters import AdminBotExecutionAdapter
    from core.models.errors import CoreExecutionError

    def _raise(tool_name, payload=None, **kwargs):
        raise CoreExecutionError(
            StructuredError(error_code="execution_error", message="AdminBot unavailable")
        )

    monkeypatch.setattr("services.core.execute_tool", _raise)
    adapter = AdminBotExecutionAdapter()
    descriptor = _make_descriptor(
        agent_id="adminbot-err",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
    )

    result = adapter.execute({"task_type": "system_status"}, descriptor)

    assert isinstance(result, ExecutionResult)
    assert result.success is False
    assert result.error is not None


def test_flowise_adapter_success_result_shape(monkeypatch):
    from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter

    dummy = _DummyHTTPClient(
        {"text": "Analysis complete", "sessionId": "sess-1", "question": "analyze"}
    )
    monkeypatch.setattr("httpx.Client", lambda timeout: dummy)
    adapter = FlowiseExecutionAdapter(timeout_seconds=1.0)
    descriptor = AgentDescriptor(
        agent_id="flowise-1",
        display_name="Flowise Agent",
        source_type=AgentSourceType.FLOWISE,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["analysis"],
        metadata={"base_url": "http://localhost:3000", "chatflow_id": "cf-1"},
    )

    result = adapter.execute({"task_type": "analysis", "description": "Analyze this"}, descriptor)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.error is None
    assert result.output is not None


def test_n8n_adapter_success_result_shape(monkeypatch):
    from core.execution.adapters.n8n_adapter import N8NExecutionAdapter

    dummy = _DummyHTTPClient({"status": "success", "data": {"result": "workflow complete"}})
    monkeypatch.setattr("httpx.Client", lambda timeout: dummy)
    adapter = N8NExecutionAdapter(timeout_seconds=1.0)
    descriptor = AgentDescriptor(
        agent_id="n8n-1",
        display_name="N8N Workflow",
        source_type=AgentSourceType.N8N,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["workflow.execute"],
        metadata={"webhook_url": "http://localhost:5678/webhook/run-workflow"},
    )

    result = adapter.execute({"task_type": "workflow_automation", "description": "Run workflow"}, descriptor)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.error is None


# ---------------------------------------------------------------------------
# 5. Fallback-eligible error code exhaustiveness and stability
# ---------------------------------------------------------------------------


def test_fallback_eligible_codes_are_infrastructure_level():
    """The 3 canonical fallback codes represent infrastructure failures only."""
    expected = {"adapter_unavailable", "adapter_timeout", "adapter_transport_error"}
    assert _FALLBACK_ELIGIBLE_ERROR_CODES == expected


def test_fallback_eligible_set_is_frozen():
    """_FALLBACK_ELIGIBLE_ERROR_CODES must not be mutated at runtime."""
    assert isinstance(_FALLBACK_ELIGIBLE_ERROR_CODES, frozenset)


def test_execution_result_with_fallback_eligible_error_is_recognized():
    for code in _FALLBACK_ELIGIBLE_ERROR_CODES:
        result = _err(error_code=code)
        assert is_fallback_eligible(result), f"Expected fallback eligible for {code!r}"


# ---------------------------------------------------------------------------
# 6. ExecutionResult as canonical output snapshot fixture set
#
# These fixtures represent the canonical expected output shape per adapter type.
# They serve as reference snapshots: if the contract changes, update these.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agent_id,source_type,execution_kind,expected_meta_keys",
    [
        # AdminBot: system executor — no cost/token reporting
        pytest.param(
            "adminbot-agent",
            AgentSourceType.ADMINBOT,
            AgentExecutionKind.SYSTEM_EXECUTOR,
            [],
            id="adminbot_snapshot",
        ),
        # OpenHands: HTTP service — supports cost reporting
        pytest.param(
            "openhands-agent",
            AgentSourceType.OPENHANDS,
            AgentExecutionKind.HTTP_SERVICE,
            [],
            id="openhands_snapshot",
        ),
        # Flowise: HTTP service — supports cost reporting
        pytest.param(
            "flowise-agent",
            AgentSourceType.FLOWISE,
            AgentExecutionKind.HTTP_SERVICE,
            [],
            id="flowise_snapshot",
        ),
        # N8N: workflow engine — no direct cost reporting
        pytest.param(
            "n8n-agent",
            AgentSourceType.N8N,
            AgentExecutionKind.WORKFLOW_ENGINE,
            [],
            id="n8n_snapshot",
        ),
        # Codex: cloud agent — may report cost
        pytest.param(
            "codex-agent",
            AgentSourceType.CODEX,
            AgentExecutionKind.CLOUD_AGENT,
            [],
            id="codex_snapshot",
        ),
    ],
)
def test_execution_result_success_snapshot_invariants(
    agent_id, source_type, execution_kind, expected_meta_keys
):
    """A success snapshot for each adapter type satisfies all ExecutionResult invariants."""
    snapshot = ExecutionResult(
        agent_id=agent_id,
        success=True,
        output={"status": "completed", "adapter": agent_id},
        metadata={"source_type": source_type, "execution_kind": execution_kind},
        duration_ms=500,
    )
    # Core invariants
    assert snapshot.success is True
    assert snapshot.error is None
    assert snapshot.warnings == []
    assert is_fallback_eligible(snapshot) is False
    # Schema round-trip
    payload = snapshot.model_dump(mode="json")
    restored = ExecutionResult.model_validate(payload)
    assert restored.agent_id == snapshot.agent_id
    assert restored.success == snapshot.success
    assert restored.output == snapshot.output


@pytest.mark.parametrize(
    "error_code,eligible",
    [
        ("adapter_unavailable", True),
        ("adapter_timeout", True),
        ("adapter_transport_error", True),
        ("execution_error", False),
        ("validation_error", False),
        ("policy_denied", False),
    ],
)
def test_execution_result_error_snapshot_invariants(error_code, eligible):
    """An error snapshot satisfies fallback eligibility and error field contracts."""
    snapshot = ExecutionResult(
        agent_id="test-agent",
        success=False,
        error=StructuredError(
            error_code=error_code,
            message=f"Simulated {error_code}",
            details={"adapter": "test-adapter"},
        ),
    )
    assert snapshot.success is False
    assert snapshot.output is None
    assert snapshot.error.error_code == error_code
    assert is_fallback_eligible(snapshot) is eligible
    # Schema round-trip
    payload = snapshot.model_dump(mode="json")
    restored = ExecutionResult.model_validate(payload)
    assert restored.error is not None
    assert restored.error.error_code == error_code
