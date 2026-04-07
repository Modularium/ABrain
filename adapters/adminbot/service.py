"""Strict AdminBot service mapping for fixed tool handlers."""

from __future__ import annotations

from dataclasses import dataclass

from .client import AdminBotClient, AdminBotClientConfig
from core.models.adminbot import (
    AdminBotGetHealthInput,
    AdminBotGetServiceStatusInput,
    AdminBotGetStatusInput,
    AdminBotRequestEnvelope,
    AdminBotRequestedBy,
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

    def get_status(
        self,
        tool_request: ToolExecutionRequest,
        payload: AdminBotGetStatusInput,
    ) -> dict[str, object]:
        """Map ``adminbot_get_status`` to ``get_status``."""
        envelope = self._build_envelope(
            action="get_status",
            tool_request=tool_request,
            payload={"target": payload.target.value},
        )
        return self.client.send_request(envelope)

    def get_health(
        self,
        tool_request: ToolExecutionRequest,
        payload: AdminBotGetHealthInput,
    ) -> dict[str, object]:
        """Map ``adminbot_get_health`` to ``get_health``."""
        envelope = self._build_envelope(
            action="get_health",
            tool_request=tool_request,
            payload={"include_checks": payload.include_checks},
        )
        return self.client.send_request(envelope)

    def get_service_status(
        self,
        tool_request: ToolExecutionRequest,
        payload: AdminBotGetServiceStatusInput,
    ) -> dict[str, object]:
        """Map ``adminbot_get_service_status`` to ``get_service_status``."""
        envelope = self._build_envelope(
            action="get_service_status",
            tool_request=tool_request,
            payload={
                "service_name": payload.service_name,
                "allow_nonsystem": payload.allow_nonsystem,
            },
        )
        return self.client.send_request(envelope)

    def _build_envelope(
        self,
        *,
        action: str,
        tool_request: ToolExecutionRequest,
        payload: dict[str, object],
    ) -> AdminBotRequestEnvelope:
        """Build the strict AdminBot request envelope."""
        return AdminBotRequestEnvelope(
            version=1,
            action=action,
            requested_by=AdminBotRequestedBy(
                type="agent",
                id=self.client.config.adapter_id,
            ),
            payload=payload,
            run_id=tool_request.run_id,
            correlation_id=tool_request.correlation_id,
        )
