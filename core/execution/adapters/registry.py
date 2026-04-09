"""Static execution-adapter registry."""

from __future__ import annotations

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType

from .adminbot_adapter import AdminBotExecutionAdapter
from .base import BaseExecutionAdapter
from .claude_code_adapter import ClaudeCodeExecutionAdapter
from .codex_adapter import CodexExecutionAdapter
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
