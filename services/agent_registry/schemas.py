"""Data models for the Agent Registry API."""

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field
from uuid import uuid4

from core.decision.agent_descriptor import (
    AgentAvailability,
    AgentCostProfile,
    AgentDescriptor,
    AgentExecutionKind,
    AgentLatencyProfile,
    AgentSourceType,
    AgentTrustLevel,
)


def _cost_profile_from_token_cost(value: float) -> AgentCostProfile:
    if value <= 0:
        return AgentCostProfile.UNKNOWN
    if value < 0.001:
        return AgentCostProfile.LOW
    if value < 0.01:
        return AgentCostProfile.MEDIUM
    return AgentCostProfile.HIGH


def _latency_profile_from_seconds(value: float) -> AgentLatencyProfile:
    if value <= 0:
        return AgentLatencyProfile.UNKNOWN
    if value <= 2:
        return AgentLatencyProfile.INTERACTIVE
    if value <= 10:
        return AgentLatencyProfile.BACKGROUND
    return AgentLatencyProfile.BATCH


def _coerce_enum(value: Any, enum_cls, default):
    try:
        return enum_cls(value)
    except Exception:
        return default


class AgentInfo(BaseModel):
    """Information about a registered agent."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    url: str
    domain: str | None = None
    version: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    role: str | None = None
    traits: Dict[str, Any] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    estimated_cost_per_token: float = 0.0
    avg_response_time: float = 0.0
    load_factor: float = 0.0

    def to_descriptor(self) -> AgentDescriptor:
        """Map the service-facing model into the canonical descriptor."""
        return AgentDescriptor(
            agent_id=self.id,
            display_name=self.name,
            source_type=AgentSourceType.NATIVE,
            execution_kind=AgentExecutionKind.HTTP_SERVICE,
            capabilities=self.capabilities,
            trust_level=_coerce_enum(
                self.traits.get("trust_level", AgentTrustLevel.SANDBOXED),
                AgentTrustLevel,
                AgentTrustLevel.SANDBOXED,
            ),
            cost_profile=_cost_profile_from_token_cost(self.estimated_cost_per_token),
            latency_profile=_latency_profile_from_seconds(self.avg_response_time),
            availability=_coerce_enum(
                self.traits.get("availability", AgentAvailability.UNKNOWN),
                AgentAvailability,
                AgentAvailability.UNKNOWN,
            ),
            editable_in_flowise=bool(self.traits.get("editable_in_flowise", False)),
            metadata={
                "url": self.url,
                "domain": self.domain,
                "version": self.version,
                "role": self.role,
                "traits": dict(self.traits),
                "skills": list(self.skills),
                "estimated_cost_per_token": self.estimated_cost_per_token,
                "avg_response_time": self.avg_response_time,
                "load_factor": self.load_factor,
            },
        )

    @classmethod
    def from_descriptor(cls, descriptor: AgentDescriptor) -> "AgentInfo":
        """Map a canonical descriptor into the legacy registry schema."""
        return cls(
            id=descriptor.agent_id,
            name=descriptor.display_name,
            url=str(
                descriptor.metadata.get("url")
                or descriptor.metadata.get("endpoint_url")
                or f"descriptor://{descriptor.agent_id}"
            ),
            domain=str(descriptor.metadata.get("domain") or "") or None,
            version=str(descriptor.metadata.get("version") or "") or None,
            capabilities=list(descriptor.capabilities),
            role=str(descriptor.metadata.get("role") or "") or None,
            traits={
                "source_type": descriptor.source_type.value,
                "execution_kind": descriptor.execution_kind.value,
                "trust_level": descriptor.trust_level.value,
                "availability": descriptor.availability.value,
                "editable_in_flowise": descriptor.editable_in_flowise,
                **(
                    descriptor.metadata.get("traits")
                    if isinstance(descriptor.metadata.get("traits"), dict)
                    else {}
                ),
            },
            skills=[
                item.strip()
                for item in descriptor.metadata.get("skills", [])
                if isinstance(item, str) and item.strip()
            ],
            estimated_cost_per_token=float(descriptor.metadata.get("estimated_cost_per_token", 0.0)),
            avg_response_time=float(descriptor.metadata.get("avg_response_time", 0.0)),
            load_factor=float(descriptor.metadata.get("load_factor", 0.0)),
        )


class AgentList(BaseModel):
    agents: List[AgentInfo]
