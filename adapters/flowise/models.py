"""Minimal Flowise interoperability models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlowiseTool(BaseModel):
    """Minimal tool shape used by the Flowise interop layer."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    description: str | None = None

    @field_validator("id", "name")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class FlowiseMetadata(BaseModel):
    """Typed wrapper for optional Flowise metadata."""

    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] = Field(default_factory=dict)


class FlowiseAgent(BaseModel):
    """Small Flowise-facing agent artifact for import/export."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    description: str | None = None
    tools: list[FlowiseTool] = Field(default_factory=list)
    metadata: FlowiseMetadata | None = None

    @field_validator("id", "name")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized
