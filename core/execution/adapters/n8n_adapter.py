"""n8n workflow execution adapter."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import httpx

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.models.errors import StructuredError
from core.model_context import ModelContext, TaskContext
from core.execution.provider_capabilities import ExecutionCapabilities

from .base import BaseExecutionAdapter, ExecutionResult


class N8NExecutionAdapter(BaseExecutionAdapter):
    """Execute workflow-style tasks through a fixed n8n webhook contract."""

    adapter_name = "n8n"

    capabilities = ExecutionCapabilities(
        execution_protocol="webhook_json",
        requires_network=True,
        requires_local_process=False,
        supports_cost_reporting=True,
        supports_token_reporting=False,
        runtime_constraints=["requires_webhook_url"],
    )

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def validate(self, task, agent_descriptor: AgentDescriptor) -> None:
        super().validate(task, agent_descriptor)
        if agent_descriptor.source_type != AgentSourceType.N8N:
            raise ValueError("n8n adapter requires source_type='n8n'")
        if agent_descriptor.execution_kind != AgentExecutionKind.WORKFLOW_ENGINE:
            raise ValueError("n8n adapter requires execution_kind='workflow_engine'")
        if not self.task_text(task).strip():
            raise ValueError("n8n task text must not be empty")
        self._resolve_webhook_url(agent_descriptor)

    def execute(self, task, agent_descriptor: AgentDescriptor) -> ExecutionResult:
        self.validate(task, agent_descriptor)
        webhook_url = self._resolve_webhook_url(agent_descriptor)
        headers = self._build_headers(agent_descriptor)
        payload = self._build_payload(task, agent_descriptor)
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(webhook_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            return self._error_result(
                agent_descriptor,
                webhook_url,
                "adapter_timeout",
                "n8n request timed out",
                {"adapter": self.adapter_name, "exception": str(exc)},
            )
        except httpx.HTTPStatusError as exc:
            return self._error_result(
                agent_descriptor,
                webhook_url,
                "adapter_http_error",
                "n8n request failed",
                {
                    "adapter": self.adapter_name,
                    "status_code": exc.response.status_code,
                    "exception": str(exc),
                },
            )
        except httpx.RequestError as exc:
            return self._error_result(
                agent_descriptor,
                webhook_url,
                "adapter_transport_error",
                "n8n transport failed",
                {"adapter": self.adapter_name, "exception": str(exc)},
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if not isinstance(data, Mapping):
            return self._error_result(
                agent_descriptor,
                webhook_url,
                "adapter_protocol_error",
                "n8n response must be a JSON object",
                {"adapter": self.adapter_name, "response_type": type(data).__name__},
                raw_output=data,
                duration_ms=duration_ms,
            )
        workflow_success = bool(data.get("success", True))
        output = data.get("result") or data.get("output") or data.get("data") or dict(data)
        warnings = [str(warning) for warning in data.get("warnings", []) if isinstance(warning, str)]
        return ExecutionResult(
            agent_id=agent_descriptor.agent_id,
            success=workflow_success,
            output=output,
            raw_output=data,
            duration_ms=duration_ms,
            cost=self._extract_cost(data),
            warnings=warnings,
            metadata={
                "adapter": self.adapter_name,
                "webhook_url": webhook_url,
                "workflow_contract": "webhook_v1",
                "workflow_id": agent_descriptor.metadata.get("workflow_id"),
            },
            error=None
            if workflow_success
            else StructuredError(
                error_code="adapter_execution_error",
                message="n8n workflow reported a failure",
                details={"adapter": self.adapter_name, "response": dict(data)},
            ),
        )

    def _resolve_webhook_url(self, agent_descriptor: AgentDescriptor) -> str:
        webhook_url = agent_descriptor.metadata.get("webhook_url")
        if isinstance(webhook_url, str) and webhook_url.strip():
            return webhook_url.rstrip("/")
        base_url = agent_descriptor.metadata.get("base_url")
        webhook_path = agent_descriptor.metadata.get("webhook_path")
        if isinstance(base_url, str) and base_url.strip() and isinstance(webhook_path, str) and webhook_path.strip():
            normalized_path = webhook_path.strip()
            if not normalized_path.startswith("/"):
                normalized_path = f"/{normalized_path}"
            if not normalized_path.startswith(("/webhook/", "/webhook-test/")):
                raise ValueError("n8n webhook_path must start with /webhook/ or /webhook-test/")
            parsed = urlparse(normalized_path)
            if parsed.scheme or parsed.netloc:
                raise ValueError("n8n webhook_path must be relative")
            return f"{base_url.rstrip('/')}{normalized_path}"
        raise ValueError("n8n adapter requires webhook_url or base_url + webhook_path")

    def _build_headers(self, agent_descriptor: AgentDescriptor) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        configured_headers = agent_descriptor.metadata.get("headers")
        if isinstance(configured_headers, Mapping):
            for key, value in configured_headers.items():
                if isinstance(key, str) and isinstance(value, str) and key.strip():
                    headers[key.strip()] = value
        auth_header = agent_descriptor.metadata.get("auth_header")
        if isinstance(auth_header, str) and auth_header.strip():
            headers["Authorization"] = auth_header.strip()
        api_key = agent_descriptor.metadata.get("api_key")
        if "Authorization" not in headers and isinstance(api_key, str) and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        return headers

    def _build_payload(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        agent_descriptor: AgentDescriptor,
    ) -> dict[str, Any]:
        task_text = self.task_text(task).strip()
        preferences = self.task_preferences(task)
        payload: dict[str, Any] = {
            "task": {
                "task_type": self.task_type(task),
                "description": task_text,
                "input_data": self._task_input_data(task),
                "preferences": preferences,
            },
            "agent": {
                "agent_id": agent_descriptor.agent_id,
                "source_type": agent_descriptor.source_type.value,
                "execution_kind": agent_descriptor.execution_kind.value,
                "capabilities": list(agent_descriptor.capabilities),
            },
            "contract": "abrain.n8n.workflow.v1",
        }
        workflow_id = agent_descriptor.metadata.get("workflow_id")
        if isinstance(workflow_id, str) and workflow_id:
            payload["workflow_id"] = workflow_id
        fixed_payload = agent_descriptor.metadata.get("fixed_payload")
        if isinstance(fixed_payload, Mapping):
            payload["workflow_input"] = dict(fixed_payload)
        return payload

    def _task_input_data(self, task: TaskContext | ModelContext | Mapping[str, Any]) -> str | None:
        if isinstance(task, ModelContext):
            if task.task_context is not None:
                return self._task_input_data(task.task_context)
            return None
        if isinstance(task, TaskContext):
            if task.input_data is None:
                return None
            return task.input_data.text
        if isinstance(task, Mapping):
            value = task.get("input_data")
            if isinstance(value, Mapping):
                text = value.get("text")
                return str(text) if text is not None else None
            if value is None:
                return None
            return str(value)
        return None

    def _extract_cost(self, data: Mapping[str, Any]) -> float | None:
        for key in ("cost", "cost_usd", "total_cost"):
            value = data.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        metrics = data.get("metrics")
        if isinstance(metrics, Mapping):
            for key in ("cost", "cost_usd", "total_cost"):
                value = metrics.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        return None

    def _error_result(
        self,
        agent_descriptor: AgentDescriptor,
        webhook_url: str,
        error_code: str,
        message: str,
        details: dict[str, Any],
        *,
        raw_output: Any | None = None,
        duration_ms: int | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            agent_id=agent_descriptor.agent_id,
            success=False,
            raw_output=raw_output,
            duration_ms=duration_ms,
            error=StructuredError(error_code=error_code, message=message, details=details),
            metadata={
                "adapter": self.adapter_name,
                "webhook_url": webhook_url,
                "workflow_contract": "webhook_v1",
                "workflow_id": agent_descriptor.metadata.get("workflow_id"),
            },
        )
