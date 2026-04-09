"""Minimal canonical registry for :class:`AgentDescriptor` objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .agent_descriptor import AgentDescriptor


class AgentRegistrySnapshot(BaseModel):
    """Serializable snapshot for the registry."""

    model_config = ConfigDict(extra="forbid")

    descriptors: list[AgentDescriptor] = Field(default_factory=list)


class AgentRegistry:
    """In-memory registry with explicit JSON load/save support."""

    def __init__(self, descriptors: Iterable[AgentDescriptor] | None = None) -> None:
        self._descriptors: dict[str, AgentDescriptor] = {}
        for descriptor in descriptors or []:
            self.register(descriptor)

    def register(self, descriptor: AgentDescriptor, *, replace: bool = False) -> AgentDescriptor:
        """Register a descriptor or reject duplicates."""
        if not replace and descriptor.agent_id in self._descriptors:
            raise ValueError(f"AgentDescriptor already registered: {descriptor.agent_id}")
        self._descriptors[descriptor.agent_id] = descriptor
        return descriptor

    def get(self, agent_id: str) -> AgentDescriptor | None:
        """Return a descriptor by id."""
        return self._descriptors.get(agent_id)

    def list_descriptors(self) -> list[AgentDescriptor]:
        """Return all registered descriptors ordered by ``agent_id``."""
        return [self._descriptors[key] for key in sorted(self._descriptors)]

    def save_json(self, path: str | Path) -> Path:
        """Persist the registry as JSON."""
        target = Path(path)
        snapshot = AgentRegistrySnapshot(descriptors=self.list_descriptors())
        target.write_text(
            json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return target

    @classmethod
    def load_json(cls, path: str | Path) -> "AgentRegistry":
        """Load a registry snapshot from JSON."""
        source = Path(path)
        snapshot = AgentRegistrySnapshot.model_validate_json(source.read_text(encoding="utf-8"))
        return cls(snapshot.descriptors)
