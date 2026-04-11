"""MCP v2 handler for multi-step plan execution."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunPlanOptions(BaseModel):
    """Optional execution hints for MCP plan execution."""

    model_config = ConfigDict(extra="forbid")

    allow_parallel: bool = False


class RunPlanParams(BaseModel):
    """Strict MCP input for the canonical plan entry."""

    model_config = ConfigDict(extra="forbid")

    task_type: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=4096)
    input_data: Any | None = None
    options: RunPlanOptions = Field(default_factory=RunPlanOptions)

    @field_validator("task_type", "description")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class RunPlanHandler:
    """Thin wrapper around :func:`services.core.run_task_plan`."""

    name = "abrain.run_plan"
    description = "Run a multi-step ABrain execution plan through routing, policy, approval, execution and audit."
    input_model = RunPlanParams

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        from services.core import run_task_plan

        request = self.input_model.model_validate(params)
        task = {
            "task_type": request.task_type,
            "description": request.description,
            "input_data": request.input_data,
            "preferences": {
                "execution_hints": {
                    "allow_parallel_quality_checks": request.options.allow_parallel,
                }
            },
        }
        core_result = run_task_plan(task)
        trace_id = (core_result.get("trace") or {}).get("trace_id")
        plan_result = dict(core_result.get("result") or {})
        warnings = list(plan_result.get("aggregated_warnings") or [])
        return {
            "status": _map_plan_status(str(plan_result.get("status") or "error")),
            "plan_result": plan_result,
            "trace_id": trace_id,
            "warnings": warnings,
        }


def _map_plan_status(status: str) -> str:
    if status == "completed":
        return "success"
    if status == "paused":
        return "paused"
    return "error"
