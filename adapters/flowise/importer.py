"""Import Flowise artifacts into the canonical ABrain agent model."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.decision.agent_descriptor import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
)

from .models import FlowiseAgent, FlowiseMetadata, FlowiseTool

_KNOWN_FIELDS = {"id", "name", "description", "tools", "metadata"}


def import_flowise_agent(data: Mapping[str, Any] | FlowiseAgent) -> AgentDescriptor:
    """Map a minimal Flowise artifact into an ``AgentDescriptor``."""
    flowise_agent, extra_fields = _coerce_agent(data)
    metadata_values = dict(flowise_agent.metadata.values if flowise_agent.metadata else {})
    if extra_fields:
        metadata_values["flowise_extra"] = extra_fields
    metadata_values["flowise_description"] = flowise_agent.description
    metadata_values["flowise_tools"] = [tool.model_dump(mode="json") for tool in flowise_agent.tools]
    metadata_values["imported_from"] = "flowise"
    capabilities = _extract_capabilities(metadata_values)
    return AgentDescriptor(
        agent_id=flowise_agent.id,
        display_name=flowise_agent.name,
        source_type=AgentSourceType.FLOWISE,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=capabilities,
        trust_level=AgentTrustLevel.SANDBOXED,
        availability=AgentAvailability.UNKNOWN,
        editable_in_flowise=True,
        metadata=metadata_values,
    )


def _coerce_agent(data: Mapping[str, Any] | FlowiseAgent) -> tuple[FlowiseAgent, dict[str, Any]]:
    if isinstance(data, FlowiseAgent):
        return data, {}
    if not isinstance(data, Mapping):
        raise TypeError(f"Unsupported Flowise artifact: {type(data)!r}")
    payload = dict(data)
    extra_fields = {key: value for key, value in payload.items() if key not in _KNOWN_FIELDS}
    tools = [_coerce_tool(item) for item in payload.get("tools", []) or []]
    metadata = payload.get("metadata")
    flowise_agent = FlowiseAgent(
        id=str(payload.get("id") or "").strip(),
        name=str(payload.get("name") or "").strip(),
        description=_normalize_optional_string(payload.get("description")),
        tools=tools,
        metadata=_coerce_metadata(metadata),
    )
    return flowise_agent, extra_fields


def _coerce_tool(data: Any) -> FlowiseTool:
    if isinstance(data, FlowiseTool):
        return data
    if isinstance(data, str):
        normalized = data.strip()
        return FlowiseTool(id=normalized, name=normalized)
    if isinstance(data, Mapping):
        return FlowiseTool(
            id=str(data.get("id") or data.get("name") or "").strip(),
            name=str(data.get("name") or data.get("id") or "").strip(),
            description=_normalize_optional_string(data.get("description")),
        )
    raise TypeError(f"Unsupported Flowise tool value: {type(data)!r}")


def _coerce_metadata(data: Any) -> FlowiseMetadata | None:
    if data is None:
        return None
    if isinstance(data, FlowiseMetadata):
        return data
    if isinstance(data, Mapping):
        return FlowiseMetadata(values=dict(data))
    raise TypeError(f"Unsupported Flowise metadata value: {type(data)!r}")


def _extract_capabilities(metadata_values: Mapping[str, Any]) -> list[str]:
    raw_capabilities = metadata_values.get("capabilities")
    if not isinstance(raw_capabilities, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_capabilities:
        if not isinstance(item, str):
            continue
        capability_id = item.strip()
        if capability_id and capability_id not in seen:
            seen.add(capability_id)
            normalized.append(capability_id)
    return normalized


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
