"""Execution helpers for the stabilized core layer."""

from .dispatcher import ExecutionDispatcher, maybe_await, run_sync

__all__ = [
    "AdminBotExecutionAdapter",
    "BaseExecutionAdapter",
    "ClaudeCodeExecutionAdapter",
    "CodexExecutionAdapter",
    "ExecutionAdapterRegistry",
    "ExecutionCapabilities",
    "ExecutionDispatcher",
    "ExecutionEngine",
    "ExecutionResult",
    "OpenHandsExecutionAdapter",
    "maybe_await",
    "run_sync",
]


def __getattr__(name: str):
    if name == "ExecutionEngine":
        from .execution_engine import ExecutionEngine

        return ExecutionEngine
    if name in {
        "AdminBotExecutionAdapter",
        "BaseExecutionAdapter",
        "ClaudeCodeExecutionAdapter",
        "CodexExecutionAdapter",
        "ExecutionAdapterRegistry",
        "OpenHandsExecutionAdapter",
    }:
        from .adapters import (
            AdminBotExecutionAdapter,
            BaseExecutionAdapter,
            ClaudeCodeExecutionAdapter,
            CodexExecutionAdapter,
            ExecutionAdapterRegistry,
            OpenHandsExecutionAdapter,
        )

        return {
            "AdminBotExecutionAdapter": AdminBotExecutionAdapter,
            "BaseExecutionAdapter": BaseExecutionAdapter,
            "ClaudeCodeExecutionAdapter": ClaudeCodeExecutionAdapter,
            "CodexExecutionAdapter": CodexExecutionAdapter,
            "ExecutionAdapterRegistry": ExecutionAdapterRegistry,
            "OpenHandsExecutionAdapter": OpenHandsExecutionAdapter,
        }[name]
    if name == "ExecutionResult":
        from .adapters.base import ExecutionResult

        return ExecutionResult
    if name == "ExecutionCapabilities":
        from .provider_capabilities import ExecutionCapabilities

        return ExecutionCapabilities
    raise AttributeError(name)
