"""Tests for manifest-driven input validation (Phase 2 — S17).

Covers:
1. missing_metadata_keys() — pure helper function
2. validate_required_metadata() — raises ValueError on missing keys
3. BaseExecutionAdapter.validate() — manifest contract enforced via base class
4. Integration: concrete adapters reject descriptors with missing metadata
"""

from __future__ import annotations

import pytest

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.execution.adapters import (
    FlowiseExecutionAdapter,
    N8NExecutionAdapter,
    AdminBotExecutionAdapter,
    ClaudeCodeExecutionAdapter,
    CodexExecutionAdapter,
    OpenHandsExecutionAdapter,
    missing_metadata_keys,
    validate_required_metadata,
)
from core.execution.adapters.base import BaseExecutionAdapter
from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.provider_capabilities import ExecutionCapabilities

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _manifest(required: list[str], name: str = "test-adapter") -> AdapterManifest:
    return AdapterManifest(
        adapter_name=name,
        description="Test adapter.",
        capabilities=ExecutionCapabilities(
            execution_protocol="http_api",
            requires_network=True,
            requires_local_process=False,
            supports_cost_reporting=False,
            supports_token_reporting=False,
        ),
        risk_tier=RiskTier.LOW,
        required_metadata_keys=required,
    )


def _descriptor(metadata: dict | None = None, agent_id: str = "agent-1") -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        display_name="Test Agent",
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=["analysis"],
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 1. missing_metadata_keys() — pure function
# ---------------------------------------------------------------------------


def test_missing_metadata_keys_returns_empty_when_all_present():
    manifest = _manifest(["base_url", "api_key"])
    descriptor = _descriptor({"base_url": "http://example.com", "api_key": "secret"})
    assert missing_metadata_keys(manifest, descriptor) == []


def test_missing_metadata_keys_returns_absent_keys():
    manifest = _manifest(["base_url", "api_key"])
    descriptor = _descriptor({"base_url": "http://example.com"})
    missing = missing_metadata_keys(manifest, descriptor)
    assert missing == ["api_key"]


def test_missing_metadata_keys_all_absent():
    manifest = _manifest(["base_url", "api_key"])
    descriptor = _descriptor({})
    missing = missing_metadata_keys(manifest, descriptor)
    assert set(missing) == {"base_url", "api_key"}


def test_missing_metadata_keys_no_requirements_always_empty():
    manifest = _manifest([])
    descriptor = _descriptor({})
    assert missing_metadata_keys(manifest, descriptor) == []


def test_missing_metadata_keys_extra_metadata_not_flagged():
    manifest = _manifest(["base_url"])
    descriptor = _descriptor({"base_url": "http://x", "extra_key": "ignored"})
    assert missing_metadata_keys(manifest, descriptor) == []


def test_missing_metadata_keys_preserves_order():
    manifest = _manifest(["z_key", "a_key", "m_key"])
    descriptor = _descriptor({})
    missing = missing_metadata_keys(manifest, descriptor)
    assert missing == ["z_key", "a_key", "m_key"]


# ---------------------------------------------------------------------------
# 2. validate_required_metadata() — raises ValueError
# ---------------------------------------------------------------------------


def test_validate_required_metadata_passes_when_all_present():
    manifest = _manifest(["base_url"])
    descriptor = _descriptor({"base_url": "http://example.com"})
    validate_required_metadata(manifest, descriptor)  # must not raise


def test_validate_required_metadata_raises_on_missing_key():
    manifest = _manifest(["base_url", "api_key"], name="flowise-adapter")
    descriptor = _descriptor({"base_url": "http://example.com"}, agent_id="agent-42")
    with pytest.raises(ValueError) as exc_info:
        validate_required_metadata(manifest, descriptor)
    msg = str(exc_info.value)
    assert "flowise-adapter" in msg
    assert "agent-42" in msg
    assert "api_key" in msg


def test_validate_required_metadata_error_names_adapter_and_agent():
    manifest = _manifest(["webhook_url"], name="n8n-adapter")
    descriptor = _descriptor({}, agent_id="wf-agent-7")
    with pytest.raises(ValueError) as exc_info:
        validate_required_metadata(manifest, descriptor)
    msg = str(exc_info.value)
    assert "n8n-adapter" in msg
    assert "wf-agent-7" in msg


def test_validate_required_metadata_no_requirements_never_raises():
    manifest = _manifest([])
    descriptor = _descriptor({})
    validate_required_metadata(manifest, descriptor)  # must not raise


# ---------------------------------------------------------------------------
# 3. BaseExecutionAdapter.validate() — manifest enforcement in base class
# ---------------------------------------------------------------------------


class _ConcreteAdapter(BaseExecutionAdapter):
    """Minimal concrete adapter for testing base.validate() delegation."""
    adapter_name = "concrete-test"
    manifest = _manifest(["required_key"], name="concrete-test")

    def execute(self, task, agent_descriptor):
        raise NotImplementedError


def test_base_adapter_validate_passes_with_required_key():
    adapter = _ConcreteAdapter()
    descriptor = _descriptor({"required_key": "present"})
    adapter.validate({}, descriptor)  # must not raise


def test_base_adapter_validate_raises_on_missing_required_key():
    adapter = _ConcreteAdapter()
    descriptor = _descriptor({})
    with pytest.raises(ValueError) as exc_info:
        adapter.validate({}, descriptor)
    assert "required_key" in str(exc_info.value)


def test_base_adapter_validate_raises_valueerror_not_other():
    """Callers see a uniform ValueError — not a custom exception class."""
    adapter = _ConcreteAdapter()
    descriptor = _descriptor({})
    with pytest.raises(ValueError):
        adapter.validate({"task": "whatever"}, descriptor)


def test_base_adapter_validate_task_arg_is_ignored_in_base():
    """Base validate() does not inspect the task payload — only manifest vs descriptor."""
    adapter = _ConcreteAdapter()
    descriptor = _descriptor({"required_key": "ok"})
    # Any task shape should not influence the metadata check
    for task in [{}, {"task": "x"}, {"some_field": 99}]:
        adapter.validate(task, descriptor)  # must not raise for any task shape


# ---------------------------------------------------------------------------
# 4. Integration: concrete adapters reject descriptors with missing metadata
# ---------------------------------------------------------------------------


def test_flowise_validate_raises_without_base_url(monkeypatch):
    adapter = FlowiseExecutionAdapter()
    descriptor = AgentDescriptor(
        agent_id="flowise-missing",
        display_name="Flowise No URL",
        source_type=AgentSourceType.FLOWISE,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["analysis"],
        metadata={"chatflow_id": "cf-1"},  # base_url missing
    )
    with pytest.raises(ValueError) as exc_info:
        adapter.validate({}, descriptor)
    assert "base_url" in str(exc_info.value)


def test_flowise_validate_passes_with_both_required_keys():
    adapter = FlowiseExecutionAdapter()
    descriptor = AgentDescriptor(
        agent_id="flowise-ok",
        display_name="Flowise OK",
        source_type=AgentSourceType.FLOWISE,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["analysis"],
        metadata={"base_url": "http://localhost:3000", "chatflow_id": "cf-1"},
    )
    # Flowise also requires non-empty task text and valid source_type — supply both.
    adapter.validate({"description": "Analyse logs"}, descriptor)  # must not raise


def test_n8n_validate_raises_without_webhook_url():
    adapter = N8NExecutionAdapter()
    descriptor = AgentDescriptor(
        agent_id="n8n-missing",
        display_name="N8N No Webhook",
        source_type=AgentSourceType.N8N,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["workflow.execute"],
        metadata={},
    )
    with pytest.raises(ValueError) as exc_info:
        adapter.validate({"description": "Run workflow"}, descriptor)
    assert "webhook_url" in str(exc_info.value)


def test_n8n_validate_passes_with_webhook_url():
    adapter = N8NExecutionAdapter()
    descriptor = AgentDescriptor(
        agent_id="n8n-ok",
        display_name="N8N OK",
        source_type=AgentSourceType.N8N,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=["workflow.execute"],
        metadata={"webhook_url": "http://localhost:5678/webhook/run"},
    )
    # N8N also requires non-empty task text and valid source_type — supply both.
    adapter.validate({"description": "Run workflow"}, descriptor)  # must not raise


def test_adminbot_validate_passes_with_empty_metadata():
    """AdminBot requires no metadata — validate() always succeeds on metadata grounds."""
    adapter = AdminBotExecutionAdapter()
    assert adapter.manifest.required_metadata_keys == []
    descriptor = AgentDescriptor(
        agent_id="adminbot-ok",
        display_name="AdminBot",
        source_type=AgentSourceType.ADMINBOT,
        execution_kind=AgentExecutionKind.SYSTEM_EXECUTOR,
        capabilities=["system.read"],
        metadata={},
    )
    adapter.validate({}, descriptor)  # must not raise
