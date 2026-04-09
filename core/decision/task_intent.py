"""Task intent models for the canonical decision layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .capabilities import CapabilityRisk


class TaskIntent(BaseModel):
    """Normalized task intent used by the planner and router."""

    model_config = ConfigDict(extra="forbid")

    task_type: str = Field(min_length=1, max_length=128)
    domain: str = Field(min_length=1, max_length=128)
    risk: CapabilityRisk = CapabilityRisk.MEDIUM
    required_capabilities: list[str] = Field(default_factory=list)
    execution_hints: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None

    @field_validator("task_type", "domain")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_optional_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("required_capabilities")
    @classmethod
    def normalize_required_capabilities(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized_capabilities: list[str] = []
        for capability_id in value:
            normalized = capability_id.strip()
            if not normalized:
                raise ValueError("required_capabilities must not contain empty values")
            if normalized not in seen:
                seen.add(normalized)
                normalized_capabilities.append(normalized)
        return normalized_capabilities


class PlannerResult(BaseModel):
    """Structured planner output."""

    model_config = ConfigDict(extra="forbid")

    intent: TaskIntent
    normalized_task: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
