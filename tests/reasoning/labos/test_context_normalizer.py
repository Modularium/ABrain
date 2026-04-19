"""Unit tests for :mod:`core.reasoning.labos.context_normalizer`.

The normaliser is pure and deterministic — these tests pin the
bucket/health escalation rules so reasoners upstream can trust them.
"""

from __future__ import annotations

import pytest

from core.reasoning.labos.context_normalizer import normalize_labos_context
from core.reasoning.labos.schemas import (
    HealthStatus,
    IncidentSeverity,
    LabOsContext,
    PriorityBucket,
)

pytestmark = pytest.mark.unit


def _ctx(**kwargs) -> LabOsContext:
    return LabOsContext.model_validate(kwargs)


class TestReactorHealth:
    def test_nominal_reactor_with_no_signals_stays_nominal(self):
        ctx = _ctx(reactors=[{"reactor_id": "R1", "status": "nominal"}])
        norm = normalize_labos_context(ctx)
        view = norm.reactor_health["R1"]
        assert view.effective_status == HealthStatus.NOMINAL
        assert view.health_bucket == PriorityBucket.NOMINAL

    def test_critical_incident_escalates_nominal_reactor_to_incident(self):
        ctx = _ctx(
            reactors=[{"reactor_id": "R1", "status": "nominal"}],
            incidents=[
                {
                    "incident_id": "I1",
                    "severity": "critical",
                    "status": "open",
                    "reactor_id": "R1",
                }
            ],
        )
        view = normalize_labos_context(ctx).reactor_health["R1"]
        assert view.effective_status == HealthStatus.INCIDENT
        assert view.health_bucket == PriorityBucket.CRITICAL
        assert view.worst_incident_severity == IncidentSeverity.CRITICAL

    def test_labos_declared_incident_never_downgraded_by_missing_signals(self):
        # Even if no incident rows are attached, a LabOS-declared
        # incident status is authoritative and must not be downgraded.
        ctx = _ctx(reactors=[{"reactor_id": "R1", "status": "incident"}])
        view = normalize_labos_context(ctx).reactor_health["R1"]
        assert view.effective_status == HealthStatus.INCIDENT

    def test_overdue_maintenance_on_reactor_escalates_to_warning(self):
        ctx = _ctx(
            reactors=[{"reactor_id": "R1", "status": "nominal"}],
            maintenance=[
                {
                    "maintenance_id": "M1",
                    "target_type": "reactor",
                    "target_id": "R1",
                    "kind": "calibration",
                    "overdue": True,
                    "risk_level": "medium",
                }
            ],
        )
        view = normalize_labos_context(ctx).reactor_health["R1"]
        assert view.has_overdue_maintenance is True
        assert view.effective_status == HealthStatus.WARNING
        assert view.health_bucket == PriorityBucket.HIGH

    def test_safety_alert_escalates_to_incident_even_without_incident_row(self):
        ctx = _ctx(
            reactors=[{"reactor_id": "R1", "status": "nominal"}],
            safety_alerts=[
                {
                    "alert_id": "A1",
                    "severity": "warning",
                    "target_type": "reactor",
                    "target_id": "R1",
                }
            ],
        )
        view = normalize_labos_context(ctx).reactor_health["R1"]
        assert view.has_safety_alert is True
        assert view.effective_status == HealthStatus.INCIDENT


class TestIncidentBuckets:
    def test_closed_incidents_are_not_considered_open(self):
        ctx = _ctx(
            incidents=[
                {"incident_id": "I1", "severity": "critical", "status": "closed"}
            ]
        )
        norm = normalize_labos_context(ctx)
        assert norm.open_incidents == []
        assert norm.critical_incidents == []

    def test_separates_critical_and_warning(self):
        ctx = _ctx(
            incidents=[
                {"incident_id": "I1", "severity": "critical", "status": "open"},
                {"incident_id": "I2", "severity": "warning", "status": "open"},
                {"incident_id": "I3", "severity": "info", "status": "open"},
            ]
        )
        norm = normalize_labos_context(ctx)
        assert [i.incident_id for i in norm.critical_incidents] == ["I1"]
        assert [i.incident_id for i in norm.warning_incidents] == ["I2"]
        assert len(norm.open_incidents) == 3


class TestMaintenanceBuckets:
    def test_overdue_and_due_soon_are_separate(self):
        ctx = _ctx(
            maintenance=[
                {
                    "maintenance_id": "M1",
                    "target_type": "reactor",
                    "target_id": "R1",
                    "kind": "calibration",
                    "overdue": True,
                    "risk_level": "medium",
                    "due_at": "2026-01-01T00:00:00",
                },
                {
                    "maintenance_id": "M2",
                    "target_type": "reactor",
                    "target_id": "R1",
                    "kind": "service",
                    "due_at": "2026-12-01T00:00:00",
                },
            ]
        )
        norm = normalize_labos_context(ctx)
        assert [m.maintenance_id for m in norm.overdue_maintenance] == ["M1"]
        assert [m.maintenance_id for m in norm.due_soon_maintenance] == ["M2"]


class TestSchedules:
    def test_failed_and_blocked_tracked_independently(self):
        ctx = _ctx(
            schedules=[
                {"schedule_id": "S1", "status": "failed", "consecutive_failures": 2},
                {"schedule_id": "S2", "status": "running", "blocked": True},
                {"schedule_id": "S3", "status": "running"},
            ]
        )
        norm = normalize_labos_context(ctx)
        assert [s.schedule_id for s in norm.failed_schedules] == ["S1"]
        assert [s.schedule_id for s in norm.blocked_schedules] == ["S2"]


class TestUsedContextSections:
    def test_only_populated_sections_surface(self):
        ctx = _ctx(
            reactors=[{"reactor_id": "R1"}],
            incidents=[],
        )
        norm = normalize_labos_context(ctx)
        assert "reactors" in norm.used_context_sections
        assert "incidents" not in norm.used_context_sections

    def test_action_catalog_section_declared_when_catalog_present(self):
        ctx = _ctx(
            action_catalog=[
                {"action_name": "open_reactor_detail"},
            ]
        )
        norm = normalize_labos_context(ctx)
        assert "action_catalog" in norm.used_context_sections


class TestActionCatalogUniqueness:
    def test_duplicate_action_names_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            _ctx(
                action_catalog=[
                    {"action_name": "open_reactor_detail"},
                    {"action_name": "open_reactor_detail"},
                ]
            )
