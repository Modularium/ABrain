"""MCP v2 handler for single-task execution."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunTaskParams(BaseModel):
    """Strict MCP input for the canonical single-task entry."""

    model_config = ConfigDict(extra="forbid")

    task_type: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=4096)
    input_data: Any | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)

    @field_validator("task_type", "description")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class RunTaskHandler:
    """Thin wrapper around :func:`services.core.run_task`."""

    name = "abrain.run_task"
    description = "Run a single ABrain task through decision, policy, execution, learning and audit."
    input_model = RunTaskParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import get_explainability, run_task

        request = self.input_model.model_validate(params)
        task = {
            "task_type": request.task_type,
            "description": request.description,
            "input_data": request.input_data,
            "preferences": request.preferences,
        }
        core_result = run_task(task)
        trace_id = (core_result.get("trace") or {}).get("trace_id")
        explainability = (
            get_explainability(trace_id).get("explainability", [])
            if isinstance(trace_id, str) and trace_id
            else []
        )
        return {
            "status": _map_run_task_status(str(core_result.get("status") or "error")),
            "result": core_result.get("execution"),
            "decision": core_result.get("decision"),
            "approval": core_result.get("approval"),
            "governance": core_result.get("governance"),
            "trace_id": trace_id,
            "explainability_summary": _build_explainability_summary(explainability),
            "warnings": list(core_result.get("warnings") or []),
        }


def _map_run_task_status(status: str) -> str:
    if status == "completed":
        return "success"
    if status == "paused":
        return "approval_required"
    return "error"


def _build_explainability_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}
    record = records[-1]
    return {
        "selected_agent": record.get("selected_agent_id"),
        "policy_decision": "require_approval" if record.get("approval_required") else "allow",
        "reason": record.get("routing_reason_summary"),
        "matched_policy_ids": record.get("matched_policy_ids", []),
    }
