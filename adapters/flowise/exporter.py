"""Export canonical ABrain agent descriptors into minimal Flowise artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind

from .models import FlowiseAgent, FlowiseMetadata, FlowiseTool


def export_to_flowise(descriptor: AgentDescriptor) -> FlowiseAgent:
    """Project a canonical descriptor into a minimal Flowise artifact."""
    if descriptor.execution_kind == AgentExecutionKind.SYSTEM_EXECUTOR:
        raise ValueError("system_executor descriptors are not exportable to minimal Flowise artifacts")
    metadata = dict(descriptor.metadata)
    description = _normalize_optional_string(metadata.get("flowise_description"))
    flowise_tools = _coerce_tools(metadata.get("flowise_tools"))
    if not flowise_tools:
        flowise_tools = [
            FlowiseTool(
                id=capability_id,
                name=capability_id,
                description="Exported from AgentDescriptor capability",
            )
            for capability_id in descriptor.capabilities
        ]
    metadata_payload = {
        "source_type": descriptor.source_type.value,
        "execution_kind": descriptor.execution_kind.value,
        "editable_in_flowise": descriptor.editable_in_flowise,
        "capabilities": list(descriptor.capabilities),
    }
    return FlowiseAgent(
        id=descriptor.agent_id,
        name=descriptor.display_name,
        description=description,
        tools=flowise_tools,
        metadata=FlowiseMetadata(values=metadata_payload),
    )


def _coerce_tools(data: Any) -> list[FlowiseTool]:
    if not isinstance(data, list):
        return []
    tools: list[FlowiseTool] = []
    for item in data:
        if isinstance(item, FlowiseTool):
            tools.append(item)
            continue
        if isinstance(item, str):
            normalized = item.strip()
            if normalized:
                tools.append(FlowiseTool(id=normalized, name=normalized))
            continue
        if isinstance(item, Mapping):
            tool_id = str(item.get("id") or item.get("name") or "").strip()
            tool_name = str(item.get("name") or item.get("id") or "").strip()
            if tool_id and tool_name:
                tools.append(
                    FlowiseTool(
                        id=tool_id,
                        name=tool_name,
                        description=_normalize_optional_string(item.get("description")),
                    )
                )
    return tools


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
