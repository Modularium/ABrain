"""Flowise import helpers for canonical :class:`AgentDescriptor` objects."""

from __future__ import annotations

import re
from typing import Any, Mapping

from core.decision.agent_descriptor import (
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
)

from .models import (
    FlowiseAgentArtifact,
    FlowiseChatflowArtifact,
    FlowiseImportReport,
    FlowiseInteropWarning,
)


def _normalize_string_list(value: Any) -> list[str]:
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


def _safe_extra_fields(payload: Mapping[str, Any], ignored_fields: list[str]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for key in ignored_fields:
        value = payload.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            extras[key] = value
        elif isinstance(value, (list, dict)):
            extras[key] = value
    return extras


def _derive_agent_id(raw_id: str | None, raw_name: str | None) -> str:
    candidate = (raw_id or raw_name or "flowise-agent").strip().lower()
    normalized = re.sub(r"[^a-z0-9._-]+", "-", candidate).strip("-")
    return normalized or "flowise-agent"


def _import_agent_definition(payload: Mapping[str, Any]) -> FlowiseImportReport:
    supported_fields = {
        "id",
        "name",
        "description",
        "type",
        "tools",
        "capabilities",
        "llm",
        "created_at",
        "version",
        "metadata",
    }
    warnings: list[FlowiseInteropWarning] = []
    ignored_fields = sorted(set(payload) - supported_fields)
    if ignored_fields:
        warnings.append(
            FlowiseInteropWarning(
                code="ignored_fields",
                message=(
                    "Unsupported Flowise agent fields were kept only as metadata: "
                    + ", ".join(ignored_fields)
                ),
            )
        )

    artifact = FlowiseAgentArtifact(
        id=_derive_agent_id(payload.get("id"), payload.get("name")),
        name=str(payload.get("name") or payload.get("id") or "Unnamed Flowise Agent"),
        description=str(payload.get("description") or ""),
        tools=_normalize_string_list(payload.get("tools")),
        capabilities=_normalize_string_list(payload.get("capabilities")),
        llm=payload.get("llm") if isinstance(payload.get("llm"), dict) else {},
        created_at=str(payload.get("created_at")) if payload.get("created_at") else None,
        version=str(payload.get("version")) if payload.get("version") else None,
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    )

    metadata: dict[str, Any] = {
        "description": artifact.description,
        "tool_refs": artifact.tools,
        "flowise_llm": artifact.llm,
        "flowise_artifact_type": "agent",
    }
    if artifact.created_at is not None:
        metadata["created_at"] = artifact.created_at
    if artifact.version is not None:
        metadata["version"] = artifact.version
    if artifact.metadata:
        metadata["flowise_metadata"] = artifact.metadata
    extras = _safe_extra_fields(payload, ignored_fields)
    if extras:
        metadata["flowise_extra_fields"] = extras

    descriptor = AgentDescriptor(
        agent_id=artifact.id,
        display_name=artifact.name,
        source_type=AgentSourceType.FLOWISE,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=artifact.capabilities,
        editable_in_flowise=True,
        metadata=metadata,
    )
    return FlowiseImportReport(descriptor=descriptor, warnings=warnings)


def _extract_node_refs(artifact: FlowiseChatflowArtifact) -> list[str]:
    node_refs: list[str] = []
    seen: set[str] = set()
    for node in artifact.nodes:
        candidates = [
            node.label,
            node.type,
            node.data.get("name") if isinstance(node.data, dict) else None,
            node.data.get("label") if isinstance(node.data, dict) else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, str):
                normalized = candidate.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    node_refs.append(normalized)
                    break
    return node_refs


def _extract_llm_from_nodes(artifact: FlowiseChatflowArtifact) -> dict[str, Any]:
    for node in artifact.nodes:
        data = node.data if isinstance(node.data, dict) else {}
        node_type = (node.type or data.get("type") or "").lower()
        if any(token in node_type for token in ("openai", "anthropic", "llm", "chat")):
            llm: dict[str, Any] = {}
            if isinstance(data.get("provider"), str):
                llm["provider"] = data["provider"]
            if isinstance(data.get("model"), str):
                llm["model"] = data["model"]
            if isinstance(data.get("modelName"), str):
                llm["model"] = data["modelName"]
            if llm:
                return llm
    return {}


def _import_chatflow_definition(payload: Mapping[str, Any]) -> FlowiseImportReport:
    artifact = FlowiseChatflowArtifact.model_validate(payload)
    warnings = [
        FlowiseInteropWarning(
            code="partial_chatflow_support",
            message=(
                "Flowise chatflow imports are reduced to descriptor metadata; "
                "node graph semantics are not reconstructed in V1."
            ),
        )
    ]
    node_refs = _extract_node_refs(artifact)
    llm = _extract_llm_from_nodes(artifact)
    metadata: dict[str, Any] = {
        "description": artifact.description or "",
        "flowise_artifact_type": artifact.type or "chatflow",
        "flowise_node_refs": node_refs,
        "flowise_edge_count": len(artifact.edges),
        "flowise_llm": llm,
    }
    descriptor = AgentDescriptor(
        agent_id=_derive_agent_id(artifact.id, artifact.name),
        display_name=(artifact.name or artifact.id or "Unnamed Flowise Chatflow").strip(),
        source_type=AgentSourceType.FLOWISE,
        execution_kind=AgentExecutionKind.WORKFLOW_ENGINE,
        capabilities=[],
        editable_in_flowise=True,
        metadata=metadata,
    )
    return FlowiseImportReport(descriptor=descriptor, warnings=warnings)


def import_flowise_artifact(payload: Mapping[str, Any]) -> FlowiseImportReport:
    """Import a supported Flowise artifact into the canonical agent model."""
    if not isinstance(payload, Mapping):
        raise TypeError("Flowise artifact must be a mapping")
    if isinstance(payload.get("nodes"), list):
        return _import_chatflow_definition(payload)
    return _import_agent_definition(payload)
