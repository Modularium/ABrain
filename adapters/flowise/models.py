"""Supported Flowise interop models for the V1 compatibility layer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.decision.agent_descriptor import AgentDescriptor


class FlowiseInteropWarning(BaseModel):
    """Structured warning emitted during import or export."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class FlowiseAgentArtifact(BaseModel):
    """Small, explicitly supported Flowise-compatible agent artifact."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    type: Literal["agent"] = "agent"
    tools: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    llm: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tools", "capabilities")
    @classmethod
    def normalize_lists(cls, value: list[str]) -> list[str]:
        """Normalize string lists while preserving order."""
        seen: set[str] = set()
        normalized_items: list[str] = []
        for item in value:
            normalized = item.strip()
            if not normalized:
                raise ValueError("list entries must not be empty")
            if normalized not in seen:
                seen.add(normalized)
                normalized_items.append(normalized)
        return normalized_items


class FlowiseChatflowNode(BaseModel):
    """Small subset of Flowise chatflow node data used for import only."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    type: str | None = None
    label: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class FlowiseChatflowArtifact(BaseModel):
    """Small subset of Flowise chatflow export used for import only."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    name: str | None = None
    type: str | None = None
    description: str | None = None
    nodes: list[FlowiseChatflowNode] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class FlowiseImportReport(BaseModel):
    """Import result with warnings."""

    model_config = ConfigDict(extra="forbid")

    descriptor: AgentDescriptor
    warnings: list[FlowiseInteropWarning] = Field(default_factory=list)


class FlowiseExportReport(BaseModel):
    """Export result with warnings."""

    model_config = ConfigDict(extra="forbid")

    artifact: FlowiseAgentArtifact
    warnings: list[FlowiseInteropWarning] = Field(default_factory=list)
