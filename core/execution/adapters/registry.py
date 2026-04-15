"""Static execution-adapter registry."""

from __future__ import annotations

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.execution.provider_capabilities import ExecutionCapabilities
from core.execution.adapters.manifest import AdapterManifest

from .adminbot_adapter import AdminBotExecutionAdapter
from .base import BaseExecutionAdapter
from .claude_code_adapter import ClaudeCodeExecutionAdapter
from .codex_adapter import CodexExecutionAdapter
from .flowise_adapter import FlowiseExecutionAdapter
from .n8n_adapter import N8NExecutionAdapter
from .openhands_adapter import OpenHandsExecutionAdapter


class ExecutionAdapterRegistry:
    """Resolve adapters from a static execution-kind/source-type table."""

    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], BaseExecutionAdapter] = {
            (AgentExecutionKind.SYSTEM_EXECUTOR.value, AgentSourceType.ADMINBOT.value): AdminBotExecutionAdapter(),
            (AgentExecutionKind.HTTP_SERVICE.value, AgentSourceType.OPENHANDS.value): OpenHandsExecutionAdapter(),
            (AgentExecutionKind.LOCAL_PROCESS.value, AgentSourceType.OPENHANDS.value): OpenHandsExecutionAdapter(),
            (AgentExecutionKind.LOCAL_PROCESS.value, AgentSourceType.CLAUDE_CODE.value): ClaudeCodeExecutionAdapter(),
            (AgentExecutionKind.CLOUD_AGENT.value, AgentSourceType.CLAUDE_CODE.value): ClaudeCodeExecutionAdapter(),
            (AgentExecutionKind.LOCAL_PROCESS.value, AgentSourceType.CODEX.value): CodexExecutionAdapter(),
            (AgentExecutionKind.CLOUD_AGENT.value, AgentSourceType.CODEX.value): CodexExecutionAdapter(),
            (AgentExecutionKind.WORKFLOW_ENGINE.value, AgentSourceType.N8N.value): N8NExecutionAdapter(),
            (AgentExecutionKind.WORKFLOW_ENGINE.value, AgentSourceType.FLOWISE.value): FlowiseExecutionAdapter(),
        }

    def resolve(self, descriptor: AgentDescriptor) -> BaseExecutionAdapter:
        key = (descriptor.execution_kind.value, descriptor.source_type.value)
        adapter = self._adapters.get(key)
        if adapter is None:
            raise KeyError(
                f"No execution adapter for execution_kind={descriptor.execution_kind.value} "
                f"source_type={descriptor.source_type.value}"
            )
        return adapter

    def get_capabilities_for(
        self, execution_kind: str, source_type: str
    ) -> ExecutionCapabilities | None:
        """Return the static capabilities for a given (execution_kind, source_type) pair.

        Returns ``None`` when no adapter is registered for the combination.
        Both arguments are matched as string values (the ``.value`` of the enums).
        """
        adapter = self._adapters.get((execution_kind, source_type))
        if adapter is None:
            return None
        return getattr(adapter, "capabilities", None)

    def get_manifest_for(
        self, execution_kind: str, source_type: str
    ) -> AdapterManifest | None:
        """Return the governance manifest for a given (execution_kind, source_type) pair.

        Returns ``None`` when no adapter is registered for the combination.
        Both arguments are matched as string values (the ``.value`` of the enums).
        """
        adapter = self._adapters.get((execution_kind, source_type))
        if adapter is None:
            return None
        return getattr(adapter, "manifest", None)
