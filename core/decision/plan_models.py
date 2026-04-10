"""Plan models for multi-agent orchestration."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .agent_descriptor import AgentExecutionKind, AgentSourceType
from .capabilities import CapabilityRisk


class PlanStrategy(str, Enum):
    """Supported orchestration strategies."""

    SINGLE = "single"
    SEQUENTIAL = "sequential"
    PARALLEL_GROUPS = "parallel_groups"


class PlanStep(BaseModel):
    """Single executable step inside an execution plan."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1)
    required_capabilities: list[str] = Field(default_factory=list)
    preferred_source_types: list[AgentSourceType] = Field(default_factory=list)
    preferred_execution_kinds: list[AgentExecutionKind] = Field(default_factory=list)
    inputs_from_steps: list[str] = Field(default_factory=list)
    risk: CapabilityRisk = CapabilityRisk.MEDIUM
    allow_parallel_group: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("step_id", "title", "description")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("required_capabilities", "inputs_from_steps")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized_values: list[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                normalized_values.append(normalized)
        return normalized_values


class ExecutionPlan(BaseModel):
    """Structured execution plan for multi-step orchestration."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=128)
    original_task: dict[str, Any] = Field(default_factory=dict)
    steps: list[PlanStep] = Field(default_factory=list)
    strategy: PlanStrategy = PlanStrategy.SINGLE
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("steps")
    @classmethod
    def validate_step_order(cls, steps: list[PlanStep]) -> list[PlanStep]:
        known_ids: set[str] = set()
        for step in steps:
            if step.step_id in known_ids:
                raise ValueError(f"duplicate step_id: {step.step_id}")
            for dependency in step.inputs_from_steps:
                if dependency not in known_ids:
                    raise ValueError(
                        f"step {step.step_id} depends on unknown or later step {dependency}"
                    )
            known_ids.add(step.step_id)
        return steps
