"""Use-case layer for LabOS domain reasoning.

Each use case is an explicit function that:

1. Normalises the input :class:`LabOsContext`.
2. Runs the priority engine with the narrow set of sections it cares
   about.
3. Builds the recommendation bundle via
   :func:`recommendation_engine.build_action` (never directly).
4. Returns a :class:`DomainReasoningResponse` (Response Shape V2).

Use cases never fetch anything themselves, never execute anything,
and never invent action names.  The orchestrator gives them a
snapshot; they produce a deterministic structured answer.
"""

from __future__ import annotations

from .context_normalizer import NormalizedLabOsContext, normalize_labos_context
from .priority_engine import prioritize
from .recommendation_engine import RecommendationBundle, build_action
from .schemas import (
    DomainReasoningResponse,
    HealthStatus,
    IncidentSeverity,
    LabOsContext,
    PriorityBucket,
)

REASONING_MODE_REACTOR_DAILY = "labos_reactor_daily_overview"
REASONING_MODE_INCIDENT_REVIEW = "labos_incident_review"
REASONING_MODE_MAINTENANCE = "labos_maintenance_suggestions"
REASONING_MODE_SCHEDULE_RUNTIME = "labos_schedule_runtime_review"
REASONING_MODE_CROSS_DOMAIN = "labos_cross_domain_overview"


# ---------------------------------------------------------------------------
# Helpers — shared across use cases
# ---------------------------------------------------------------------------


def _fallback_summary(empty_phrase: str, nominal_count: int) -> str:
    if nominal_count:
        return f"{empty_phrase}; {nominal_count} targets nominal"
    return empty_phrase


def _assemble(
    *,
    mode: str,
    summary: str,
    highlights: list[str],
    prioritized,
    bundle: RecommendationBundle,
    normalized: NormalizedLabOsContext,
    trace_metadata: dict,
) -> DomainReasoningResponse:
    return DomainReasoningResponse(
        reasoning_mode=mode,
        summary=summary,
        highlights=highlights,
        prioritized_entities=prioritized,
        recommended_actions=bundle.recommended_actions,
        recommended_checks=[],
        approval_required_actions=bundle.approval_required_actions,
        blocked_or_deferred_actions=bundle.deferred_actions,
        used_context_sections=list(normalized.used_context_sections),
        trace_metadata=trace_metadata,
    )


# ---------------------------------------------------------------------------
# 1. Reactor daily overview
# ---------------------------------------------------------------------------


def reactor_daily_overview(ctx: LabOsContext) -> DomainReasoningResponse:
    """Which reactors need attention today, which are nominal.

    Context sections used: reactors, incidents, maintenance, safety_alerts,
    action_catalog (when actions are recommended).
    """
    normalized = normalize_labos_context(ctx)
    bundle = RecommendationBundle()

    prioritized = prioritize(
        normalized,
        include_reactors=True,
        include_incidents=False,
        include_maintenance=False,
        include_schedules=False,
        include_nominal_reactors=True,
    )

    attention_count = sum(
        1
        for view in normalized.reactor_health.values()
        if view.health_bucket
        in {PriorityBucket.CRITICAL, PriorityBucket.HIGH, PriorityBucket.MEDIUM}
    )
    nominal_count = sum(
        1
        for view in normalized.reactor_health.values()
        if view.health_bucket == PriorityBucket.NOMINAL
    )

    highlights: list[str] = []
    for view in normalized.reactor_health.values():
        if view.effective_status == HealthStatus.INCIDENT:
            highlights.append(
                f"{view.reactor.reactor_id}: incident state "
                f"({view.open_incident_count} open incident"
                f"{'s' if view.open_incident_count != 1 else ''})"
            )
        elif view.effective_status == HealthStatus.WARNING:
            highlights.append(f"{view.reactor.reactor_id}: warning state")
        elif view.effective_status == HealthStatus.OFFLINE:
            highlights.append(f"{view.reactor.reactor_id}: offline")

    # Recommend a review-style action for each critical/high reactor if
    # the catalog exposes one.  Intent name is intentionally generic so
    # callers can choose a LabOS-side name (e.g. "open_reactor_detail").
    for view in normalized.reactor_health.values():
        if view.health_bucket == PriorityBucket.CRITICAL:
            build_action(
                bundle,
                normalized=normalized,
                intended_action="open_reactor_detail",
                target_entity_type="reactor",
                target_entity_id=view.reactor.reactor_id,
                rationale="reactor is in incident state — open detail view",
                priority_bucket=PriorityBucket.CRITICAL,
                contributing_signals=["reactor_critical"],
                allow_on_unsafe_target=True,
            )
        elif view.health_bucket == PriorityBucket.HIGH:
            build_action(
                bundle,
                normalized=normalized,
                intended_action="open_reactor_detail",
                target_entity_type="reactor",
                target_entity_id=view.reactor.reactor_id,
                rationale="reactor needs attention — open detail view",
                priority_bucket=PriorityBucket.HIGH,
                contributing_signals=["reactor_high"],
                allow_on_unsafe_target=True,
            )

    if attention_count == 0:
        summary = _fallback_summary("all reactors nominal", nominal_count)
    else:
        summary = (
            f"{attention_count} reactor(s) need attention; "
            f"{nominal_count} nominal"
        )

    return _assemble(
        mode=REASONING_MODE_REACTOR_DAILY,
        summary=summary,
        highlights=highlights,
        prioritized=prioritized,
        bundle=bundle,
        normalized=normalized,
        trace_metadata={
            "reactor_count": len(normalized.reactor_health),
            "attention_count": attention_count,
            "nominal_count": nominal_count,
        },
    )


# ---------------------------------------------------------------------------
# 2. Incident review
# ---------------------------------------------------------------------------


def incident_review(ctx: LabOsContext) -> DomainReasoningResponse:
    """Which open incidents matter, which reactors/assets are affected."""
    normalized = normalize_labos_context(ctx)
    bundle = RecommendationBundle()

    prioritized = prioritize(
        normalized,
        include_reactors=False,
        include_incidents=True,
        include_maintenance=False,
        include_schedules=False,
    )

    highlights: list[str] = []
    for incident in normalized.critical_incidents:
        highlights.append(
            f"CRITICAL incident {incident.incident_id}"
            + (f" on reactor {incident.reactor_id}" if incident.reactor_id else "")
        )
    for incident in normalized.warning_incidents:
        highlights.append(f"warning incident {incident.incident_id}")

    # Acknowledge recommendations: only for incidents whose severity is
    # not already resolved and where the action catalogue defines an
    # acknowledge intent.
    for incident in normalized.open_incidents:
        intent = (
            "acknowledge_critical_incident"
            if incident.severity == IncidentSeverity.CRITICAL
            else "acknowledge_incident"
        )
        bucket = (
            PriorityBucket.CRITICAL
            if incident.severity == IncidentSeverity.CRITICAL
            else PriorityBucket.HIGH
            if incident.severity == IncidentSeverity.WARNING
            else PriorityBucket.MEDIUM
        )
        build_action(
            bundle,
            normalized=normalized,
            intended_action=intent,
            target_entity_type="incident",
            target_entity_id=incident.incident_id,
            rationale=(
                f"{incident.severity.value} incident is still open"
                + (f" on reactor {incident.reactor_id}" if incident.reactor_id else "")
            ),
            priority_bucket=bucket,
            contributing_signals=[f"incident_severity_{incident.severity.value}"],
            allow_on_unsafe_target=True,
        )

    if not normalized.open_incidents:
        summary = "no open incidents"
    else:
        summary = (
            f"{len(normalized.critical_incidents)} critical / "
            f"{len(normalized.warning_incidents)} warning / "
            f"{len(normalized.open_incidents)} total open incidents"
        )

    return _assemble(
        mode=REASONING_MODE_INCIDENT_REVIEW,
        summary=summary,
        highlights=highlights,
        prioritized=prioritized,
        bundle=bundle,
        normalized=normalized,
        trace_metadata={
            "open_incidents": len(normalized.open_incidents),
            "critical_incidents": len(normalized.critical_incidents),
            "warning_incidents": len(normalized.warning_incidents),
        },
    )


# ---------------------------------------------------------------------------
# 3. Maintenance suggestions
# ---------------------------------------------------------------------------


def maintenance_suggestions(ctx: LabOsContext) -> DomainReasoningResponse:
    """Which maintenance / calibration items are overdue or due, and
    which follow-up actions the catalogue allows."""
    normalized = normalize_labos_context(ctx)
    bundle = RecommendationBundle()

    prioritized = prioritize(
        normalized,
        include_reactors=False,
        include_incidents=False,
        include_maintenance=True,
        include_schedules=False,
    )

    highlights: list[str] = []
    for item in normalized.overdue_maintenance:
        highlights.append(
            f"overdue {item.kind} for {item.target_type}:{item.target_id}"
        )

    # One "run_<kind>" intent per overdue maintenance item.  The
    # catalogue enforcement in build_action drops any kind LabOS does
    # not expose, and the safety-context check defers items whose
    # target is in an unsafe state.
    for item in normalized.overdue_maintenance:
        intent_by_kind = {
            "calibration": "run_calibration",
            "maintenance": "run_maintenance",
            "service": "run_maintenance",
        }
        intended_action = intent_by_kind.get(item.kind.lower(), f"run_{item.kind.lower()}")
        build_action(
            bundle,
            normalized=normalized,
            intended_action=intended_action,
            target_entity_type=item.target_type,
            target_entity_id=item.target_id,
            rationale=f"overdue {item.kind} (risk={item.risk_level.value})",
            priority_bucket=PriorityBucket.HIGH,
            contributing_signals=[
                "overdue_maintenance",
                f"maintenance_kind_{item.kind}",
            ],
        )

    if not normalized.overdue_maintenance and not normalized.due_soon_maintenance:
        summary = "no maintenance overdue or due"
    else:
        summary = (
            f"{len(normalized.overdue_maintenance)} overdue, "
            f"{len(normalized.due_soon_maintenance)} due soon"
        )

    return _assemble(
        mode=REASONING_MODE_MAINTENANCE,
        summary=summary,
        highlights=highlights,
        prioritized=prioritized,
        bundle=bundle,
        normalized=normalized,
        trace_metadata={
            "overdue_count": len(normalized.overdue_maintenance),
            "due_soon_count": len(normalized.due_soon_maintenance),
        },
    )


# ---------------------------------------------------------------------------
# 4. Schedule / runtime review
# ---------------------------------------------------------------------------


def schedule_runtime_review(ctx: LabOsContext) -> DomainReasoningResponse:
    """Which schedules / commands are problematic, where is systemic noise."""
    normalized = normalize_labos_context(ctx)
    bundle = RecommendationBundle()

    prioritized = prioritize(
        normalized,
        include_reactors=False,
        include_incidents=False,
        include_maintenance=False,
        include_schedules=True,
    )

    highlights: list[str] = []
    for schedule in normalized.failed_schedules:
        highlights.append(
            f"schedule {schedule.schedule_id} failing "
            f"({schedule.consecutive_failures}x)"
        )
    for schedule in normalized.blocked_schedules:
        highlights.append(f"schedule {schedule.schedule_id} blocked")

    for schedule in normalized.failed_schedules:
        build_action(
            bundle,
            normalized=normalized,
            intended_action="pause_schedule"
            if schedule.consecutive_failures >= 3
            else "investigate_schedule",
            target_entity_type="schedule",
            target_entity_id=schedule.schedule_id,
            rationale=(
                f"schedule has {schedule.consecutive_failures} consecutive "
                "failure(s)"
            ),
            priority_bucket=PriorityBucket.HIGH,
            contributing_signals=["schedule_failing"],
            allow_on_unsafe_target=True,
        )
    for schedule in normalized.blocked_schedules:
        if schedule in normalized.failed_schedules:
            continue
        build_action(
            bundle,
            normalized=normalized,
            intended_action="investigate_schedule",
            target_entity_type="schedule",
            target_entity_id=schedule.schedule_id,
            rationale="schedule flagged as blocked",
            priority_bucket=PriorityBucket.HIGH,
            contributing_signals=["schedule_blocked"],
            allow_on_unsafe_target=True,
        )

    if not normalized.failed_schedules and not normalized.blocked_schedules:
        summary = "no schedule issues"
    else:
        summary = (
            f"{len(normalized.failed_schedules)} failing schedule(s), "
            f"{len(normalized.blocked_schedules)} blocked, "
            f"{len(normalized.failed_commands)} failed command(s)"
        )

    return _assemble(
        mode=REASONING_MODE_SCHEDULE_RUNTIME,
        summary=summary,
        highlights=highlights,
        prioritized=prioritized,
        bundle=bundle,
        normalized=normalized,
        trace_metadata={
            "failed_schedules": len(normalized.failed_schedules),
            "blocked_schedules": len(normalized.blocked_schedules),
            "failed_commands": len(normalized.failed_commands),
        },
    )


# ---------------------------------------------------------------------------
# 5. Cross-domain overview
# ---------------------------------------------------------------------------


def cross_domain_overview(ctx: LabOsContext) -> DomainReasoningResponse:
    """Unified operator view combining reactors, incidents, maintenance,
    schedules and safety signals into one prioritised focus list."""
    normalized = normalize_labos_context(ctx)
    bundle = RecommendationBundle()

    prioritized = prioritize(
        normalized,
        include_reactors=True,
        include_incidents=True,
        include_maintenance=True,
        include_schedules=True,
        include_nominal_reactors=False,
    )

    highlights: list[str] = []
    if normalized.critical_incidents:
        highlights.append(
            f"{len(normalized.critical_incidents)} critical incident(s) open"
        )
    if normalized.overdue_maintenance:
        highlights.append(
            f"{len(normalized.overdue_maintenance)} overdue maintenance item(s)"
        )
    if normalized.failed_schedules:
        highlights.append(
            f"{len(normalized.failed_schedules)} failing schedule(s)"
        )
    if normalized.safety_alerts_by_target:
        highlights.append(
            f"{sum(len(v) for v in normalized.safety_alerts_by_target.values())} "
            "safety alert(s) active"
        )

    total_signal_entities = (
        len(normalized.open_incidents)
        + len(normalized.overdue_maintenance)
        + len(normalized.failed_schedules)
        + len(normalized.blocked_schedules)
        + sum(
            1
            for view in normalized.reactor_health.values()
            if view.health_bucket
            in {PriorityBucket.CRITICAL, PriorityBucket.HIGH}
        )
    )

    if total_signal_entities == 0:
        summary = "cross-domain nominal — no open signals"
    else:
        summary = (
            f"{total_signal_entities} cross-domain signal(s) "
            "prioritised across reactors, incidents, maintenance and "
            "schedules"
        )

    return _assemble(
        mode=REASONING_MODE_CROSS_DOMAIN,
        summary=summary,
        highlights=highlights,
        prioritized=prioritized,
        bundle=bundle,
        normalized=normalized,
        trace_metadata={
            "total_signals": total_signal_entities,
            "sections": list(normalized.used_context_sections),
        },
    )
