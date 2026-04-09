"""Execution adapter that wraps the existing AdminBot tool integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.decision.agent_descriptor import AgentDescriptor
from core.models.errors import CoreExecutionError, StructuredError

from .base import BaseExecutionAdapter, ExecutionResult


class AdminBotExecutionAdapter(BaseExecutionAdapter):
    """Use the hardened AdminBot tools as a system-executor adapter."""

    adapter_name = "adminbot"

    _TASK_TO_TOOL = {
        "system_status": "adminbot_system_status",
        "system_health": "adminbot_system_health",
        "service_status": "adminbot_service_status",
    }

    def execute(
        self,
        task,
        agent_descriptor: AgentDescriptor,
    ) -> ExecutionResult:
        from services.core import execute_tool

        self.validate(task, agent_descriptor)
        task_type = self.task_type(task)
        preferences = self.task_preferences(task)
        tool_name = self._TASK_TO_TOOL.get(task_type)
        if tool_name is None:
            raise ValueError(f"Unsupported AdminBot task_type: {task_type}")
        payload: dict[str, Any] = {}
        if tool_name == "adminbot_service_status":
            service_name = (
                preferences.get("service_name")
                or agent_descriptor.metadata.get("service_name")
            )
            if not isinstance(service_name, str) or not service_name.strip():
                raise ValueError("service_status requires a service_name")
            payload["service_name"] = service_name.strip()
        try:
            output = execute_tool(tool_name, payload)
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=True,
                output=output,
                raw_output=output,
                metadata={"tool_name": tool_name, "adapter": self.adapter_name},
            )
        except CoreExecutionError as exc:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                raw_output=None,
                error=exc.error,
                metadata={"tool_name": tool_name, "adapter": self.adapter_name},
            )

