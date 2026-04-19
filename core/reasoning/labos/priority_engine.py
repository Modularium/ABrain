"""Deterministic priority/triage engine for LabOS reasoning.

Rules are intentionally small and explicit; every prioritised entity
carries a :attr:`priority_reason` explaining *why* it landed in its
bucket.  No probabilistic scoring, no opaque weights — when a rule
needs to change, the change lands as a new branch in this module,
not as a tuning parameter.
"""

from __future__ import annotations

from dataclasses import dataclass

from .context_normalizer import NormalizedLabOsContext, ReactorHealthView
from .schemas import (
    IncidentSeverity,
    LabOsIncident,
    LabOsMaintenanceItem,
    LabOsScheduleEntry,
    PrioritizedEntity,
    PriorityBucket,
)


@dataclass(frozen=True)
class _RankedCandidate:
    """Internal work record before we assign stable ranks."""

    entity: PrioritizedEntity
    score: int


_BUCKET_BASE_SCORE: dict[PriorityBucket, int] = {
    PriorityBucket.CRITICAL: 100,
    PriorityBucket.HIGH: 80,
    PriorityBucket.MEDIUM: 60,
    PriorityBucket.LOW: 40,
    PriorityBucket.NOMINAL: 10,
}


def _reactor_candidate(view: ReactorHealthView) -> PrioritizedEntity:
    reasons: list[str] = []
    signals: list[str] = []
    if view.worst_incident_severity == IncidentSeverity.CRITICAL:
        reasons.append("open critical incident")
        signals.append("critical_incident")
    elif view.worst_incident_severity == IncidentSeverity.WARNING:
        reasons.append("open warning incident")
        signals.append("warning_incident")
    if view.has_overdue_maintenance:
        reasons.append("overdue maintenance")
        signals.append("overdue_maintenance")
    if view.has_safety_alert:
        reasons.append("active safety alert")
        signals.append("safety_alert")
    if not reasons:
        reasons.append(f"reactor status {view.effective_status.value}")
        signals.append(f"status_{view.effective_status.value}")
    return PrioritizedEntity(
        entity_type="reactor",
        entity_id=view.reactor.reactor_id,
        display_name=view.reactor.display_name,
        priority_rank=1,  # replaced after global sort
        priority_bucket=view.health_bucket,
        priority_reason="; ".join(reasons),
        contributing_signals=signals,
        metadata={
            "open_incident_count": view.open_incident_count,
            "effective_status": view.effective_status.value,
        },
    )


def _incident_candidate(incident: LabOsIncident) -> PrioritizedEntity:
    if incident.severity == IncidentSeverity.CRITICAL:
        bucket = PriorityBucket.CRITICAL
        reason = "critical incident open"
    elif incident.severity == IncidentSeverity.WARNING:
        bucket = PriorityBucket.HIGH
        reason = "warning incident open"
    else:
        bucket = PriorityBucket.MEDIUM
        reason = "info incident open"
    return PrioritizedEntity(
        entity_type="incident",
        entity_id=incident.incident_id,
        display_name=incident.summary,
        priority_rank=1,
        priority_bucket=bucket,
        priority_reason=reason,
        contributing_signals=[f"incident_severity_{incident.severity.value}"],
        metadata={
            "reactor_id": incident.reactor_id,
            "asset_id": incident.asset_id,
            "severity": incident.severity.value,
        },
    )


def _maintenance_candidate(item: LabOsMaintenanceItem) -> PrioritizedEntity:
    if item.overdue:
        bucket = PriorityBucket.HIGH
        reason = f"{item.kind} overdue"
    else:
        bucket = PriorityBucket.MEDIUM
        reason = f"{item.kind} due"
    if item.risk_level.value in {"high", "critical"}:
        bucket = PriorityBucket.CRITICAL if item.overdue else PriorityBucket.HIGH
        reason = f"{reason} (risk={item.risk_level.value})"
    return PrioritizedEntity(
        entity_type="maintenance",
        entity_id=item.maintenance_id,
        display_name=item.summary,
        priority_rank=1,
        priority_bucket=bucket,
        priority_reason=reason,
        contributing_signals=[
            "maintenance_overdue" if item.overdue else "maintenance_due",
            f"maintenance_kind_{item.kind}",
            f"maintenance_risk_{item.risk_level.value}",
        ],
        metadata={
            "target_type": item.target_type,
            "target_id": item.target_id,
            "kind": item.kind,
            "risk_level": item.risk_level.value,
        },
    )


def _schedule_candidate(schedule: LabOsScheduleEntry) -> PrioritizedEntity:
    if schedule.blocked:
        bucket = PriorityBucket.HIGH
        reason = "schedule blocked"
    elif schedule.consecutive_failures >= 3:
        bucket = PriorityBucket.HIGH
        reason = f"schedule failing ({schedule.consecutive_failures} consecutive)"
    elif schedule.consecutive_failures > 0:
        bucket = PriorityBucket.MEDIUM
        reason = "schedule recently failed"
    else:
        bucket = PriorityBucket.LOW
        reason = f"schedule status {schedule.status}"
    signals = [f"schedule_status_{schedule.status.lower()}"]
    if schedule.blocked:
        signals.append("schedule_blocked")
    if schedule.consecutive_failures > 0:
        signals.append(f"schedule_failures_{schedule.consecutive_failures}")
    return PrioritizedEntity(
        entity_type="schedule",
        entity_id=schedule.schedule_id,
        display_name=None,
        priority_rank=1,
        priority_bucket=bucket,
        priority_reason=reason,
        contributing_signals=signals,
        metadata={
            "consecutive_failures": schedule.consecutive_failures,
            "blocked": schedule.blocked,
        },
    )


def _score(entity: PrioritizedEntity) -> int:
    base = _BUCKET_BASE_SCORE[entity.priority_bucket]
    # within a bucket, stable ordering is guided by a small per-signal bump
    bump = 0
    for signal in entity.contributing_signals:
        if signal in {"critical_incident", "safety_alert"}:
            bump += 5
        elif signal in {"overdue_maintenance"}:
            bump += 3
        elif signal == "schedule_blocked":
            bump += 3
    return base + bump


def _assign_ranks(candidates: list[PrioritizedEntity]) -> list[PrioritizedEntity]:
    """Assign 1-based, stable ``priority_rank`` across all candidates."""
    ranked = [_RankedCandidate(entity=c, score=_score(c)) for c in candidates]
    # Stable sort preserves input order for equal scores — keeps the
    # reasoner deterministic on identical input snapshots.
    ranked.sort(key=lambda r: -r.score)
    out: list[PrioritizedEntity] = []
    for position, record in enumerate(ranked, start=1):
        entity = record.entity
        out.append(entity.model_copy(update={"priority_rank": position}))
    return out


def prioritize(
    normalized: NormalizedLabOsContext,
    *,
    include_reactors: bool = True,
    include_incidents: bool = True,
    include_maintenance: bool = True,
    include_schedules: bool = True,
    include_nominal_reactors: bool = False,
) -> list[PrioritizedEntity]:
    """Return a deterministic, fully-ranked list of prioritised entities.

    The ``include_*`` flags let use cases narrow the surface (e.g. the
    incident-review use case only needs incidents and the reactors
    they touch).  ``include_nominal_reactors`` defaults off so callers
    who want an operator-facing "focus list" don't get noise — set to
    ``True`` for the full daily overview.
    """
    candidates: list[PrioritizedEntity] = []

    if include_reactors:
        for view in normalized.reactor_health.values():
            if not include_nominal_reactors and view.health_bucket == PriorityBucket.NOMINAL:
                continue
            candidates.append(_reactor_candidate(view))

    if include_incidents:
        for incident in normalized.open_incidents:
            candidates.append(_incident_candidate(incident))

    if include_maintenance:
        for item in normalized.overdue_maintenance:
            candidates.append(_maintenance_candidate(item))
        for item in normalized.due_soon_maintenance:
            candidates.append(_maintenance_candidate(item))

    if include_schedules:
        for schedule in normalized.failed_schedules:
            candidates.append(_schedule_candidate(schedule))
        for schedule in normalized.blocked_schedules:
            if schedule not in normalized.failed_schedules:
                candidates.append(_schedule_candidate(schedule))

    return _assign_ranks(candidates)
