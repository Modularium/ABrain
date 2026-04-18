"""Phase 6 – Brain v1 B6-S1: State representation and target variable schema.

Defines the immutable input/output types for the Brain decision network:

- ``BrainBudget``        — budget constraints at routing time
- ``BrainPolicySignals`` — governance/policy signals at routing time
- ``BrainAgentSignal``   — per-candidate feature snapshot
- ``BrainState``         — complete network input (task + budget + policy + candidates)
- ``BrainTarget``        — supervision target variables (selection + outcome)
- ``BrainRecord``        — (state, target) training pair with trace provenance

All models use ``extra="forbid"`` so schema drift is caught at construction
rather than silently ignored.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..capabilities import CapabilityRisk

_SCHEMA_VERSION = "1.0"


class BrainBudget(BaseModel):
    """Budget constraints available at routing time."""

    model_config = ConfigDict(extra="forbid")

    budget_usd: float | None = Field(
        default=None,
        ge=0.0,
        description="Remaining USD budget for this task; None = unconstrained",
    )
    time_budget_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Remaining time budget in milliseconds; None = unconstrained",
    )
    max_agents: int = Field(
        default=1,
        ge=1,
        description="Maximum number of agents that may be invoked",
    )


class BrainPolicySignals(BaseModel):
    """Governance and policy signals at routing time."""

    model_config = ConfigDict(extra="forbid")

    has_policy_effect: bool = Field(
        default=False,
        description="True when at least one policy matched for this task",
    )
    approval_required: bool = Field(
        default=False,
        description="True when an approval gate is triggered by policy",
    )
    matched_policy_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of policy IDs that matched this task",
    )


class BrainAgentSignal(BaseModel):
    """Per-candidate feature snapshot for one agent at routing time."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(description="Stable agent identifier")

    # Capability fit
    capability_match_score: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of required capabilities matched",
    )

    # Performance history (from PerformanceHistoryStore or descriptor metadata)
    success_rate: float = Field(ge=0.0, le=1.0, description="Historical success rate")
    avg_latency_s: float = Field(ge=0.0, description="Average latency in seconds")
    avg_cost_usd: float = Field(ge=0.0, description="Average cost per invocation in USD")
    recent_failures: int = Field(ge=0, description="Recent consecutive failure count")
    execution_count: int = Field(ge=0, description="Total observed executions")
    load_factor: float = Field(ge=0.0, le=1.0, description="Current load factor [0,1]")

    # Descriptor-level signals (ordinal-encoded to [0,1])
    trust_level_ord: float = Field(
        ge=0.0, le=1.0,
        description="Trust level ordinal: UNKNOWN=0.0, SANDBOXED=0.33, TRUSTED=0.67, PRIVILEGED=1.0",
    )
    availability_ord: float = Field(
        ge=0.0, le=1.0,
        description="Availability ordinal: OFFLINE=0.0, DEGRADED=0.33, UNKNOWN=0.5, ONLINE=1.0",
    )


class BrainState(BaseModel):
    """Immutable state snapshot fed to the Brain decision network.

    Captures all signals visible *before* the routing decision is finalised:
    task semantics, budget constraints, policy activation, and the ranked
    candidate set with per-agent features.

    Candidates are ordered best-first (by neural policy score when a prior
    ``RoutingDecision`` is available, otherwise by capability match score).
    """

    model_config = ConfigDict(extra="forbid")

    # ---- Task features -------------------------------------------------
    task_type: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    risk: CapabilityRisk = CapabilityRisk.MEDIUM
    required_capabilities: list[str] = Field(default_factory=list)
    num_required_capabilities: int = Field(ge=0)
    description: str | None = None

    # ---- Budget --------------------------------------------------------
    budget: BrainBudget = Field(default_factory=BrainBudget)

    # ---- Policy --------------------------------------------------------
    policy: BrainPolicySignals = Field(default_factory=BrainPolicySignals)

    # ---- Candidate set -------------------------------------------------
    candidates: list[BrainAgentSignal] = Field(default_factory=list)
    num_candidates: int = Field(ge=0)

    # ---- Routing confidence (from prior production pass, if available) --
    routing_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Top-1 neural score from the production routing pass",
    )
    score_gap: float | None = Field(
        default=None, ge=0.0,
        description="Score delta between top-1 and top-2 production candidates",
    )
    confidence_band: str | None = Field(
        default=None,
        description="'high' | 'medium' | 'low' confidence band from production routing",
    )


class BrainTarget(BaseModel):
    """Supervision target variables for Brain training.

    Fields are nullable — an absent value means the signal was not observed
    for this trace (e.g. no approval flow, execution not yet complete).
    """

    model_config = ConfigDict(extra="forbid")

    selected_agent_id: str | None = Field(
        default=None,
        description="Agent ID actually selected by the production router",
    )
    outcome_success: bool | None = Field(
        default=None,
        description="True when the execution succeeded; None = not observed",
    )
    outcome_cost_usd: float | None = Field(
        default=None, ge=0.0,
        description="Actual cost incurred; None = not observed",
    )
    outcome_latency_ms: float | None = Field(
        default=None, ge=0.0,
        description="Actual end-to-end latency in ms; None = not observed",
    )
    approval_required: bool = Field(
        default=False,
        description="True when an approval gate was triggered",
    )
    approval_granted: bool | None = Field(
        default=None,
        description="Approval outcome; None = no approval flow ran",
    )


class BrainRecord(BaseModel):
    """State + target training pair with trace provenance.

    Written by ``BrainRecordBuilder`` (B6-S2+) and consumed by the Brain
    offline trainer.  The ``schema_version`` field allows forward-compatible
    evolution of the record format.
    """

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(description="Originating trace ID")
    workflow_name: str = Field(description="Workflow that produced this trace")
    schema_version: str = Field(default=_SCHEMA_VERSION)
    state: BrainState
    target: BrainTarget
