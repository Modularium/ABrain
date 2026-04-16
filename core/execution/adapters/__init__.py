"""Execution adapters for the canonical execution layer."""

from .adminbot_adapter import AdminBotExecutionAdapter
from .base import BaseExecutionAdapter
from .claude_code_adapter import ClaudeCodeExecutionAdapter
from .codex_adapter import CodexExecutionAdapter
from .flowise_adapter import FlowiseExecutionAdapter
from .manifest import AdapterManifest, RiskTier
from .n8n_adapter import N8NExecutionAdapter
from .policy_bindings import build_default_rules_for_manifest, get_all_adapter_default_rules
from .validation import (
    missing_metadata_keys,
    missing_result_metadata_keys,
    result_warnings,
    validate_required_metadata,
    validate_result,
)
from .openhands_adapter import OpenHandsExecutionAdapter
from .registry import ExecutionAdapterRegistry

__all__ = [
    "AdapterManifest",
    "AdminBotExecutionAdapter",
    "BaseExecutionAdapter",
    "ClaudeCodeExecutionAdapter",
    "CodexExecutionAdapter",
    "ExecutionAdapterRegistry",
    "FlowiseExecutionAdapter",
    "N8NExecutionAdapter",
    "OpenHandsExecutionAdapter",
    "RiskTier",
    "build_default_rules_for_manifest",
    "get_all_adapter_default_rules",
    "missing_metadata_keys",
    "missing_result_metadata_keys",
    "result_warnings",
    "validate_required_metadata",
    "validate_result",
]
