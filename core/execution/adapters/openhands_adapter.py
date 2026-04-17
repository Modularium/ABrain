"""OpenHands execution adapter using the documented V1 conversation API."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import httpx

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.models.errors import StructuredError
from core.execution.provider_capabilities import ExecutionCapabilities
from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.adapters.budget import AdapterBudget, IsolationRequirements

from .base import BaseExecutionAdapter, ExecutionResult


class OpenHandsExecutionAdapter(BaseExecutionAdapter):
    """Minimal OpenHands adapter for non-streaming task submission."""

    adapter_name = "openhands"
    conversation_path = "/api/v1/app-conversations"

    capabilities = ExecutionCapabilities(
        execution_protocol="http_api",
        requires_network=True,
        requires_local_process=False,
        supports_cost_reporting=True,
        supports_token_reporting=False,
        runtime_constraints=["requires_service_endpoint"],
    )

    manifest = AdapterManifest(
        adapter_name="openhands",
        description=(
            "Code-execution adapter for the OpenHands service. Submits tasks via "
            "the V1 conversation API; the remote service has full filesystem and "
            "tool access."
        ),
        capabilities=ExecutionCapabilities(
            execution_protocol="http_api",
            requires_network=True,
            requires_local_process=False,
            supports_cost_reporting=True,
            supports_token_reporting=False,
            runtime_constraints=["requires_service_endpoint"],
        ),
        risk_tier=RiskTier.HIGH,
        required_metadata_keys=[],
        optional_metadata_keys=["endpoint_url", "api_key", "selected_repository", "branch"],
        recommended_policy_scope="code_execution",
        budget=AdapterBudget(
            max_cost_usd=5.0,
            max_duration_ms=120_000,
        ),
        isolation=IsolationRequirements(
            network_access_required=True,
            filesystem_write_required=True,
            process_spawn_required=True,
            privileged_operation=False,
        ),
    )

    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def validate(self, task, agent_descriptor: AgentDescriptor) -> None:
        super().validate(task, agent_descriptor)
        if agent_descriptor.source_type != AgentSourceType.OPENHANDS:
            raise ValueError("OpenHands adapter requires source_type='openhands'")
        if agent_descriptor.execution_kind not in {
            AgentExecutionKind.HTTP_SERVICE,
            AgentExecutionKind.LOCAL_PROCESS,
        }:
            raise ValueError("OpenHands adapter requires execution_kind='http_service'")
        if not self.task_text(task).strip():
            raise ValueError("OpenHands task text must not be empty")

    def execute(self, task, agent_descriptor: AgentDescriptor) -> ExecutionResult:
        self.validate(task, agent_descriptor)
        task_text = self.task_text(task).strip()
        endpoint = str(
            agent_descriptor.metadata.get("endpoint_url")
            or agent_descriptor.metadata.get("base_url")
            or agent_descriptor.metadata.get("url")
            or "http://localhost:3000"
        ).rstrip("/")
        api_key = agent_descriptor.metadata.get("api_key")
        selected_repository = agent_descriptor.metadata.get("selected_repository")
        payload: dict[str, Any] = {
            "initial_message": {"content": [{"type": "text", "text": task_text}]},
        }
        if selected_repository:
            payload["selected_repository"] = selected_repository
        branch = agent_descriptor.metadata.get("branch")
        if isinstance(branch, str) and branch:
            payload["branch"] = branch
        headers = {"Content-Type": "application/json"}
        if isinstance(api_key, str) and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{endpoint}{self.conversation_path}",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                error=StructuredError(
                    error_code="adapter_timeout",
                    message="OpenHands request timed out",
                    details={"adapter": self.adapter_name, "exception": str(exc)},
                ),
                metadata={"adapter": self.adapter_name, "endpoint": endpoint, "path": self.conversation_path},
            )
        except httpx.HTTPStatusError as exc:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                error=StructuredError(
                    error_code="adapter_http_error",
                    message="OpenHands request failed",
                    details={
                        "adapter": self.adapter_name,
                        "status_code": exc.response.status_code,
                        "exception": str(exc),
                    },
                ),
                metadata={"adapter": self.adapter_name, "endpoint": endpoint, "path": self.conversation_path},
            )
        except httpx.RequestError as exc:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                error=StructuredError(
                    error_code="adapter_transport_error",
                    message="OpenHands transport failed",
                    details={"adapter": self.adapter_name, "exception": str(exc)},
                ),
                metadata={"adapter": self.adapter_name, "endpoint": endpoint, "path": self.conversation_path},
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if not isinstance(data, Mapping):
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                raw_output=data,
                error=StructuredError(
                    error_code="adapter_protocol_error",
                    message="OpenHands response must be a JSON object",
                    details={"adapter": self.adapter_name, "response_type": type(data).__name__},
                ),
                duration_ms=duration_ms,
                metadata={"adapter": self.adapter_name, "endpoint": endpoint, "path": self.conversation_path},
            )
        extracted = self._extract_output(data)
        return ExecutionResult(
            agent_id=agent_descriptor.agent_id,
            success=True,
            output=extracted,
            raw_output=data,
            duration_ms=duration_ms,
            cost=self._extract_cost(data),
            metadata={
                "adapter": self.adapter_name,
                "endpoint": endpoint,
                "path": self.conversation_path,
                "selected_repository": selected_repository,
            },
        )

    def _extract_output(self, data: Mapping[str, Any]) -> Any:
        assistant_message = data.get("assistant_response") or data.get("response")
        if assistant_message:
            return assistant_message
        for key in ("id", "app_conversation_id", "conversation_id", "status"):
            if key in data:
                return data[key]
        return dict(data)

    def _extract_cost(self, data: Mapping[str, Any]) -> float | None:
        for key in ("cost", "cost_usd", "estimated_cost"):
            value = data.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        usage = data.get("usage")
        if isinstance(usage, Mapping):
            for key in ("cost", "cost_usd", "estimated_cost"):
                value = usage.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        return None
