"""Canonical schemas for LabOS domain reasoning (V2).

Two sides:

* **Input** — :class:`LabOsContext`: a snapshot the caller assembles
  from LabOS MCP output.  ABrain does not fetch LabOS state; it only
  interprets the snapshot it is given.  Every section is optional so
  callers can drive partial use cases (e.g. only reactors for the
  daily overview).
* **Output** — :class:`DomainReasoningResponse`: the Response Shape
  V2 every use case returns.  Operator-facing, control-surface-
  compatible, and deterministic on fixed input.

All schemas are strict pydantic models (``extra="forbid"``) so typos
in caller payloads surface as ``ValidationError`` instead of silent
drops.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------


class PriorityBucket(str, Enum):
    """Coarse priority bucket for prioritised entities.

    Stable order — UI rendering, CLI summaries and recommendation
    grouping rely on the enum's declared sequence.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOMINAL = "nominal"


class HealthStatus(str, Enum):
    """Normalised health/status label for reactors/nodes/assets."""

    NOMINAL = "nominal"
    ATTENTION = "attention"
    WARNING = "warning"
    INCIDENT = "incident"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk level ABrain recognises in LabOS actions.

    Mirrors the common ``low/medium/high/critical`` convention used by
    LabOS' action catalogue; ABrain never invents new risk levels.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentSeverity(str, Enum):
    """Severity levels ABrain recognises on LabOS incidents."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DeferralReason(str, Enum):
    """Why ABrain surfaced an action as deferred rather than actionable."""

    MISSING_ACTION_CATALOG_ENTRY = "missing_action_catalog_entry"
    REQUIRES_APPROVAL = "requires_approval"
    SAFETY_CONTEXT = "safety_context"
    UNHEALTHY_TARGET = "unhealthy_target"


# ---------------------------------------------------------------------------
# Input — LabOS context snapshot
# ---------------------------------------------------------------------------


class LabOsReactor(BaseModel):
    """Normalised reactor entry (subset of the LabOS digital twin)."""

    model_config = ConfigDict(extra="forbid")

    reactor_id: str = Field(min_length=1, max_length=128)
    display_name: str | None = None
    status: HealthStatus = HealthStatus.UNKNOWN
    open_incident_count: int = Field(default=0, ge=0)
    last_update: datetime | None = None
    attention_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LabOsIncident(BaseModel):
    """Normalised incident entry (subset of the LabOS incident store)."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1, max_length=128)
    severity: IncidentSeverity
    status: str = Field(min_length=1, max_length=64)
    reactor_id: str | None = None
    asset_id: str | None = None
    opened_at: datetime | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        # LabOS statuses vary; treat anything that is not closed/resolved as open.
        return self.status.lower() not in {"closed", "resolved", "acknowledged"}


class LabOsMaintenanceItem(BaseModel):
    """Normalised maintenance / calibration item."""

    model_config = ConfigDict(extra="forbid")

    maintenance_id: str = Field(min_length=1, max_length=128)
    target_type: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=128)
    kind: str = Field(min_length=1, max_length=64)
    due_at: datetime | None = None
    overdue: bool = False
    risk_level: RiskLevel = RiskLevel.MEDIUM
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LabOsScheduleEntry(BaseModel):
    """Normalised schedule entry."""

    model_config = ConfigDict(extra="forbid")

    schedule_id: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=1, max_length=64)
    next_run_at: datetime | None = None
    last_failure_reason: str | None = None
    consecutive_failures: int = Field(default=0, ge=0)
    blocked: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LabOsCommand(BaseModel):
    """Normalised command record (execution attempt within LabOS)."""

    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(min_length=1, max_length=128)
    status: str = Field(min_length=1, max_length=64)
    target_type: str | None = None
    target_id: str | None = None
    failure_reason: str | None = None
    blocked: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LabOsSafetyAlert(BaseModel):
    """Normalised safety-layer alert."""

    model_config = ConfigDict(extra="forbid")

    alert_id: str = Field(min_length=1, max_length=128)
    severity: IncidentSeverity
    target_type: str | None = None
    target_id: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LabOsActionCatalogEntry(BaseModel):
    """Single action ABrain is allowed to recommend.

    ABrain recommends actions by *name* only.  The caller is expected
    to map these names back to LabOS MCP tool invocations.  ABrain
    never recommends an action whose name is absent from this
    catalogue — the ``no_invented_actions`` invariant is enforced at
    the recommendation layer by a lookup against this dict.
    """

    model_config = ConfigDict(extra="forbid")

    action_name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = False
    allowed_roles: list[str] = Field(default_factory=list)
    guarded_by: list[str] = Field(default_factory=list)
    applicable_target_types: list[str] = Field(default_factory=list)


class LabOsContext(BaseModel):
    """LabOS snapshot ABrain reasons over.

    Every section is optional; reasoners declare which sections they
    actually used via :attr:`DomainReasoningResponse.used_context_sections`.
    """

    model_config = ConfigDict(extra="forbid")

    reactors: list[LabOsReactor] = Field(default_factory=list)
    incidents: list[LabOsIncident] = Field(default_factory=list)
    maintenance: list[LabOsMaintenanceItem] = Field(default_factory=list)
    schedules: list[LabOsScheduleEntry] = Field(default_factory=list)
    commands: list[LabOsCommand] = Field(default_factory=list)
    safety_alerts: list[LabOsSafetyAlert] = Field(default_factory=list)
    action_catalog: list[LabOsActionCatalogEntry] = Field(default_factory=list)
    context_timestamp: datetime | None = None

    @field_validator("action_catalog")
    @classmethod
    def _validate_unique_action_names(
        cls, entries: list[LabOsActionCatalogEntry]
    ) -> list[LabOsActionCatalogEntry]:
        seen: set[str] = set()
        for entry in entries:
            if entry.action_name in seen:
                raise ValueError(
                    f"action_catalog contains duplicate action_name '{entry.action_name}'"
                )
            seen.add(entry.action_name)
        return entries

    def action_by_name(self, name: str) -> LabOsActionCatalogEntry | None:
        """Look up an action by name; returns ``None`` when absent."""
        for entry in self.action_catalog:
            if entry.action_name == name:
                return entry
        return None


# ---------------------------------------------------------------------------
# Output — Response Shape V2
# ---------------------------------------------------------------------------


class PrioritizedEntity(BaseModel):
    """One prioritised entity from the LabOS snapshot.

    ``priority_rank`` is 1-based and stable within a single response
    (lower is higher priority).  ``priority_bucket`` gives the coarse
    grouping used for rendering.  ``priority_reason`` is a short,
    human-readable justification — it must be populated.
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(min_length=1, max_length=64)
    entity_id: str = Field(min_length=1, max_length=128)
    display_name: str | None = None
    priority_rank: int = Field(ge=1)
    priority_bucket: PriorityBucket
    priority_reason: str = Field(min_length=1)
    contributing_signals: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendedAction(BaseModel):
    """A structured action recommendation.

    ``action_name`` MUST match an entry in
    :attr:`LabOsContext.action_catalog`.  ABrain never recommends an
    action whose name is absent from the catalogue — the invariant
    is enforced at construction time by the recommendation engine.
    """

    model_config = ConfigDict(extra="forbid")

    action_name: str = Field(min_length=1, max_length=128)
    target_entity_type: str = Field(min_length=1, max_length=64)
    target_entity_id: str = Field(min_length=1, max_length=128)
    rationale: str = Field(min_length=1)
    risk_level: RiskLevel
    requires_approval: bool
    priority_bucket: PriorityBucket
    contributing_signals: list[str] = Field(default_factory=list)


class RecommendedCheck(BaseModel):
    """A diagnostic/investigation step (not an executable action)."""

    model_config = ConfigDict(extra="forbid")

    check: str = Field(min_length=1)
    target_entity_type: str | None = None
    target_entity_id: str | None = None
    rationale: str = Field(min_length=1)


class DeferredAction(BaseModel):
    """An action ABrain considered but did not surface as actionable.

    Rendered in the ``blocked_or_deferred_actions`` slot so operators
    see the intent but also see *why* ABrain held it back.  Used for
    missing-catalogue-entry, safety-context and unhealthy-target
    cases.
    """

    model_config = ConfigDict(extra="forbid")

    intended_action: str = Field(min_length=1, max_length=128)
    target_entity_type: str = Field(min_length=1, max_length=64)
    target_entity_id: str = Field(min_length=1, max_length=128)
    deferral_reason: DeferralReason
    detail: str = Field(min_length=1)


class DomainReasoningResponse(BaseModel):
    """ABrain V2 Response Shape for LabOS use cases.

    Stable-schema — every key is always present, lists default to
    ``[]``, and optional fields are ``None`` rather than missing.
    """

    model_config = ConfigDict(extra="forbid")

    reasoning_mode: str = Field(min_length=1, max_length=64)
    summary: str = Field(min_length=1)
    highlights: list[str] = Field(default_factory=list)
    prioritized_entities: list[PrioritizedEntity] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    recommended_checks: list[RecommendedCheck] = Field(default_factory=list)
    approval_required_actions: list[RecommendedAction] = Field(default_factory=list)
    blocked_or_deferred_actions: list[DeferredAction] = Field(default_factory=list)
    used_context_sections: list[str] = Field(default_factory=list)
    trace_metadata: dict[str, Any] = Field(default_factory=dict)
