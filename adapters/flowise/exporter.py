"""Flowise export helpers for canonical :class:`AgentDescriptor` objects."""

from __future__ import annotations

from typing import Any, Mapping

from core.decision.agent_descriptor import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)

from .models import FlowiseAgentArtifact, FlowiseExportReport, FlowiseInteropWarning


def _metadata_list(metadata: Mapping[str, Any], key: str) -> list[str]:
    value = metadata.get(key)
    if not isinstance(value, list):
        return []
    normalized_items: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            normalized_items.append(normalized)
    return normalized_items


def _metadata_dict(metadata: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, dict):
            return value
    return {}


def export_descriptor_to_flowise(descriptor: AgentDescriptor) -> FlowiseExportReport:
    """Export a canonical descriptor as a small Flowise-compatible artifact."""
    if descriptor.execution_kind == AgentExecutionKind.SYSTEM_EXECUTOR:
        raise ValueError("system_executor descriptors are not exportable to Flowise in V1")
    if not descriptor.editable_in_flowise:
        raise ValueError("descriptor is not marked editable_in_flowise")

    warnings: list[FlowiseInteropWarning] = []
    tool_refs = _metadata_list(descriptor.metadata, "tool_refs")
    if not tool_refs:
        warnings.append(
            FlowiseInteropWarning(
                code="missing_tool_refs",
                message="Descriptor metadata has no exportable tool_refs; tools will be empty.",
            )
        )

    llm = _metadata_dict(descriptor.metadata, "flowise_llm", "llm", "model_config")
    if not llm:
        warnings.append(
            FlowiseInteropWarning(
                code="missing_llm_config",
                message="Descriptor metadata has no explicit Flowise LLM config; llm will be empty.",
            )
        )

    description = str(descriptor.metadata.get("description") or "")
    metadata: dict[str, Any] = {
        "source_type": descriptor.source_type.value,
        "execution_kind": descriptor.execution_kind.value,
        "trust_level": descriptor.trust_level.value,
        "availability": descriptor.availability.value,
        "editable_in_flowise": descriptor.editable_in_flowise,
    }
    if descriptor.metadata.get("flowise_artifact_type"):
        metadata["flowise_artifact_type"] = descriptor.metadata["flowise_artifact_type"]

    artifact = FlowiseAgentArtifact(
        id=descriptor.agent_id,
        name=descriptor.display_name,
        description=description,
        tools=tool_refs,
        capabilities=descriptor.capabilities,
        llm=llm,
        created_at=str(descriptor.metadata.get("created_at")) if descriptor.metadata.get("created_at") else None,
        version=str(descriptor.metadata.get("version")) if descriptor.metadata.get("version") else None,
        metadata=metadata,
    )
    return FlowiseExportReport(artifact=artifact, warnings=warnings)


def legacy_agent_config_to_descriptor(config: Mapping[str, Any]) -> AgentDescriptor:
    """Map a legacy agent config dict into the canonical descriptor model."""
    raw_name = str(config.get("name") or config.get("agent_id") or "unnamed-agent").strip()
    if not raw_name:
        raw_name = "unnamed-agent"

    capabilities = [
        item.strip()
        for item in config.get("capabilities", [])
        if isinstance(item, str) and item.strip()
    ]
    tool_refs = [
        item.strip()
        for item in config.get("tools", [])
        if isinstance(item, str) and item.strip()
    ]

    return AgentDescriptor(
        agent_id=raw_name,
        display_name=raw_name,
        source_type=AgentSourceType.NATIVE,
        execution_kind=AgentExecutionKind.HTTP_SERVICE,
        capabilities=capabilities,
        editable_in_flowise=True,
        metadata={
            "description": str(config.get("description") or config.get("domain") or ""),
            "tool_refs": tool_refs,
            "model_config": config.get("model_config") if isinstance(config.get("model_config"), dict) else {},
            "created_at": config.get("created_at"),
            "version": config.get("version"),
        },
    )


def export_legacy_agent_config_to_flowise(config: Mapping[str, Any]) -> dict[str, Any]:
    """Export a legacy agent config dict using the canonical interop path."""
    descriptor = legacy_agent_config_to_descriptor(config)
    report = export_descriptor_to_flowise(descriptor)
    return report.artifact.model_dump(mode="json", by_alias=True)
