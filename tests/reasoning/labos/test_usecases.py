"""Reasoning use-case tests — five explicit scenarios.

Tests here assert the Response Shape V2 contract end-to-end on
fixed input snapshots.  These are deterministic: given the same
:class:`LabOsContext`, each use case returns the same response.
"""

from __future__ import annotations

import pytest

from services.core import (
    get_labos_cross_domain_overview,
    get_labos_incident_review,
    get_labos_maintenance_suggestions,
    get_labos_reactor_daily_overview,
    get_labos_schedule_runtime_review,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared fixture — one snapshot exercises every section
# ---------------------------------------------------------------------------


def _full_snapshot() -> dict:
    return {
        "reactors": [
            {"reactor_id": "R1", "display_name": "Reactor One", "status": "nominal"},
            {"reactor_id": "R2", "display_name": "Reactor Two", "status": "warning"},
            {"reactor_id": "R3", "display_name": "Reactor Three", "status": "nominal"},
        ],
        "incidents": [
            {
                "incident_id": "I-crit",
                "severity": "critical",
                "status": "open",
                "reactor_id": "R2",
            },
            {
                "incident_id": "I-warn",
                "severity": "warning",
                "status": "open",
                "reactor_id": "R2",
            },
            {
                "incident_id": "I-closed",
                "severity": "critical",
                "status": "closed",
                "reactor_id": "R1",
            },
        ],
        "maintenance": [
            {
                "maintenance_id": "M-overdue",
                "target_type": "reactor",
                "target_id": "R2",
                "kind": "calibration",
                "overdue": True,
                "risk_level": "medium",
            },
            {
                "maintenance_id": "M-due",
                "target_type": "reactor",
                "target_id": "R1",
                "kind": "service",
                "overdue": False,
                "due_at": "2026-12-01T00:00:00",
            },
        ],
        "schedules": [
            {
                "schedule_id": "S-bad",
                "status": "failed",
                "consecutive_failures": 4,
            },
            {"schedule_id": "S-ok", "status": "running"},
        ],
        "commands": [
            {"command_id": "C1", "status": "failed", "failure_reason": "timeout"}
        ],
        "action_catalog": [
            {"action_name": "open_reactor_detail", "requires_approval": False},
            {
                "action_name": "acknowledge_critical_incident",
                "risk_level": "medium",
                "requires_approval": True,
            },
            {
                "action_name": "acknowledge_incident",
                "risk_level": "low",
                "requires_approval": False,
            },
            {
                "action_name": "run_calibration",
                "risk_level": "medium",
                "requires_approval": True,
            },
            {"action_name": "pause_schedule", "requires_approval": False},
            {"action_name": "investigate_schedule", "requires_approval": False},
        ],
    }


# ---------------------------------------------------------------------------
# 1. Reactor daily overview
# ---------------------------------------------------------------------------


class TestReactorDailyOverview:
    def test_summary_reports_attention_and_nominal_counts(self):
        out = get_labos_reactor_daily_overview(_full_snapshot())
        assert out["reasoning_mode"] == "labos_reactor_daily_overview"
        # R2 attention, R1 + R3 nominal.
        assert "1 reactor(s) need attention" in out["summary"]
        assert "2 nominal" in out["summary"]

    def test_critical_reactor_prioritised_first(self):
        out = get_labos_reactor_daily_overview(_full_snapshot())
        ranked = out["prioritized_entities"]
        assert ranked[0]["entity_id"] == "R2"
        assert ranked[0]["priority_bucket"] == "critical"
        assert ranked[0]["priority_reason"]

    def test_includes_nominal_reactors_in_focus_list(self):
        out = get_labos_reactor_daily_overview(_full_snapshot())
        ranked_ids = {e["entity_id"] for e in out["prioritized_entities"]}
        assert {"R1", "R2", "R3"}.issubset(ranked_ids)

    def test_recommends_open_reactor_detail_for_critical_reactor(self):
        out = get_labos_reactor_daily_overview(_full_snapshot())
        rec_names = [(a["action_name"], a["target_entity_id"]) for a in out["recommended_actions"]]
        assert ("open_reactor_detail", "R2") in rec_names

    def test_empty_context_returns_well_formed_response(self):
        out = get_labos_reactor_daily_overview({})
        assert out["reasoning_mode"] == "labos_reactor_daily_overview"
        assert out["summary"]
        assert out["prioritized_entities"] == []
        assert out["recommended_actions"] == []


# ---------------------------------------------------------------------------
# 2. Incident review
# ---------------------------------------------------------------------------


class TestIncidentReview:
    def test_counts_reported(self):
        out = get_labos_incident_review(_full_snapshot())
        assert "1 critical" in out["summary"]
        assert "1 warning" in out["summary"]
        # Closed incident (I-closed) excluded.
        assert "2 total open" in out["summary"]

    def test_critical_first(self):
        out = get_labos_incident_review(_full_snapshot())
        first = out["prioritized_entities"][0]
        assert first["entity_type"] == "incident"
        assert first["entity_id"] == "I-crit"
        assert first["priority_bucket"] == "critical"

    def test_acknowledge_critical_requires_approval(self):
        out = get_labos_incident_review(_full_snapshot())
        assert any(
            a["action_name"] == "acknowledge_critical_incident"
            and a["target_entity_id"] == "I-crit"
            for a in out["approval_required_actions"]
        )
        # The warning-severity ack is catalog-configured requires_approval=False.
        assert any(
            a["action_name"] == "acknowledge_incident"
            and a["target_entity_id"] == "I-warn"
            for a in out["recommended_actions"]
        )


# ---------------------------------------------------------------------------
# 3. Maintenance suggestions
# ---------------------------------------------------------------------------


class TestMaintenanceSuggestions:
    def test_overdue_item_surfaces(self):
        out = get_labos_maintenance_suggestions(_full_snapshot())
        ranked = out["prioritized_entities"]
        assert ranked[0]["entity_id"] == "M-overdue"
        assert "overdue" in ranked[0]["priority_reason"].lower()

    def test_run_calibration_goes_to_approval_bucket(self):
        out = get_labos_maintenance_suggestions(_full_snapshot())
        assert any(
            a["action_name"] == "run_calibration"
            and a["target_entity_id"] == "R2"
            and a["requires_approval"] is True
            for a in out["approval_required_actions"]
        )

    def test_missing_catalog_entry_deferred_not_invented(self):
        # Drop run_calibration from the catalogue so the engine has
        # nothing safe to recommend — it must defer, not invent.
        snapshot = _full_snapshot()
        snapshot["action_catalog"] = [
            entry
            for entry in snapshot["action_catalog"]
            if entry["action_name"] != "run_calibration"
        ]
        out = get_labos_maintenance_suggestions(snapshot)
        assert all(
            a["action_name"] != "run_calibration" for a in out["recommended_actions"]
        )
        assert all(
            a["action_name"] != "run_calibration"
            for a in out["approval_required_actions"]
        )
        assert any(
            d["intended_action"] == "run_calibration"
            and d["deferral_reason"] == "missing_action_catalog_entry"
            for d in out["blocked_or_deferred_actions"]
        )


# ---------------------------------------------------------------------------
# 4. Schedule / runtime review
# ---------------------------------------------------------------------------


class TestScheduleRuntimeReview:
    def test_failing_schedule_past_threshold_suggests_pause(self):
        out = get_labos_schedule_runtime_review(_full_snapshot())
        rec = [(a["action_name"], a["target_entity_id"]) for a in out["recommended_actions"]]
        assert ("pause_schedule", "S-bad") in rec

    def test_summary_counts_failed_and_blocked(self):
        out = get_labos_schedule_runtime_review(_full_snapshot())
        assert "1 failing" in out["summary"]
        assert "0 blocked" in out["summary"]


# ---------------------------------------------------------------------------
# 5. Cross-domain overview
# ---------------------------------------------------------------------------


class TestCrossDomainOverview:
    def test_highlights_call_out_each_section_that_contributes(self):
        out = get_labos_cross_domain_overview(_full_snapshot())
        joined = " | ".join(out["highlights"])
        assert "critical incident" in joined
        assert "overdue maintenance" in joined
        assert "failing schedule" in joined

    def test_cross_domain_ranks_critical_incidents_first(self):
        out = get_labos_cross_domain_overview(_full_snapshot())
        first = out["prioritized_entities"][0]
        assert first["priority_bucket"] == "critical"


# ---------------------------------------------------------------------------
# Shared invariants — apply to every use case
# ---------------------------------------------------------------------------


USE_CASES = [
    ("reactor_daily_overview", get_labos_reactor_daily_overview),
    ("incident_review", get_labos_incident_review),
    ("maintenance_suggestions", get_labos_maintenance_suggestions),
    ("schedule_runtime_review", get_labos_schedule_runtime_review),
    ("cross_domain_overview", get_labos_cross_domain_overview),
]


class TestSharedInvariants:
    @pytest.mark.parametrize("name,fn", USE_CASES)
    def test_response_shape_v2_keys_always_present(self, name, fn):
        out = fn(_full_snapshot())
        required_keys = {
            "reasoning_mode",
            "summary",
            "highlights",
            "prioritized_entities",
            "recommended_actions",
            "recommended_checks",
            "approval_required_actions",
            "blocked_or_deferred_actions",
            "used_context_sections",
            "trace_metadata",
        }
        assert required_keys.issubset(out.keys()), name

    @pytest.mark.parametrize("name,fn", USE_CASES)
    def test_deterministic_on_identical_input(self, name, fn):
        snapshot = _full_snapshot()
        assert fn(snapshot) == fn(snapshot), name

    @pytest.mark.parametrize("name,fn", USE_CASES)
    def test_no_recommendation_names_outside_catalog(self, name, fn):
        snapshot = _full_snapshot()
        catalog_names = {
            entry["action_name"] for entry in snapshot["action_catalog"]
        }
        out = fn(snapshot)
        for action in out["recommended_actions"] + out["approval_required_actions"]:
            assert action["action_name"] in catalog_names, (
                f"{name} surfaced an action not in the catalog: {action['action_name']}"
            )

    @pytest.mark.parametrize("name,fn", USE_CASES)
    def test_invalid_context_returns_error_envelope(self, name, fn):
        out = fn({"incidents": [{"bogus": 1}]})
        assert out.get("error") == "invalid_context"
        assert "detail" in out


class TestInvalidReasoningMode:
    def test_unknown_mode_surfaces_error(self):
        from services.core import _run_labos_reasoner

        out = _run_labos_reasoner("not_a_real_mode", {})
        assert out["error"] == "invalid_reasoning_mode"
        assert "Valid:" in out["detail"]
