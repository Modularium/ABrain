"""Manage federated ABrain nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable

import httpx

from core.model_context import ModelContext


@dataclass
class FederatedNode:
    """Information about a remote ABrain instance."""

    name: str
    base_url: str
    last_seen: datetime = field(default_factory=datetime.utcnow)
    tasks_sent: int = 0
    failure_count: int = 0


class FederationManagerService:
    """Register and dispatch tasks to federated nodes."""

    def __init__(self) -> None:
        self.nodes: Dict[str, FederatedNode] = {}
        self._rr: Iterable[str] | None = None

    def register_node(self, name: str, base_url: str) -> None:
        self.nodes[name] = FederatedNode(name, base_url.rstrip("/"))
        self._rr = None

    def remove_node(self, name: str) -> None:
        self.nodes.pop(name, None)

    def heartbeat(self, name: str) -> None:
        if name in self.nodes:
            self.nodes[name].last_seen = datetime.utcnow()

    def list_nodes(self) -> Dict[str, FederatedNode]:
        self._cleanup()
        return self.nodes

    def _select_node(self) -> FederatedNode:
        self._cleanup()
        if not self.nodes:
            raise ValueError("no nodes registered")
        if not self._rr or all(n not in self.nodes for n in self._rr):
            self._rr = list(self.nodes)
        # pick node with least tasks
        candidate = min(self.nodes.values(), key=lambda n: n.tasks_sent)
        return candidate

    def dispatch(self, node_name: str | None, ctx: ModelContext) -> ModelContext:
        node = self.nodes.get(node_name) if node_name else self._select_node()
        if not node:
            raise ValueError(f"node {node_name} not registered")
        try:
            with httpx.Client() as client:
                resp = client.post(
                    f"{node.base_url}/dispatch",
                    json=ctx.model_dump(),
                    timeout=10,
                )
                resp.raise_for_status()
                node.tasks_sent += 1
                return ModelContext(**resp.json())
        except Exception:
            node.failure_count += 1
            raise

    def _cleanup(self) -> None:
        ttl = timedelta(seconds=60)
        now = datetime.utcnow()
        for name, node in list(self.nodes.items()):
            if now - node.last_seen > ttl:
                self.nodes.pop(name)
