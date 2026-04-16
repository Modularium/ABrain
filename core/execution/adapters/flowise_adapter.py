"""Flowise execution adapter for controlled runtime calls."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import httpx

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.models.errors import StructuredError
from core.model_context import ModelContext, TaskContext
from core.execution.provider_capabilities import ExecutionCapabilities
from core.execution.adapters.manifest import AdapterManifest, RiskTier

from .base import BaseExecutionAdapter, ExecutionResult


class FlowiseExecutionAdapter(BaseExecutionAdapter):
    """Execute a task through a constrained Flowise prediction contract."""

    adapter_name = "flowise"

    capabilities = ExecutionCapabilities(
        execution_protocol="http_api",
        requires_network=True,
        requires_local_process=False,
        supports_cost_reporting=True,
        supports_token_reporting=False,
        runtime_constraints=["requires_service_endpoint", "requires_chatflow_id"],
    )

    manifest = AdapterManifest(
        adapter_name="flowise",
        description=(
            "Flowise workflow-engine adapter. POSTs tasks to the Flowise prediction "
            "API endpoint identified by base_url + chatflow_id."
        ),
        capabilities=ExecutionCapabilities(
            execution_protocol="http_api",
            requires_network=True,
            requires_local_process=False,
            supports_cost_reporting=True,
            supports_token_reporting=False,
            runtime_constraints=["requires_service_endpoint", "requires_chatflow_id"],
        ),
        risk_tier=RiskTier.MEDIUM,
        required_metadata_keys=["base_url", "chatflow_id"],
        optional_metadata_keys=["api_key", "headers", "fixed_config", "prediction_url"],
        required_result_metadata_keys=["runtime_contract"],
        recommended_policy_scope="workflow_execution",
    )

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def validate(self, task, agent_descriptor: AgentDescriptor) -> None:
        super().validate(task, agent_descriptor)
        if agent_descriptor.source_type != AgentSourceType.FLOWISE:
            raise ValueError("Flowise adapter requires source_type='flowise'")
        if agent_descriptor.execution_kind != AgentExecutionKind.WORKFLOW_ENGINE:
            raise ValueError("Flowise adapter requires execution_kind='workflow_engine'")
        if not self.task_text(task).strip():
            raise ValueError("Flowise task text must not be empty")
        self._resolve_prediction_url(agent_descriptor)

    def execute(self, task, agent_descriptor: AgentDescriptor) -> ExecutionResult:
        self.validate(task, agent_descriptor)
        prediction_url = self._resolve_prediction_url(agent_descriptor)
        payload = self._build_payload(task, agent_descriptor)
        headers = self._build_headers(agent_descriptor)
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(prediction_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            return self._error_result(
                agent_descriptor,
                prediction_url,
                "adapter_timeout",
                "Flowise request timed out",
                {"adapter": self.adapter_name, "exception": str(exc)},
            )
        except httpx.HTTPStatusError as exc:
            return self._error_result(
                agent_descriptor,
                prediction_url,
                "adapter_http_error",
                "Flowise request failed",
                {
                    "adapter": self.adapter_name,
                    "status_code": exc.response.status_code,
                    "exception": str(exc),
                },
            )
        except httpx.RequestError as exc:
            return self._error_result(
                agent_descriptor,
                prediction_url,
                "adapter_transport_error",
                "Flowise transport failed",
                {"adapter": self.adapter_name, "exception": str(exc)},
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if not isinstance(data, Mapping):
            return self._error_result(
                agent_descriptor,
                prediction_url,
                "adapter_protocol_error",
                "Flowise response must be a JSON object",
                {"adapter": self.adapter_name, "response_type": type(data).__name__},
                raw_output=data,
                duration_ms=duration_ms,
            )
        flowise_success = bool(data.get("success", True))
        warnings = [str(warning) for warning in data.get("warnings", []) if isinstance(warning, str)]
        return ExecutionResult(
            agent_id=agent_descriptor.agent_id,
            success=flowise_success,
            output=self._extract_output(data),
            raw_output=data,
            duration_ms=duration_ms,
            cost=self._extract_cost(data),
            warnings=warnings,
            metadata={
                "adapter": self.adapter_name,
                "prediction_url": prediction_url,
                "runtime_contract": "prediction_v1",
                "chatflow_id": agent_descriptor.metadata.get("chatflow_id"),
            },
            error=None
            if flowise_success
            else StructuredError(
                error_code="adapter_execution_error",
                message="Flowise runtime reported a failure",
                details={"adapter": self.adapter_name, "response": dict(data)},
            ),
        )

    def _resolve_prediction_url(self, agent_descriptor: AgentDescriptor) -> str:
        prediction_url = agent_descriptor.metadata.get("prediction_url")
        if isinstance(prediction_url, str) and prediction_url.strip():
            return prediction_url.rstrip("/")
        base_url = agent_descriptor.metadata.get("base_url")
        chatflow_id = agent_descriptor.metadata.get("chatflow_id")
        if isinstance(base_url, str) and base_url.strip() and isinstance(chatflow_id, str) and chatflow_id.strip():
            return f"{base_url.rstrip('/')}/api/v1/prediction/{chatflow_id.strip()}"
        raise ValueError("Flowise adapter requires prediction_url or base_url + chatflow_id")

    def _build_headers(self, agent_descriptor: AgentDescriptor) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        api_key = agent_descriptor.metadata.get("api_key")
        if isinstance(api_key, str) and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        configured_headers = agent_descriptor.metadata.get("headers")
        if isinstance(configured_headers, Mapping):
            for key, value in configured_headers.items():
                if isinstance(key, str) and isinstance(value, str) and key.strip():
                    headers[key.strip()] = value
        return headers

    def _build_payload(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        agent_descriptor: AgentDescriptor,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "question": self.task_text(task).strip(),
            "overrideConfig": {
                "abrain_agent_id": agent_descriptor.agent_id,
                "abrain_capabilities": list(agent_descriptor.capabilities),
                "abrain_task_type": self.task_type(task),
            },
        }
        task_preferences = self.task_preferences(task)
        if task_preferences:
            payload["overrideConfig"]["abrain_preferences"] = task_preferences
        input_data = self._task_input_data(task)
        if input_data is not None:
            payload["overrideConfig"]["abrain_input_data"] = input_data
        fixed_config = agent_descriptor.metadata.get("fixed_config")
        if isinstance(fixed_config, Mapping):
            payload["overrideConfig"].update(dict(fixed_config))
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

    def _extract_output(self, data: Mapping[str, Any]) -> Any:
        for key in ("text", "result", "output", "response"):
            value = data.get(key)
            if value is not None:
                return value
        return dict(data)

    def _extract_cost(self, data: Mapping[str, Any]) -> float | None:
        for key in ("cost", "cost_usd", "total_cost"):
            value = data.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def _error_result(
        self,
        agent_descriptor: AgentDescriptor,
        prediction_url: str,
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
                "prediction_url": prediction_url,
                "runtime_contract": "prediction_v1",
                "chatflow_id": agent_descriptor.metadata.get("chatflow_id"),
            },
        )
