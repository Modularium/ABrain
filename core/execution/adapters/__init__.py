"""Execution adapters for the canonical execution layer."""

from .adminbot_adapter import AdminBotExecutionAdapter
from .base import BaseExecutionAdapter
from .claude_code_adapter import ClaudeCodeExecutionAdapter
from .codex_adapter import CodexExecutionAdapter
from .flowise_adapter import FlowiseExecutionAdapter
from .manifest import AdapterManifest, RiskTier
from .n8n_adapter import N8NExecutionAdapter
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
]
