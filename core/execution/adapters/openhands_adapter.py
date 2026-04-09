"""OpenHands execution adapter using the documented V1 conversation API."""

from __future__ import annotations

import time

import httpx

from core.decision.agent_descriptor import AgentDescriptor
from core.models.errors import StructuredError

from .base import BaseExecutionAdapter, ExecutionResult


class OpenHandsExecutionAdapter(BaseExecutionAdapter):
    """Minimal OpenHands adapter for non-streaming task submission."""

    adapter_name = "openhands"

    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(self, task, agent_descriptor: AgentDescriptor) -> ExecutionResult:
        self.validate(task, agent_descriptor)
        task_text = self.task_text(task).strip()
        if not task_text:
            raise ValueError("OpenHands task text must not be empty")
        endpoint = str(
            agent_descriptor.metadata.get("endpoint_url")
            or agent_descriptor.metadata.get("url")
            or "http://localhost:3000"
        ).rstrip("/")
        api_key = agent_descriptor.metadata.get("api_key")
        selected_repository = agent_descriptor.metadata.get("selected_repository")
        payload = {
            "initial_message": {"content": [{"type": "text", "text": task_text}]},
        }
        if selected_repository:
            payload["selected_repository"] = selected_repository
        headers = {"Content-Type": "application/json"}
        if isinstance(api_key, str) and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{endpoint}/api/v1/app-conversations",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                error=StructuredError(
                    error_code="adapter_timeout",
                    message="OpenHands request timed out",
                    details={"adapter": self.adapter_name},
                ),
                metadata={"adapter": self.adapter_name, "endpoint": endpoint},
            )
        except httpx.HTTPError as exc:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                error=StructuredError(
                    error_code="adapter_http_error",
                    message="OpenHands request failed",
                    details={"adapter": self.adapter_name, "exception": str(exc)},
                ),
                metadata={"adapter": self.adapter_name, "endpoint": endpoint},
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        extracted = data.get("id") or data.get("app_conversation_id") or data.get("status")
        return ExecutionResult(
            agent_id=agent_descriptor.agent_id,
            success=True,
            output=extracted,
            raw_output=data,
            duration_ms=duration_ms,
            metadata={"adapter": self.adapter_name, "endpoint": endpoint},
        )

