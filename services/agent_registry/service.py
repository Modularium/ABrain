"""Agent registry logic."""

from typing import Dict, List

from core.decision.agent_descriptor import AgentDescriptor

from .schemas import AgentInfo
from core.metrics_utils import TASKS_PROCESSED


class AgentRegistryService:
    """Maintain a list of available agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentInfo] = {}
        self._status: Dict[str, Dict[str, float | int | bool]] = {}

    def list_agents(self) -> List[AgentInfo]:
        """Return registered agents."""
        TASKS_PROCESSED.labels("agent_registry").inc()
        return list(self._agents.values())

    def register_agent(self, info: AgentInfo) -> None:
        """Register a new agent."""
        self._agents[info.id] = info
        TASKS_PROCESSED.labels("agent_registry").inc()

    def register_descriptor(self, descriptor: AgentDescriptor) -> AgentDescriptor:
        """Register a canonical descriptor through the existing service store."""
        info = AgentInfo.from_descriptor(descriptor)
        self.register_agent(info)
        return info.to_descriptor()

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Return a single agent by id."""
        TASKS_PROCESSED.labels("agent_registry").inc()
        return self._agents.get(agent_id)

    def get_descriptor(self, agent_id: str) -> AgentDescriptor | None:
        """Return a canonical descriptor by id."""
        info = self.get_agent(agent_id)
        if info is None:
            return None
        return info.to_descriptor()

    def list_descriptors(self) -> List[AgentDescriptor]:
        """Return all registered agents as canonical descriptors."""
        return [info.to_descriptor() for info in self.list_agents()]

    def update_status(self, name: str, status: Dict[str, float | int | bool]) -> None:
        """Update status info for an agent."""
        self._status[name] = status

    def get_status(self, name: str) -> Dict[str, float | int | bool] | None:
        """Return current status for agent."""
        return self._status.get(name)
