"""S15 — Adapter manifest contracts.

Phase 2, Step 1: Plugin-/Adapter-Manifest spezifizieren + Risk-Tiering.

These tests verify:
1. AdapterManifest model field constraints and defaults
2. RiskTier enum exhaustiveness and values
3. Per-adapter manifest presence and correctness
4. ExecutionAdapterRegistry.get_manifest_for() lookup
5. Manifest–capabilities consistency (manifest.capabilities == adapter.capabilities)
6. Required metadata keys accuracy (match actual adapter validate() requirements)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.adapters.base import BaseExecutionAdapter
from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
from core.execution.adapters.codex_adapter import CodexExecutionAdapter
from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
from core.execution.adapters.n8n_adapter import N8NExecutionAdapter
from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
from core.execution.adapters.registry import ExecutionAdapterRegistry
from core.execution.provider_capabilities import ExecutionCapabilities


# ---------------------------------------------------------------------------
# Section 1: AdapterManifest model field constraints
# ---------------------------------------------------------------------------


def test_manifest_required_fields():
    """adapter_name, description, capabilities, and risk_tier are required."""
    caps = ExecutionCapabilities(
        execution_protocol="http_api",
        requires_network=False,
        requires_local_process=False,
        supports_cost_reporting=False,
        supports_token_reporting=False,
    )
    manifest = AdapterManifest(
        adapter_name="test",
        description="A test adapter.",
        capabilities=caps,
        risk_tier=RiskTier.LOW,
    )
    assert manifest.adapter_name == "test"
    assert manifest.description == "A test adapter."
    assert manifest.capabilities is caps
    assert manifest.risk_tier == RiskTier.LOW


def test_manifest_optional_fields_default():
    """optional fields default to empty list / None."""
    caps = ExecutionCapabilities(
        execution_protocol="http_api",
        requires_network=False,
        requires_local_process=False,
        supports_cost_reporting=False,
        supports_token_reporting=False,
    )
    manifest = AdapterManifest(
        adapter_name="test",
        description="desc",
        capabilities=caps,
        risk_tier=RiskTier.LOW,
    )
    assert manifest.required_metadata_keys == []
    assert manifest.optional_metadata_keys == []
    assert manifest.recommended_policy_scope is None


def test_manifest_full_population():
    """All fields can be set."""
    caps = ExecutionCapabilities(
        execution_protocol="cli_process",
        requires_network=False,
        requires_local_process=True,
        supports_cost_reporting=True,
        supports_token_reporting=True,
    )
    manifest = AdapterManifest(
        adapter_name="my_adapter",
        description="Does things.",
        capabilities=caps,
        risk_tier=RiskTier.HIGH,
        required_metadata_keys=["base_url"],
        optional_metadata_keys=["api_key", "timeout"],
        recommended_policy_scope="code_execution",
    )
    assert manifest.required_metadata_keys == ["base_url"]
    assert manifest.optional_metadata_keys == ["api_key", "timeout"]
    assert manifest.recommended_policy_scope == "code_execution"


def test_manifest_extra_fields_forbidden():
    """extra='forbid' rejects unknown fields."""
    caps = ExecutionCapabilities(
        execution_protocol="http_api",
        requires_network=False,
        requires_local_process=False,
        supports_cost_reporting=False,
        supports_token_reporting=False,
    )
    with pytest.raises(ValidationError):
        AdapterManifest(
            adapter_name="test",
            description="desc",
            capabilities=caps,
            risk_tier=RiskTier.LOW,
            unknown_field="value",  # type: ignore[call-arg]
        )


def test_manifest_missing_required_field_raises():
    """Omitting a required field raises ValidationError."""
    caps = ExecutionCapabilities(
        execution_protocol="http_api",
        requires_network=False,
        requires_local_process=False,
        supports_cost_reporting=False,
        supports_token_reporting=False,
    )
    with pytest.raises(ValidationError):
        AdapterManifest(  # type: ignore[call-arg]
            description="desc",
            capabilities=caps,
            risk_tier=RiskTier.LOW,
        )


def test_manifest_json_round_trip():
    """AdapterManifest survives a JSON serialization round-trip."""
    caps = ExecutionCapabilities(
        execution_protocol="webhook_json",
        requires_network=True,
        requires_local_process=False,
        supports_cost_reporting=False,
        supports_token_reporting=False,
    )
    original = AdapterManifest(
        adapter_name="roundtrip",
        description="round trip test",
        capabilities=caps,
        risk_tier=RiskTier.MEDIUM,
        required_metadata_keys=["webhook_url"],
        optional_metadata_keys=["api_key"],
        recommended_policy_scope="workflow_execution",
    )
    data = original.model_dump()
    restored = AdapterManifest.model_validate(data)
    assert restored == original


# ---------------------------------------------------------------------------
# Section 2: RiskTier enum
# ---------------------------------------------------------------------------


def test_risk_tier_values():
    """RiskTier has exactly the three expected string values."""
    assert RiskTier.LOW == "low"
    assert RiskTier.MEDIUM == "medium"
    assert RiskTier.HIGH == "high"


def test_risk_tier_exhaustive():
    """RiskTier contains exactly {low, medium, high} — no more, no less."""
    values = {t.value for t in RiskTier}
    assert values == {"low", "medium", "high"}


def test_risk_tier_ordering_semantics():
    """LOW < MEDIUM < HIGH in terms of string comparison is irrelevant;
    the enum covers all three tiers needed for governance classification."""
    tiers = list(RiskTier)
    assert RiskTier.LOW in tiers
    assert RiskTier.MEDIUM in tiers
    assert RiskTier.HIGH in tiers


# ---------------------------------------------------------------------------
# Section 3: BaseExecutionAdapter default manifest
# ---------------------------------------------------------------------------


def test_base_adapter_has_manifest():
    """BaseExecutionAdapter defines a manifest class attribute."""
    assert hasattr(BaseExecutionAdapter, "manifest")
    assert isinstance(BaseExecutionAdapter.manifest, AdapterManifest)


def test_base_adapter_manifest_name():
    """Base manifest has adapter_name='base'."""
    assert BaseExecutionAdapter.manifest.adapter_name == "base"


def test_base_adapter_manifest_non_empty_description():
    """Base manifest description is not empty."""
    assert BaseExecutionAdapter.manifest.description.strip()


# ---------------------------------------------------------------------------
# Section 4: Per-adapter manifest presence and correctness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_cls,expected_name,expected_tier,expected_scope", [
    (AdminBotExecutionAdapter,  "adminbot",     RiskTier.LOW,    "system_ops"),
    (OpenHandsExecutionAdapter, "openhands",    RiskTier.HIGH,   "code_execution"),
    (ClaudeCodeExecutionAdapter,"claude_code",  RiskTier.HIGH,   "code_execution"),
    (CodexExecutionAdapter,     "codex",        RiskTier.HIGH,   "code_execution"),
    (FlowiseExecutionAdapter,   "flowise",      RiskTier.MEDIUM, "workflow_execution"),
    (N8NExecutionAdapter,       "n8n",          RiskTier.MEDIUM, "workflow_execution"),
])
def test_adapter_manifest_name_tier_scope(adapter_cls, expected_name, expected_tier, expected_scope):
    """Each concrete adapter has the correct name, risk tier, and policy scope."""
    manifest = adapter_cls.manifest
    assert isinstance(manifest, AdapterManifest)
    assert manifest.adapter_name == expected_name
    assert manifest.risk_tier == expected_tier
    assert manifest.recommended_policy_scope == expected_scope


@pytest.mark.parametrize("adapter_cls", [
    AdminBotExecutionAdapter,
    OpenHandsExecutionAdapter,
    ClaudeCodeExecutionAdapter,
    CodexExecutionAdapter,
    FlowiseExecutionAdapter,
    N8NExecutionAdapter,
])
def test_adapter_manifest_non_empty_description(adapter_cls):
    """Every concrete adapter manifest has a non-empty description."""
    assert adapter_cls.manifest.description.strip()


@pytest.mark.parametrize("adapter_cls", [
    AdminBotExecutionAdapter,
    OpenHandsExecutionAdapter,
    ClaudeCodeExecutionAdapter,
    CodexExecutionAdapter,
    FlowiseExecutionAdapter,
    N8NExecutionAdapter,
])
def test_adapter_manifest_capabilities_consistent(adapter_cls):
    """manifest.capabilities matches the adapter's standalone capabilities attribute."""
    assert adapter_cls.manifest.capabilities == adapter_cls.capabilities


# ---------------------------------------------------------------------------
# Section 5: Required metadata keys accuracy
# ---------------------------------------------------------------------------


def test_flowise_required_metadata_keys():
    """Flowise manifest declares base_url and chatflow_id as required."""
    required = FlowiseExecutionAdapter.manifest.required_metadata_keys
    assert "base_url" in required
    assert "chatflow_id" in required


def test_n8n_required_metadata_keys():
    """n8n manifest declares webhook_url as required."""
    required = N8NExecutionAdapter.manifest.required_metadata_keys
    assert "webhook_url" in required


def test_adminbot_no_required_keys():
    """AdminBot manifest has no required metadata keys (tool dispatch, internal)."""
    assert AdminBotExecutionAdapter.manifest.required_metadata_keys == []


def test_claude_code_no_required_keys():
    """ClaudeCode manifest has no required keys (defaults to 'claude' CLI)."""
    assert ClaudeCodeExecutionAdapter.manifest.required_metadata_keys == []


def test_codex_no_required_keys():
    """Codex manifest has no required keys (defaults to 'codex' CLI)."""
    assert CodexExecutionAdapter.manifest.required_metadata_keys == []


def test_openhands_no_required_keys():
    """OpenHands manifest has no required keys (defaults to localhost:3000)."""
    assert OpenHandsExecutionAdapter.manifest.required_metadata_keys == []


def test_flowise_optional_keys_include_prediction_url():
    """Flowise manifest lists prediction_url as an alternative (optional) key."""
    assert "prediction_url" in FlowiseExecutionAdapter.manifest.optional_metadata_keys


def test_n8n_optional_keys_include_base_url_and_webhook_path():
    """n8n manifest lists base_url+webhook_path as alternative optional keys."""
    optional = N8NExecutionAdapter.manifest.optional_metadata_keys
    assert "base_url" in optional
    assert "webhook_path" in optional


# ---------------------------------------------------------------------------
# Section 6: ExecutionAdapterRegistry.get_manifest_for()
# ---------------------------------------------------------------------------


def test_registry_get_manifest_adminbot():
    """Registry resolves the AdminBot manifest by execution_kind+source_type."""
    registry = ExecutionAdapterRegistry()
    manifest = registry.get_manifest_for("system_executor", "adminbot")
    assert manifest is not None
    assert manifest.adapter_name == "adminbot"
    assert manifest.risk_tier == RiskTier.LOW


def test_registry_get_manifest_openhands_http():
    """Registry resolves OpenHands manifest for http_service+openhands."""
    registry = ExecutionAdapterRegistry()
    manifest = registry.get_manifest_for("http_service", "openhands")
    assert manifest is not None
    assert manifest.adapter_name == "openhands"
    assert manifest.risk_tier == RiskTier.HIGH


def test_registry_get_manifest_claude_code():
    """Registry resolves ClaudeCode manifest for local_process+claude_code."""
    registry = ExecutionAdapterRegistry()
    manifest = registry.get_manifest_for("local_process", "claude_code")
    assert manifest is not None
    assert manifest.adapter_name == "claude_code"
    assert manifest.risk_tier == RiskTier.HIGH


def test_registry_get_manifest_codex():
    """Registry resolves Codex manifest for local_process+codex."""
    registry = ExecutionAdapterRegistry()
    manifest = registry.get_manifest_for("local_process", "codex")
    assert manifest is not None
    assert manifest.adapter_name == "codex"
    assert manifest.risk_tier == RiskTier.HIGH


def test_registry_get_manifest_flowise():
    """Registry resolves Flowise manifest for workflow_engine+flowise."""
    registry = ExecutionAdapterRegistry()
    manifest = registry.get_manifest_for("workflow_engine", "flowise")
    assert manifest is not None
    assert manifest.adapter_name == "flowise"
    assert manifest.risk_tier == RiskTier.MEDIUM


def test_registry_get_manifest_n8n():
    """Registry resolves n8n manifest for workflow_engine+n8n."""
    registry = ExecutionAdapterRegistry()
    manifest = registry.get_manifest_for("workflow_engine", "n8n")
    assert manifest is not None
    assert manifest.adapter_name == "n8n"
    assert manifest.risk_tier == RiskTier.MEDIUM


def test_registry_get_manifest_unknown_returns_none():
    """Registry returns None for an unregistered (execution_kind, source_type) pair."""
    registry = ExecutionAdapterRegistry()
    assert registry.get_manifest_for("unknown_kind", "unknown_source") is None


# ---------------------------------------------------------------------------
# Section 7: Risk-tier distribution invariants
# ---------------------------------------------------------------------------


def test_code_execution_adapters_are_high_risk():
    """All code-execution adapters (ClaudeCode, Codex, OpenHands) are HIGH risk."""
    for cls in (ClaudeCodeExecutionAdapter, CodexExecutionAdapter, OpenHandsExecutionAdapter):
        assert cls.manifest.risk_tier == RiskTier.HIGH, f"{cls.adapter_name} should be HIGH"


def test_workflow_engine_adapters_are_medium_risk():
    """Workflow-engine adapters (Flowise, n8n) are MEDIUM risk."""
    for cls in (FlowiseExecutionAdapter, N8NExecutionAdapter):
        assert cls.manifest.risk_tier == RiskTier.MEDIUM, f"{cls.adapter_name} should be MEDIUM"


def test_internal_tool_dispatch_adapter_is_low_risk():
    """AdminBot (tool dispatch, no network) is LOW risk."""
    assert AdminBotExecutionAdapter.manifest.risk_tier == RiskTier.LOW


def test_all_adapters_have_policy_scope():
    """Every concrete adapter has a non-None recommended_policy_scope."""
    for cls in (
        AdminBotExecutionAdapter,
        OpenHandsExecutionAdapter,
        ClaudeCodeExecutionAdapter,
        CodexExecutionAdapter,
        FlowiseExecutionAdapter,
        N8NExecutionAdapter,
    ):
        assert cls.manifest.recommended_policy_scope is not None, (
            f"{cls.adapter_name} missing recommended_policy_scope"
        )


def test_policy_scope_values_are_known():
    """Policy scopes across all adapters are drawn from the three expected values."""
    known_scopes = {"system_ops", "code_execution", "workflow_execution"}
    for cls in (
        AdminBotExecutionAdapter,
        OpenHandsExecutionAdapter,
        ClaudeCodeExecutionAdapter,
        CodexExecutionAdapter,
        FlowiseExecutionAdapter,
        N8NExecutionAdapter,
    ):
        assert cls.manifest.recommended_policy_scope in known_scopes, (
            f"{cls.adapter_name} has unexpected scope: {cls.manifest.recommended_policy_scope}"
        )
