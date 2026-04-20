"""OpenAPI-facing request and response models for the canonical API gateway."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.approval.models import ApprovalRequest
from core.audit.trace_models import (
    ExplainabilityRecord,
    ReplayDescriptor,
    ReplayStepInput,
    SpanRecord,
    TraceRecord,
    TraceSnapshot,
)
from core.decision.agent_descriptor import AgentDescriptor
from core.decision.agent_quality import AgentQualitySummary
from core.decision.plan_models import ExecutionPlan
from core.decision.routing_engine import RoutingDecision
from core.decision.strategy_decision import StrategyDecision
from core.execution.adapters.base import ExecutionResult
from core.execution.provider_capabilities import ExecutionCapabilities
from core.governance.policy_models import PolicyDecision
from core.orchestration.result_aggregation import PlanExecutionResult, PlanExecutionState

API_DESCRIPTION = """
ABrain exposes one canonical external HTTP surface through the existing `api_gateway`.

The supported browser-facing developer interface is the `/control-plane/*` route family:

- inspect agents, traces, explainability, plans, approvals and governance
- launch tasks and plans through the same canonical `services/core.py` paths used by CLI and MCP
- test flows interactively through `/docs`, `/redoc` and `/openapi.json`

Surface boundaries:

- Use HTTP API when you want browser-visible docs, typed JSON requests and service-to-service integration.
- Use MCP when you need a small AI-tool surface over stdio/JSON-RPC.
- Use CLI when you are operating a local checkout and want fast operator/developer control.

Historical, compatibility or internal helper routes remain in the gateway for runtime compatibility where needed,
but they are intentionally omitted from the public OpenAPI surface to avoid parallel API truths.
""".strip()

OPENAPI_TAGS = [
    {
        "name": "Control Plane",
        "description": "Overview and top-level inspection of the canonical ABrain control plane.",
    },
    {
        "name": "Agents",
        "description": "Read-only visibility into the agent catalog projected from canonical core state.",
    },
    {
        "name": "Traces",
        "description": "Trace and explainability inspection backed by the canonical audit store.",
    },
    {
        "name": "Approvals",
        "description": "Human-in-the-loop approval listing and decision endpoints.",
    },
    {
        "name": "Plans",
        "description": "Plan execution launch and recent plan state inspection.",
    },
    {
        "name": "Tasks",
        "description": "Single-task launch through the canonical core execution pipeline.",
    },
    {
        "name": "Routing",
        "description": "Read-only inspection of the canonical routing-model catalog with lineage and energy metadata.",
    },
    {
        "name": "Reasoning",
        "description": (
            "ABrain V2 Domain Reasoning surface. Input-driven, deterministic reasoners "
            "interpret external-system context snapshots (starting with LabOS) and emit "
            "Response Shape V2 recommendations without executing anything."
        ),
    },
]


class ApiErrorResponse(BaseModel):
    """Structured HTTP error payload documented by the public gateway."""

    model_config = ConfigDict(extra="forbid")

    detail: str = Field(description="Human-readable error summary returned by the gateway.")


class ControlPlaneRunRequest(BaseModel):
    """Canonical task or plan launch payload for the control plane API."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "task_type": "system_status",
                "description": "Check current system health",
                "task_id": "task-system-status-demo",
                "input_data": {"path": "services/core.py"},
                "options": {"timeout": 5},
            }
        },
    )

    task_type: str = Field(
        min_length=1,
        description="Canonical task type consumed by `services/core.py`.",
        examples=["system_status", "workflow_automation", "code_review"],
    )
    description: str | None = Field(
        default=None,
        max_length=4096,
        description="Optional short natural-language description for operator context and audit trails.",
    )
    task_id: str | None = Field(
        default=None,
        max_length=128,
        description="Optional stable caller-supplied task identifier.",
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Opaque task input forwarded to the canonical core path.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution hints forwarded as `preferences.execution_hints`.",
    )

    def to_core_payload(self) -> dict[str, Any]:
        payload = dict(self.input_data)
        payload["task_type"] = self.task_type
        if self.description:
            payload["description"] = self.description
        if self.task_id:
            payload["task_id"] = self.task_id
        if self.options:
            payload["preferences"] = {"execution_hints": dict(self.options)}
        return payload


class ApprovalDecisionRequest(BaseModel):
    """Human approval action submitted through the control plane API."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "decided_by": "developer@example",
                "comment": "Risk understood and approved.",
                "rating": 0.9,
            }
        },
    )

    decided_by: str = Field(
        default="control-plane",
        min_length=1,
        max_length=128,
        description="Stable identifier of the human or system recording the approval decision.",
    )
    comment: str | None = Field(
        default=None,
        max_length=2048,
        description="Optional decision comment stored in approval history.",
    )
    rating: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional normalized confidence or review rating between 0.0 and 1.0.",
    )


class AgentCatalogEntry(BaseModel):
    """Externally documented agent catalog projection."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    display_name: str
    capabilities: list[str] = Field(default_factory=list)
    source_type: str | None = None
    execution_kind: str | None = None
    availability: str | None = None
    trust_level: str | None = None
    quality: AgentQualitySummary | None = None
    execution_capabilities: ExecutionCapabilities | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentCatalogResponse(BaseModel):
    """Response wrapper for the projected agent catalog."""

    model_config = ConfigDict(extra="forbid")

    agents: list[AgentCatalogEntry] = Field(default_factory=list)


class GovernanceDecisionEntry(BaseModel):
    """Derived governance decision entry exposed by the control plane."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    task_id: str | None = None
    workflow_name: str | None = None
    status: str | None = None
    effect: str | None = None
    selected_agent_id: str | None = None
    matched_policy_ids: list[str] = Field(default_factory=list)
    winning_policy_rule: str | None = None
    approval_required: bool = False
    started_at: str | None = None
    ended_at: str | None = None


class GovernanceListResponse(BaseModel):
    """Response wrapper for recent governance decisions."""

    model_config = ConfigDict(extra="forbid")

    governance: list[GovernanceDecisionEntry] = Field(default_factory=list)


class PlanSummary(BaseModel):
    """Recent plan projection exposed by the control plane list view."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    trace_id: str | None = None
    workflow_name: str
    task_id: str | None = None
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    pending_approval_id: str | None = None
    policy_effect: str | None = None
    plan: ExecutionPlan | dict[str, Any] | None = None
    state: PlanExecutionState | dict[str, Any] | None = None


class PlanListResponse(BaseModel):
    """Response wrapper for recent plan runs."""

    model_config = ConfigDict(extra="forbid")

    plans: list[PlanSummary] = Field(default_factory=list)


class TraceListResponse(BaseModel):
    """Response wrapper for recent trace summaries."""

    model_config = ConfigDict(extra="forbid")

    traces: list[TraceRecord] = Field(default_factory=list)


class TraceDetailResponse(BaseModel):
    """Response wrapper for a single trace snapshot."""

    model_config = ConfigDict(extra="forbid")

    trace: TraceSnapshot | None = None


class ExplainabilityResponse(BaseModel):
    """Response wrapper for explainability records tied to one trace."""

    model_config = ConfigDict(extra="forbid")

    explainability: list[ExplainabilityRecord] = Field(default_factory=list)


class ApprovalListResponse(BaseModel):
    """Response wrapper for currently pending approvals."""

    model_config = ConfigDict(extra="forbid")

    approvals: list[ApprovalRequest] = Field(default_factory=list)


class ApprovalDecisionResponse(BaseModel):
    """Response returned after approving or rejecting a paused plan step."""

    model_config = ConfigDict(extra="forbid")

    approval: ApprovalRequest
    plan: ExecutionPlan | dict[str, Any] | None = None
    result: PlanExecutionResult
    trace: TraceRecord


class ControlPlaneLayerStatus(BaseModel):
    """Availability status of one named control-plane layer."""

    model_config = ConfigDict(extra="forbid")

    name: str
    status: str


class GovernanceStateSummary(BaseModel):
    """Lightweight governance configuration metadata."""

    model_config = ConfigDict(extra="forbid")

    policy_path: str | None = None
    engine: str | None = None
    registry: str | None = None


class ControlPlaneSystemSummary(BaseModel):
    """Top-level system metadata returned by the control-plane overview."""

    model_config = ConfigDict(extra="forbid")

    name: str
    layers: list[ControlPlaneLayerStatus] = Field(default_factory=list)
    governance: GovernanceStateSummary
    warnings: list[str] = Field(default_factory=list)


class ControlPlaneOverviewCounts(BaseModel):
    """Summary counts exposed by the overview endpoint."""

    model_config = ConfigDict(extra="forbid")

    agent_count: int
    pending_approvals: int
    recent_traces: int
    recent_plans: int
    recent_governance_events: int


class HealthAttentionItem(BaseModel):
    """A single operator-relevant attention item in the health summary."""

    model_config = ConfigDict(extra="forbid")

    level: str = Field(description="'warning' or 'info'")
    label: str
    detail: str


class ControlPlaneHealthSummary(BaseModel):
    """Derived health summary computed from canonical control-plane signals.

    Computed inside ``services/core._compute_health_summary`` — no new IO.
    """

    model_config = ConfigDict(extra="forbid")

    overall: str = Field(description="'healthy', 'attention', or 'degraded'")
    degraded_agent_count: int = 0
    offline_agent_count: int = 0
    paused_plan_count: int = 0
    failed_plan_count: int = 0
    pending_approval_count: int = 0
    has_warnings: bool = False
    attention_items: list[HealthAttentionItem] = Field(default_factory=list)


class ControlPlaneOverviewResponse(BaseModel):
    """Canonical overview response for the external control plane API."""

    model_config = ConfigDict(extra="forbid")

    system: ControlPlaneSystemSummary
    summary: ControlPlaneOverviewCounts
    health: ControlPlaneHealthSummary
    agents: list[AgentCatalogEntry] = Field(default_factory=list)
    pending_approvals: list[ApprovalRequest] = Field(default_factory=list)
    recent_traces: list[TraceRecord] = Field(default_factory=list)
    recent_plans: list[PlanSummary] = Field(default_factory=list)
    recent_governance: list[GovernanceDecisionEntry] = Field(default_factory=list)


class TaskRunResponse(BaseModel):
    """Canonical single-task execution response."""

    model_config = ConfigDict(extra="forbid")

    status: str | None = Field(
        default=None,
        description="Top-level terminal state when the run is denied or paused before normal completion.",
    )
    decision: RoutingDecision | None = None
    execution: ExecutionResult | None = None
    created_agent: AgentDescriptor | None = None
    feedback: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    governance: PolicyDecision | None = None
    approval: ApprovalRequest | None = None
    plan: ExecutionPlan | dict[str, Any] | None = None
    result: PlanExecutionResult | None = None
    trace: TraceRecord


class PlanRunResponse(BaseModel):
    """Canonical multi-step plan execution response."""

    model_config = ConfigDict(extra="forbid")

    plan: ExecutionPlan
    result: PlanExecutionResult
    trace: TraceRecord


class StrategyDecisionResponse(BaseModel):
    """Strategy decision response emitted by ``POST /control-plane/decide``.

    Observable-only: no execution is attempted.  ``trace`` mirrors the
    ``TraceContext.summary()`` payload returned by ``services.core``.
    """

    model_config = ConfigDict(extra="forbid")

    decision: StrategyDecision
    trace: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Routing-model catalog (read-only mirror of `services.core.get_routing_models`)
# ---------------------------------------------------------------------------


class RoutingQuantizationEntry(BaseModel):
    """Quantization lineage projection for one catalog entry."""

    model_config = ConfigDict(extra="forbid")

    method: str
    bits: int
    baseline_model_id: str
    quality_delta_vs_baseline: float | None = None
    evaluated_on: str | None = None


class RoutingDistillationEntry(BaseModel):
    """Distillation lineage projection for one catalog entry."""

    model_config = ConfigDict(extra="forbid")

    teacher_model_id: str
    method: str
    quality_delta_vs_teacher: float | None = None
    evaluated_on: str | None = None


class RoutingEnergyProfileEntry(BaseModel):
    """Per-model energy profile declaration.

    Mirrors ``core.decision.energy_report.EnergyProfile`` — ``source`` is
    the declared fidelity (``measured`` / ``vendor_spec`` / ``estimated``).
    ``None`` at the outer level means the catalog has not registered
    wattage yet (honesty rule — operators register real profiles at
    runtime, catalog ships with ``None``).
    """

    model_config = ConfigDict(extra="forbid")

    avg_power_watts: float = Field(ge=0.0)
    source: str


class RoutingModelEntry(BaseModel):
    """One routing-catalog entry projected for external consumers.

    Lineage and energy fields use the "always emit, null when absent"
    convention mirroring the auditor span schema and the CLI surface.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str
    display_name: str
    provider: str
    tier: str
    purposes: list[str] = Field(default_factory=list)
    context_window: int | None = None
    cost_per_1k_tokens: float | None = None
    p95_latency_ms: int | None = None
    supports_tool_use: bool
    supports_structured_output: bool
    is_available: bool
    quantization: RoutingQuantizationEntry | None = None
    distillation: RoutingDistillationEntry | None = None
    energy_profile: RoutingEnergyProfileEntry | None = None


class RoutingModelsFilters(BaseModel):
    """Echoed filter parameters applied by the service."""

    model_config = ConfigDict(extra="forbid")

    tier: str | None = None
    provider: str | None = None
    purpose: str | None = None
    available_only: bool = False


class RoutingModelsResponse(BaseModel):
    """Read-only routing-catalog response envelope."""

    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    catalog_size: int = Field(ge=0)
    filters: RoutingModelsFilters
    tiers: dict[str, int] = Field(default_factory=dict)
    providers: dict[str, int] = Field(default_factory=dict)
    purposes: dict[str, int] = Field(default_factory=dict)
    models: list[RoutingModelEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# LabOS reasoning (read-only mirror of `services.core.run_labos_reasoning`).
# Kept as a permissive dict pass-through so the Response Shape V2 payload is
# forwarded verbatim without a second typed projection.
# ---------------------------------------------------------------------------


class LabOsReasoningRequest(BaseModel):
    """Request body wrapper carrying a LabOS context snapshot.

    The concrete per-field validation lives in the canonical reasoner
    (``core.reasoning.labos.schemas.LabOsContext``).  The gateway wrapper
    only pins that callers send a JSON object under ``context``.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "context": {
                    "reactors": [
                        {"reactor_id": "R1", "status": "warning"}
                    ]
                }
            }
        },
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "LabOS snapshot to reason over. Forwarded verbatim to "
            "`services.core.run_labos_reasoning`. The reasoner validates "
            "the concrete shape; invalid payloads surface as HTTP 400 "
            "`invalid_context` with the pydantic error detail."
        ),
    )
