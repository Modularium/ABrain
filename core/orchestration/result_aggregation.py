"""Structured plan result aggregation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.execution.adapters.base import ExecutionResult


class StepExecutionResult(BaseModel):
    """Structured outcome for a single plan step."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    selected_agent_id: str | None = None
    success: bool
    output: Any | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_execution_result(
        cls,
        step_id: str,
        execution: ExecutionResult,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> "StepExecutionResult":
        payload = dict(metadata or {})
        payload.setdefault("execution_metadata", execution.metadata)
        if execution.error is not None:
            payload.setdefault("error", execution.error.model_dump(mode="json"))
        return cls(
            step_id=step_id,
            selected_agent_id=execution.agent_id or None,
            success=execution.success,
            output=execution.output,
            warnings=list(execution.warnings),
            metadata=payload,
        )


class PlanExecutionResult(BaseModel):
    """Aggregated result for a full execution plan."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    success: bool
    step_results: list[StepExecutionResult] = Field(default_factory=list)
    final_output: Any | None = None
    aggregated_warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResultAggregator:
    """Aggregate ordered step results into a plan result."""

    def aggregate(
        self,
        plan_id: str,
        step_results: list[StepExecutionResult],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> PlanExecutionResult:
        aggregated_warnings: list[str] = []
        outputs_by_step: dict[str, Any] = {}
        success = True
        for step_result in step_results:
            outputs_by_step[step_result.step_id] = step_result.output
            aggregated_warnings.extend(step_result.warnings)
            success = success and step_result.success
        final_output = step_results[-1].output if step_results else None
        return PlanExecutionResult(
            plan_id=plan_id,
            success=success,
            step_results=step_results,
            final_output=final_output,
            aggregated_warnings=aggregated_warnings,
            metadata={
                **(metadata or {}),
                "step_count": len(step_results),
                "outputs_by_step": outputs_by_step,
            },
        )
