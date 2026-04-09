"""Canonical capability models for ABrain agent descriptors."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CapabilityRisk(StrEnum):
    """Risk level attached to a capability."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Capability(BaseModel):
    """Framework-agnostic capability descriptor."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    domain: str = Field(min_length=1, max_length=128)
    risk: CapabilityRisk = CapabilityRisk.LOW
    requires_human_approval: bool = False
    requires_certification: bool = False
    required_tools: list[str] = Field(default_factory=list)

    @field_validator("id", "domain")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        """Reject blank values and normalize surrounding whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("required_tools")
    @classmethod
    def normalize_required_tools(cls, value: list[str]) -> list[str]:
        """Normalize tool ids while preserving insertion order."""
        seen: set[str] = set()
        normalized_tools: list[str] = []
        for tool in value:
            normalized = tool.strip()
            if not normalized:
                raise ValueError("required_tools must not contain empty values")
            if normalized not in seen:
                seen.add(normalized)
                normalized_tools.append(normalized)
        return normalized_tools
