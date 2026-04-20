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
    CapabilityStatus,
    HealthStatus,
    IncidentSeverity,
    LabOsActionCatalogEntry,
    LabOsCommand,
    LabOsContext,
    LabOsIncident,
    LabOsMaintenanceItem,
    LabOsModule,
    LabOsModuleDependency,
    LabOsReactor,
    LabOsSafetyAlert,
    LabOsScheduleEntry,
    ModuleAutonomyLevel,
    PriorityBucket,
    RiskLevel,
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


@dataclass(frozen=True)
class ModuleHealthView:
    """Per-module derived health projection (RobotOps V1).

    Effective status is the LabOS-declared status escalated by
    surrounding signals (safety alert, missing/degraded critical
    capability, overdue maintenance, explicit ``offline`` /
    ``disabled`` / ``maintenance_mode`` flags).  ABrain never
    downgrades the LabOS-declared status.
    """

    module: LabOsModule
    open_incident_count: int
    worst_incident_severity: IncidentSeverity | None
    has_overdue_maintenance: bool
    has_safety_alert: bool
    missing_critical_capabilities: tuple[str, ...]
    degraded_critical_capabilities: tuple[str, ...]
    has_blocked_dependency: bool
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

    modules_by_id: dict[str, LabOsModule] = field(default_factory=dict)
    module_health: dict[str, ModuleHealthView] = field(default_factory=dict)
    modules_by_class: dict[str, list[str]] = field(default_factory=dict)
    module_dependencies: list[LabOsModuleDependency] = field(default_factory=list)
    blocked_dependencies: list[LabOsModuleDependency] = field(default_factory=list)

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


def _escalate_module_status(
    base: HealthStatus,
    *,
    worst_severity: IncidentSeverity | None,
    has_overdue_maintenance: bool,
    has_safety_alert: bool,
    offline: bool,
    disabled: bool,
    maintenance_mode: bool,
    has_missing_critical: bool,
    has_degraded_critical: bool,
) -> HealthStatus:
    """Escalate a module's declared status from surrounding RobotOps signals.

    ABrain promotes ``unknown``/``nominal`` up when evidence warrants
    it but never demotes an already-declared status.  ``offline`` and
    ``disabled`` outrank all reactor-style escalation paths.
    """
    if offline:
        candidate = HealthStatus.OFFLINE
    elif has_safety_alert or worst_severity == IncidentSeverity.CRITICAL:
        candidate = HealthStatus.INCIDENT
    elif has_missing_critical:
        candidate = HealthStatus.WARNING
    elif worst_severity == IncidentSeverity.WARNING or has_overdue_maintenance:
        candidate = HealthStatus.WARNING
    elif disabled or maintenance_mode or has_degraded_critical:
        candidate = HealthStatus.ATTENTION
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
    promoted = base
    if rank[candidate] > rank[promoted]:
        promoted = candidate
    return promoted


def _critical_capability_flags(
    module: LabOsModule,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split a module's capabilities into missing / degraded critical sets.

    A capability is treated as critical when ``critical=True`` OR its
    ``risk_level`` is ``high``/``critical``.  Non-critical capabilities
    do not escalate the module's health.
    """
    missing: list[str] = []
    degraded: list[str] = []
    for cap in module.capabilities:
        is_critical = cap.critical or cap.risk_level in {
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        }
        if not is_critical:
            continue
        if cap.status == CapabilityStatus.MISSING:
            missing.append(cap.capability_name)
        elif cap.status == CapabilityStatus.DEGRADED:
            degraded.append(cap.capability_name)
    return tuple(missing), tuple(degraded)


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

    # ---- modules (RobotOps V1)
    incidents_by_module: dict[str, list[LabOsIncident]] = {}
    maintenance_overdue_module_ids: set[str] = set()
    for incident in ctx.incidents:
        # Incidents carry asset/reactor refs today; if a caller maps a
        # module-scoped incident here, bucket it by asset_id.
        target_module = incident.metadata.get("module_id") if isinstance(
            incident.metadata, dict
        ) else None
        if isinstance(target_module, str) and target_module:
            incidents_by_module.setdefault(target_module, []).append(incident)
    for item in ctx.maintenance:
        if item.target_type == "module" and item.overdue:
            maintenance_overdue_module_ids.add(item.target_id)

    if ctx.modules:
        result.used_context_sections.append("modules")
    for module in ctx.modules:
        result.modules_by_id[module.module_id] = module
        result.modules_by_class.setdefault(module.module_class, []).append(
            module.module_id
        )

    if ctx.module_dependencies:
        result.used_context_sections.append("module_dependencies")
    for dep in ctx.module_dependencies:
        result.module_dependencies.append(dep)
        if dep.blocked:
            result.blocked_dependencies.append(dep)

    blocked_sources = {dep.source_module_id for dep in result.blocked_dependencies}

    for module_id, module in result.modules_by_id.items():
        module_incidents = [
            incident
            for incident in incidents_by_module.get(module_id, [])
            if incident.is_open
        ]
        worst = _worst_severity(module_incidents)
        has_overdue = module_id in maintenance_overdue_module_ids
        has_safety = ("module", module_id) in result.safety_alerts_by_target
        missing_critical, degraded_critical = _critical_capability_flags(module)
        has_blocked_dep = module_id in blocked_sources

        effective = _escalate_module_status(
            module.status,
            worst_severity=worst,
            has_overdue_maintenance=has_overdue,
            has_safety_alert=has_safety,
            offline=module.offline,
            disabled=module.disabled,
            maintenance_mode=module.maintenance_mode,
            has_missing_critical=bool(missing_critical),
            has_degraded_critical=bool(degraded_critical),
        )

        result.module_health[module_id] = ModuleHealthView(
            module=module,
            open_incident_count=module.open_incident_count or len(module_incidents),
            worst_incident_severity=worst,
            has_overdue_maintenance=has_overdue,
            has_safety_alert=has_safety,
            missing_critical_capabilities=missing_critical,
            degraded_critical_capabilities=degraded_critical,
            has_blocked_dependency=has_blocked_dep,
            effective_status=effective,
            health_bucket=_bucket_from_health(effective),
        )

    # ---- action catalogue
    if ctx.action_catalog:
        result.used_context_sections.append("action_catalog")
    for entry in ctx.action_catalog:
        result.action_catalog_by_name[entry.action_name] = entry

    return result
