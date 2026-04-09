"""Deterministic candidate filtering for the decision layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .agent_descriptor import (
    AgentAvailability,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    AgentTrustLevel,
)
from .task_intent import TaskIntent

_TRUST_RANK = {
    AgentTrustLevel.UNKNOWN: 0,
    AgentTrustLevel.SANDBOXED: 1,
    AgentTrustLevel.TRUSTED: 2,
    AgentTrustLevel.PRIVILEGED: 3,
}


class CandidateAgent(BaseModel):
    """Safe candidate that passed deterministic filtering."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    agent: AgentDescriptor
    capability_match_score: float = Field(ge=0.0, le=1.0)
    matched_capabilities: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class RejectedAgent(BaseModel):
    """Candidate rejected by deterministic policy checks."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    reasons: list[str] = Field(default_factory=list)


class CandidateAgentSet(BaseModel):
    """Filter result used as input to the neural policy."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    required_capabilities: list[str] = Field(default_factory=list)
    candidates: list[CandidateAgent] = Field(default_factory=list)
    rejected: list[RejectedAgent] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class CandidateFilter:
    """Apply hard capability and policy checks before neural scoring."""

    def filter_candidates(
        self,
        intent: TaskIntent,
        descriptors: list[AgentDescriptor],
    ) -> CandidateAgentSet:
        candidates: list[CandidateAgent] = []
        rejected: list[RejectedAgent] = []
        minimum_trust_level = self._parse_trust_level(
            intent.execution_hints.get("minimum_trust_level")
        )
        allowed_source_types = self._parse_enum_list(
            intent.execution_hints.get("allowed_source_types"),
            AgentSourceType,
        )
        allowed_execution_kinds = self._parse_enum_list(
            intent.execution_hints.get("allowed_execution_kinds"),
            AgentExecutionKind,
        )
        require_certification = bool(intent.execution_hints.get("requires_certification", False))
        require_human_approval = bool(intent.execution_hints.get("requires_human_approval", False))

        for descriptor in descriptors:
            reasons: list[str] = []
            missing_capabilities = [
                capability_id
                for capability_id in intent.required_capabilities
                if capability_id not in descriptor.capabilities
            ]
            if missing_capabilities:
                reasons.append("missing_capabilities")
            if descriptor.availability == AgentAvailability.OFFLINE:
                reasons.append("agent_offline")
            if minimum_trust_level and not self._trust_satisfies(
                descriptor.trust_level, minimum_trust_level
            ):
                reasons.append("trust_level_too_low")
            if allowed_source_types and descriptor.source_type not in allowed_source_types:
                reasons.append("source_type_not_allowed")
            if allowed_execution_kinds and descriptor.execution_kind not in allowed_execution_kinds:
                reasons.append("execution_kind_not_allowed")
            if require_certification and not bool(descriptor.metadata.get("certified", False)):
                reasons.append("missing_certification")
            if require_human_approval and not bool(
                descriptor.metadata.get("human_approval_ready", False)
            ):
                reasons.append("missing_human_approval")

            if reasons:
                rejected.append(RejectedAgent(agent_id=descriptor.agent_id, reasons=reasons))
                continue

            matched_capabilities = [
                capability_id
                for capability_id in intent.required_capabilities
                if capability_id in descriptor.capabilities
            ]
            capability_match_score = (
                len(matched_capabilities) / len(intent.required_capabilities)
                if intent.required_capabilities
                else 1.0
            )
            candidates.append(
                CandidateAgent(
                    agent=descriptor,
                    capability_match_score=capability_match_score,
                    matched_capabilities=matched_capabilities,
                    diagnostics={
                        "availability": descriptor.availability.value,
                        "trust_level": descriptor.trust_level.value,
                    },
                )
            )

        return CandidateAgentSet(
            required_capabilities=list(intent.required_capabilities),
            candidates=candidates,
            rejected=rejected,
            diagnostics={
                "candidate_count": len(candidates),
                "rejected_count": len(rejected),
            },
        )

    def _parse_trust_level(self, value: Any) -> AgentTrustLevel | None:
        if value is None:
            return None
        try:
            return AgentTrustLevel(str(value))
        except ValueError:
            return None

    def _parse_enum_list(self, value: Any, enum_cls) -> set[Any]:
        if not isinstance(value, list):
            return set()
        parsed: set[Any] = set()
        for item in value:
            try:
                parsed.add(enum_cls(str(item)))
            except ValueError:
                continue
        return parsed

    def _trust_satisfies(
        self,
        candidate_level: AgentTrustLevel,
        minimum_level: AgentTrustLevel,
    ) -> bool:
        return _TRUST_RANK[candidate_level] >= _TRUST_RANK[minimum_level]
