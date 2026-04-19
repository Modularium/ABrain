"""Deterministic priority-engine tests.

Priority rules are explicit and small; these tests pin them so a
future rule change shows up as a failing test, not a silent drift.
"""

from __future__ import annotations

import pytest

from core.reasoning.labos.context_normalizer import normalize_labos_context
from core.reasoning.labos.priority_engine import prioritize
from core.reasoning.labos.schemas import LabOsContext, PriorityBucket

pytestmark = pytest.mark.unit


def _ctx(**kwargs) -> LabOsContext:
    return LabOsContext.model_validate(kwargs)


class TestBucketAssignment:
    def test_critical_incident_ranked_ahead_of_warning(self):
        norm = normalize_labos_context(
            _ctx(
                incidents=[
                    {"incident_id": "I-warn", "severity": "warning", "status": "open"},
                    {"incident_id": "I-crit", "severity": "critical", "status": "open"},
                ]
            )
        )
        ranked = prioritize(
            norm,
            include_reactors=False,
            include_incidents=True,
            include_maintenance=False,
            include_schedules=False,
        )
        assert [e.entity_id for e in ranked][:2] == ["I-crit", "I-warn"]
        assert ranked[0].priority_rank == 1
        assert ranked[1].priority_rank == 2
        assert ranked[0].priority_bucket == PriorityBucket.CRITICAL
        assert ranked[1].priority_bucket == PriorityBucket.HIGH

    def test_overdue_high_risk_maintenance_escalates_to_critical(self):
        norm = normalize_labos_context(
            _ctx(
                maintenance=[
                    {
                        "maintenance_id": "M-high",
                        "target_type": "reactor",
                        "target_id": "R1",
                        "kind": "calibration",
                        "overdue": True,
                        "risk_level": "high",
                    }
                ]
            )
        )
        ranked = prioritize(
            norm,
            include_reactors=False,
            include_incidents=False,
            include_maintenance=True,
            include_schedules=False,
        )
        assert ranked[0].priority_bucket == PriorityBucket.CRITICAL

    def test_schedule_failing_below_threshold_is_medium(self):
        norm = normalize_labos_context(
            _ctx(
                schedules=[
                    {
                        "schedule_id": "S1",
                        "status": "failed",
                        "consecutive_failures": 1,
                    }
                ]
            )
        )
        ranked = prioritize(
            norm,
            include_reactors=False,
            include_incidents=False,
            include_maintenance=False,
            include_schedules=True,
        )
        assert ranked[0].priority_bucket == PriorityBucket.MEDIUM

    def test_schedule_failing_at_three_threshold_is_high(self):
        norm = normalize_labos_context(
            _ctx(
                schedules=[
                    {
                        "schedule_id": "S1",
                        "status": "failed",
                        "consecutive_failures": 3,
                    }
                ]
            )
        )
        ranked = prioritize(
            norm,
            include_reactors=False,
            include_incidents=False,
            include_maintenance=False,
            include_schedules=True,
        )
        assert ranked[0].priority_bucket == PriorityBucket.HIGH


class TestDeterminism:
    def test_stable_rank_on_identical_input(self):
        payload = {
            "reactors": [
                {"reactor_id": "R1", "status": "warning"},
                {"reactor_id": "R2", "status": "nominal"},
            ],
            "incidents": [
                {"incident_id": "I1", "severity": "warning", "status": "open"},
            ],
        }
        ranked_a = prioritize(normalize_labos_context(_ctx(**payload)))
        ranked_b = prioritize(normalize_labos_context(_ctx(**payload)))
        assert [
            (e.entity_type, e.entity_id, e.priority_rank) for e in ranked_a
        ] == [
            (e.entity_type, e.entity_id, e.priority_rank) for e in ranked_b
        ]

    def test_nominal_reactors_hidden_by_default(self):
        norm = normalize_labos_context(
            _ctx(reactors=[{"reactor_id": "R-nom", "status": "nominal"}])
        )
        assert prioritize(norm) == []
        assert len(prioritize(norm, include_nominal_reactors=True)) == 1


class TestPriorityReasonPopulated:
    def test_every_entity_carries_nonempty_reason(self):
        ranked = prioritize(
            normalize_labos_context(
                _ctx(
                    reactors=[{"reactor_id": "R1", "status": "warning"}],
                    incidents=[
                        {"incident_id": "I1", "severity": "warning", "status": "open"}
                    ],
                    maintenance=[
                        {
                            "maintenance_id": "M1",
                            "target_type": "reactor",
                            "target_id": "R1",
                            "kind": "service",
                            "overdue": True,
                        }
                    ],
                    schedules=[
                        {
                            "schedule_id": "S1",
                            "status": "failed",
                            "consecutive_failures": 1,
                        }
                    ],
                )
            )
        )
        assert ranked, "expected at least one prioritized entity"
        for entity in ranked:
            assert entity.priority_reason.strip() != ""
            assert entity.priority_rank >= 1
