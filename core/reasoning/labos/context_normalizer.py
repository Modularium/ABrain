"""Normalise a :class:`LabOsContext` into reasoning-friendly buckets.

The normaliser is a pure function: it does not fetch anything, does
not mutate the input, and produces a :class:`NormalizedLabOsContext`
that the priority and recommendation engines consume.  Normalisation
is strictly interpretation — we never synthesise entities that are
not present in the input snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import (
    HealthStatus,
    IncidentSeverity,
    LabOsActionCatalogEntry,
    LabOsCommand,
    LabOsContext,
    LabOsIncident,
    LabOsMaintenanceItem,
    LabOsReactor,
    LabOsSafetyAlert,
    LabOsScheduleEntry,
    PriorityBucket,
)


@dataclass(frozen=True)
class ReactorHealthView:
    """Per-reactor derived health projection."""

    reactor: LabOsReactor
    open_incident_count: int
    worst_incident_severity: IncidentSeverity | None
    has_overdue_maintenance: bool
    has_safety_alert: bool
    effective_status: HealthStatus
    health_bucket: PriorityBucket


@dataclass
class NormalizedLabOsContext:
    """Reasoning-friendly projection of :class:`LabOsContext`.

    All lists are stable-ordered by input position so reasoners stay
    deterministic on identical input snapshots.
    """

    reactors_by_id: dict[str, LabOsReactor] = field(default_factory=dict)
    reactor_health: dict[str, ReactorHealthView] = field(default_factory=dict)

    open_incidents: list[LabOsIncident] = field(default_factory=list)
    critical_incidents: list[LabOsIncident] = field(default_factory=list)
    warning_incidents: list[LabOsIncident] = field(default_factory=list)

    overdue_maintenance: list[LabOsMaintenanceItem] = field(default_factory=list)
    due_soon_maintenance: list[LabOsMaintenanceItem] = field(default_factory=list)

    failed_schedules: list[LabOsScheduleEntry] = field(default_factory=list)
    blocked_schedules: list[LabOsScheduleEntry] = field(default_factory=list)

    failed_commands: list[LabOsCommand] = field(default_factory=list)
    blocked_commands: list[LabOsCommand] = field(default_factory=list)

    safety_alerts_by_target: dict[tuple[str, str], list[LabOsSafetyAlert]] = field(
        default_factory=dict
    )

    action_catalog_by_name: dict[str, LabOsActionCatalogEntry] = field(
        default_factory=dict
    )

    used_context_sections: list[str] = field(default_factory=list)


def _bucket_from_health(status: HealthStatus) -> PriorityBucket:
    if status == HealthStatus.INCIDENT:
        return PriorityBucket.CRITICAL
    if status == HealthStatus.WARNING:
        return PriorityBucket.HIGH
    if status == HealthStatus.OFFLINE:
        return PriorityBucket.HIGH
    if status == HealthStatus.ATTENTION:
        return PriorityBucket.MEDIUM
    if status == HealthStatus.NOMINAL:
        return PriorityBucket.NOMINAL
    return PriorityBucket.LOW


def _worst_severity(
    incidents: list[LabOsIncident],
) -> IncidentSeverity | None:
    order = {
        IncidentSeverity.INFO: 0,
        IncidentSeverity.WARNING: 1,
        IncidentSeverity.CRITICAL: 2,
    }
    worst: IncidentSeverity | None = None
    for incident in incidents:
        if worst is None or order[incident.severity] > order[worst]:
            worst = incident.severity
    return worst


def _escalate_from_signals(
    base: HealthStatus,
    worst_severity: IncidentSeverity | None,
    has_overdue_maintenance: bool,
    has_safety_alert: bool,
) -> HealthStatus:
    """Escalate a reactor's declared status based on surrounding signals.

    The reactor's declared status from LabOS is authoritative when it
    is already at the same or higher level than the signals imply —
    we never *downgrade* a LabOS-declared status.  We only promote
    ``nominal``/``unknown`` up when surrounding evidence warrants it.
    """

    promoted = base

    if has_safety_alert or worst_severity == IncidentSeverity.CRITICAL:
        candidate = HealthStatus.INCIDENT
    elif worst_severity == IncidentSeverity.WARNING or has_overdue_maintenance:
        candidate = HealthStatus.WARNING
    else:
        candidate = base

    rank = {
        HealthStatus.UNKNOWN: 0,
        HealthStatus.NOMINAL: 1,
        HealthStatus.ATTENTION: 2,
        HealthStatus.WARNING: 3,
        HealthStatus.OFFLINE: 3,
        HealthStatus.INCIDENT: 4,
    }
    if rank[candidate] > rank[promoted]:
        promoted = candidate
    return promoted


def normalize_labos_context(ctx: LabOsContext) -> NormalizedLabOsContext:
    """Produce a :class:`NormalizedLabOsContext` for downstream reasoners."""

    result = NormalizedLabOsContext()

    # ---- reactors
    if ctx.reactors:
        result.used_context_sections.append("reactors")
    for reactor in ctx.reactors:
        result.reactors_by_id[reactor.reactor_id] = reactor

    # ---- incidents
    incidents_by_reactor: dict[str, list[LabOsIncident]] = {}
    if ctx.incidents:
        result.used_context_sections.append("incidents")
    for incident in ctx.incidents:
        if incident.is_open:
            result.open_incidents.append(incident)
            if incident.severity == IncidentSeverity.CRITICAL:
                result.critical_incidents.append(incident)
            elif incident.severity == IncidentSeverity.WARNING:
                result.warning_incidents.append(incident)
        if incident.reactor_id:
            incidents_by_reactor.setdefault(incident.reactor_id, []).append(incident)

    # ---- maintenance / calibration
    maintenance_overdue_by_target: set[tuple[str, str]] = set()
    if ctx.maintenance:
        result.used_context_sections.append("maintenance")
    for item in ctx.maintenance:
        if item.overdue:
            result.overdue_maintenance.append(item)
            maintenance_overdue_by_target.add((item.target_type, item.target_id))
        elif item.due_at is not None:
            result.due_soon_maintenance.append(item)

    # ---- schedules
    if ctx.schedules:
        result.used_context_sections.append("schedules")
    for schedule in ctx.schedules:
        if schedule.consecutive_failures > 0 or (
            schedule.status.lower() == "failed"
        ):
            result.failed_schedules.append(schedule)
        if schedule.blocked:
            result.blocked_schedules.append(schedule)

    # ---- commands
    if ctx.commands:
        result.used_context_sections.append("commands")
    for command in ctx.commands:
        if command.status.lower() in {"failed", "error"} or command.failure_reason:
            result.failed_commands.append(command)
        if command.blocked:
            result.blocked_commands.append(command)

    # ---- safety
    if ctx.safety_alerts:
        result.used_context_sections.append("safety_alerts")
    safety_targets: set[tuple[str, str]] = set()
    for alert in ctx.safety_alerts:
        if alert.target_type and alert.target_id:
            key = (alert.target_type, alert.target_id)
            result.safety_alerts_by_target.setdefault(key, []).append(alert)
            safety_targets.add(key)

    # ---- per-reactor health view
    for reactor_id, reactor in result.reactors_by_id.items():
        reactor_incidents = [
            incident
            for incident in incidents_by_reactor.get(reactor_id, [])
            if incident.is_open
        ]
        worst = _worst_severity(reactor_incidents)
        has_overdue = ("reactor", reactor_id) in maintenance_overdue_by_target
        has_safety = ("reactor", reactor_id) in safety_targets
        effective = _escalate_from_signals(
            reactor.status, worst, has_overdue, has_safety
        )
        result.reactor_health[reactor_id] = ReactorHealthView(
            reactor=reactor,
            open_incident_count=len(reactor_incidents),
            worst_incident_severity=worst,
            has_overdue_maintenance=has_overdue,
            has_safety_alert=has_safety,
            effective_status=effective,
            health_bucket=_bucket_from_health(effective),
        )

    # ---- action catalogue
    if ctx.action_catalog:
        result.used_context_sections.append("action_catalog")
    for entry in ctx.action_catalog:
        result.action_catalog_by_name[entry.action_name] = entry

    return result
