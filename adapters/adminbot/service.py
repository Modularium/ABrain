"""Strict AdminBot service mapping for fixed tool handlers."""

from __future__ import annotations

from dataclasses import dataclass

from .client import AdminBotClient, AdminBotClientConfig
from core.models.adminbot import (
    AdminBotAction,
    AdminBotRequestEnvelope,
    AdminBotRequestedBy,
    AdminBotServiceStatusInput,
    AdminBotSystemHealthInput,
    AdminBotSystemStatusInput,
    AdminBotToolName,
)
from core.models.tooling import ToolExecutionRequest


@dataclass
class AdminBotService:
    """Map fixed tool handlers to fixed AdminBot IPC actions."""

    client: AdminBotClient

    @classmethod
    def from_config(
        cls, config: AdminBotClientConfig | None = None
    ) -> "AdminBotService":
        """Build the service from static adapter config."""
        return cls(client=AdminBotClient(config or AdminBotClientConfig()))

    def system_status(
        self,
        tool_request: ToolExecutionRequest,
        payload: AdminBotSystemStatusInput,
    ) -> dict[str, object]:
        """Map ``adminbot_system_status`` to ``system.status``."""
        envelope = self._build_envelope(
            action="system.status",
            tool_name="adminbot_system_status",
            tool_request=tool_request,
            params={},
        )
        return self.client.send_request(envelope)

    def system_health(
        self,
        tool_request: ToolExecutionRequest,
        payload: AdminBotSystemHealthInput,
    ) -> dict[str, object]:
        """Map ``adminbot_system_health`` to ``system.health``."""
        envelope = self._build_envelope(
            action="system.health",
            tool_name="adminbot_system_health",
            tool_request=tool_request,
            params={},
        )
        return self.client.send_request(envelope)

    def service_status(
        self,
        tool_request: ToolExecutionRequest,
        payload: AdminBotServiceStatusInput,
    ) -> dict[str, object]:
        """Map ``adminbot_service_status`` to ``service.status``."""
        envelope = self._build_envelope(
            action="service.status",
            tool_name="adminbot_service_status",
            tool_request=tool_request,
            params={
                "service_name": payload.service_name,
            },
        )
        return self.client.send_request(envelope)

    def _build_envelope(
        self,
        *,
        action: AdminBotAction,
        tool_name: AdminBotToolName,
        tool_request: ToolExecutionRequest,
        params: dict[str, object],
    ) -> AdminBotRequestEnvelope:
        """Build the strict AdminBot request envelope."""
        return AdminBotRequestEnvelope(
            version=1,
            tool_name=tool_name,
            requested_by=AdminBotRequestedBy(
                type="agent",
                id=self.client.config.adapter_id,
            ),
            agent_run_id=tool_request.run_id,
            correlation_id=tool_request.correlation_id,
            action=action,
            params=params,
            timeout_ms=max(1, int(self.client.config.timeout_seconds * 1000)),
        )
