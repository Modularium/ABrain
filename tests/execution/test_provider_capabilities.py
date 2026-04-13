"""Tests for the canonical execution capability surface (S9).

Covers:
- ExecutionCapabilities model validation
- Per-adapter capabilities class attribute correctness
- ExecutionAdapterRegistry.get_capabilities_for() lookup
"""

import pytest
from pydantic import ValidationError

from core.decision import AgentExecutionKind, AgentSourceType
from core.execution.adapters.adminbot_adapter import AdminBotExecutionAdapter
from core.execution.adapters.base import BaseExecutionAdapter
from core.execution.adapters.claude_code_adapter import ClaudeCodeExecutionAdapter
from core.execution.adapters.codex_adapter import CodexExecutionAdapter
from core.execution.adapters.flowise_adapter import FlowiseExecutionAdapter
from core.execution.adapters.n8n_adapter import N8NExecutionAdapter
from core.execution.adapters.openhands_adapter import OpenHandsExecutionAdapter
from core.execution.adapters.registry import ExecutionAdapterRegistry
from core.execution.provider_capabilities import ExecutionCapabilities

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ExecutionCapabilities model validation
# ---------------------------------------------------------------------------


def test_execution_capabilities_valid_minimal():
    caps = ExecutionCapabilities(
        execution_protocol="cli_process",
        requires_network=False,
        requires_local_process=True,
        supports_cost_reporting=False,
        supports_token_reporting=False,
    )
    assert caps.execution_protocol == "cli_process"
    assert caps.runtime_constraints == []


def test_execution_capabilities_all_protocols_accepted():
    for proto in ("cli_process", "http_api", "webhook_json", "tool_dispatch"):
        caps = ExecutionCapabilities(
            execution_protocol=proto,
            requires_network=False,
            requires_local_process=False,
            supports_cost_reporting=False,
            supports_token_reporting=False,
        )
        assert caps.execution_protocol == proto


def test_execution_capabilities_invalid_protocol_rejected():
    with pytest.raises(ValidationError):
        ExecutionCapabilities(
            execution_protocol="rpc_socket",
            requires_network=False,
            requires_local_process=False,
            supports_cost_reporting=False,
            supports_token_reporting=False,
        )


def test_execution_capabilities_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        ExecutionCapabilities(
            execution_protocol="http_api",
            requires_network=True,
            requires_local_process=False,
            supports_cost_reporting=False,
            supports_token_reporting=False,
            undocumented_flag=True,
        )


def test_execution_capabilities_runtime_constraints_list():
    caps = ExecutionCapabilities(
        execution_protocol="http_api",
        requires_network=True,
        requires_local_process=False,
        supports_cost_reporting=False,
        supports_token_reporting=False,
        runtime_constraints=["requires_service_endpoint"],
    )
    assert caps.runtime_constraints == ["requires_service_endpoint"]


def test_execution_capabilities_model_dump_json_serialisable():
    caps = ExecutionCapabilities(
        execution_protocol="cli_process",
        requires_network=False,
        requires_local_process=True,
        supports_cost_reporting=True,
        supports_token_reporting=True,
        runtime_constraints=["requires_claude_cli"],
    )
    dumped = caps.model_dump(mode="json")
    assert dumped["execution_protocol"] == "cli_process"
    assert dumped["requires_local_process"] is True
    assert dumped["runtime_constraints"] == ["requires_claude_cli"]


# ---------------------------------------------------------------------------
# Per-adapter capabilities class attribute correctness
# ---------------------------------------------------------------------------


def test_base_adapter_has_default_capabilities():
    assert isinstance(BaseExecutionAdapter.capabilities, ExecutionCapabilities)


def test_adminbot_adapter_is_tool_dispatch():
    caps = AdminBotExecutionAdapter.capabilities
    assert caps.execution_protocol == "tool_dispatch"
    assert caps.requires_network is False
    assert caps.requires_local_process is False
    assert caps.supports_cost_reporting is False
    assert caps.supports_token_reporting is False
    assert "requires_adminbot_tools" in caps.runtime_constraints


def test_openhands_adapter_is_http_api_with_network():
    caps = OpenHandsExecutionAdapter.capabilities
    assert caps.execution_protocol == "http_api"
    assert caps.requires_network is True
    assert caps.requires_local_process is False
    assert caps.supports_cost_reporting is True
    assert "requires_service_endpoint" in caps.runtime_constraints


def test_claude_code_adapter_is_cli_process():
    caps = ClaudeCodeExecutionAdapter.capabilities
    assert caps.execution_protocol == "cli_process"
    assert caps.requires_network is False
    assert caps.requires_local_process is True
    assert caps.supports_cost_reporting is True
    assert caps.supports_token_reporting is True
    assert "requires_claude_cli" in caps.runtime_constraints


def test_codex_adapter_is_cli_process():
    caps = CodexExecutionAdapter.capabilities
    assert caps.execution_protocol == "cli_process"
    assert caps.requires_network is False
    assert caps.requires_local_process is True
    assert caps.supports_cost_reporting is True
    assert caps.supports_token_reporting is True
    assert "requires_codex_cli" in caps.runtime_constraints


def test_flowise_adapter_is_http_api_with_chatflow_constraint():
    caps = FlowiseExecutionAdapter.capabilities
    assert caps.execution_protocol == "http_api"
    assert caps.requires_network is True
    assert caps.requires_local_process is False
    assert caps.supports_cost_reporting is True
    assert "requires_service_endpoint" in caps.runtime_constraints
    assert "requires_chatflow_id" in caps.runtime_constraints


def test_n8n_adapter_is_webhook_json():
    caps = N8NExecutionAdapter.capabilities
    assert caps.execution_protocol == "webhook_json"
    assert caps.requires_network is True
    assert caps.requires_local_process is False
    assert caps.supports_cost_reporting is True
    assert "requires_webhook_url" in caps.runtime_constraints


# ---------------------------------------------------------------------------
# ExecutionAdapterRegistry.get_capabilities_for()
# ---------------------------------------------------------------------------


def test_registry_returns_capabilities_for_adminbot():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.SYSTEM_EXECUTOR.value,
        AgentSourceType.ADMINBOT.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "tool_dispatch"


def test_registry_returns_capabilities_for_claude_code_local():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.LOCAL_PROCESS.value,
        AgentSourceType.CLAUDE_CODE.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "cli_process"
    assert caps.requires_local_process is True


def test_registry_returns_capabilities_for_claude_code_cloud():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.CLOUD_AGENT.value,
        AgentSourceType.CLAUDE_CODE.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "cli_process"


def test_registry_returns_capabilities_for_codex_local():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.LOCAL_PROCESS.value,
        AgentSourceType.CODEX.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "cli_process"
    assert "requires_codex_cli" in caps.runtime_constraints


def test_registry_returns_capabilities_for_n8n():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.WORKFLOW_ENGINE.value,
        AgentSourceType.N8N.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "webhook_json"


def test_registry_returns_capabilities_for_flowise():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.WORKFLOW_ENGINE.value,
        AgentSourceType.FLOWISE.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "http_api"
    assert "requires_chatflow_id" in caps.runtime_constraints


def test_registry_returns_capabilities_for_openhands_http():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.HTTP_SERVICE.value,
        AgentSourceType.OPENHANDS.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "http_api"
    assert caps.requires_network is True


def test_registry_returns_capabilities_for_openhands_local():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for(
        AgentExecutionKind.LOCAL_PROCESS.value,
        AgentSourceType.OPENHANDS.value,
    )
    assert caps is not None
    assert caps.execution_protocol == "http_api"


def test_registry_returns_none_for_unknown_pair():
    registry = ExecutionAdapterRegistry()
    caps = registry.get_capabilities_for("nonexistent_kind", "nonexistent_source")
    assert caps is None


def test_registry_returns_none_for_empty_strings():
    registry = ExecutionAdapterRegistry()
    assert registry.get_capabilities_for("", "") is None


def test_registry_get_capabilities_does_not_raise_for_unknown():
    """get_capabilities_for must not raise — it returns None silently."""
    registry = ExecutionAdapterRegistry()
    try:
        result = registry.get_capabilities_for("bogus", "bogus")
    except Exception as exc:
        pytest.fail(f"get_capabilities_for raised unexpectedly: {exc}")
    assert result is None


def test_all_registered_pairs_have_capabilities():
    """Every adapter registered in the registry must declare capabilities."""
    registry = ExecutionAdapterRegistry()
    for (ek, st), adapter in registry._adapters.items():
        caps = registry.get_capabilities_for(ek, st)
        assert caps is not None, f"No capabilities for ({ek}, {st})"
        assert isinstance(caps, ExecutionCapabilities)
