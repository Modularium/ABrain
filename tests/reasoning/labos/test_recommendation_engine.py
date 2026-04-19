"""Recommendation-engine invariants — every test here pins one rule.

The three invariants under test:

1. ``no_invented_actions`` — if ABrain wants to suggest an action
   whose name is not in the supplied catalogue, it surfaces as a
   DeferredAction with ``missing_action_catalog_entry``, never as a
   RecommendedAction.
2. ``respects_approval`` — when the catalogue entry has
   ``requires_approval=True``, the recommendation lands in
   ``approval_required_actions``, never in ``recommended_actions``.
3. ``respects_safety_context`` — when the target is in an unsafe
   state (offline reactor or a safety alert on the same
   target_type/target_id pair), the recommendation is deferred.
"""

from __future__ import annotations

import pytest

from core.reasoning.labos.context_normalizer import normalize_labos_context
from core.reasoning.labos.recommendation_engine import (
    RecommendationBundle,
    build_action,
)
from core.reasoning.labos.schemas import (
    DeferralReason,
    LabOsContext,
    PriorityBucket,
)

pytestmark = pytest.mark.unit


def _ctx(**kwargs) -> LabOsContext:
    return LabOsContext.model_validate(kwargs)


class TestNoInventedActions:
    def test_unknown_action_name_deferred(self):
        norm = normalize_labos_context(
            _ctx(
                reactors=[{"reactor_id": "R1", "status": "warning"}],
                action_catalog=[],
            )
        )
        bundle = RecommendationBundle()
        build_action(
            bundle,
            normalized=norm,
            intended_action="some_imaginary_action",
            target_entity_type="reactor",
            target_entity_id="R1",
            rationale="test",
            priority_bucket=PriorityBucket.HIGH,
        )
        assert bundle.recommended_actions == []
        assert bundle.approval_required_actions == []
        assert len(bundle.deferred_actions) == 1
        deferred = bundle.deferred_actions[0]
        assert deferred.deferral_reason == DeferralReason.MISSING_ACTION_CATALOG_ENTRY
        assert deferred.intended_action == "some_imaginary_action"


class TestRespectsApproval:
    def test_approval_required_action_routed_to_approval_bucket(self):
        norm = normalize_labos_context(
            _ctx(
                reactors=[{"reactor_id": "R1", "status": "warning"}],
                action_catalog=[
                    {
                        "action_name": "run_calibration",
                        "risk_level": "high",
                        "requires_approval": True,
                    }
                ],
            )
        )
        bundle = RecommendationBundle()
        build_action(
            bundle,
            normalized=norm,
            intended_action="run_calibration",
            target_entity_type="reactor",
            target_entity_id="R1",
            rationale="overdue",
            priority_bucket=PriorityBucket.HIGH,
        )
        assert bundle.recommended_actions == []
        assert len(bundle.approval_required_actions) == 1
        recommendation = bundle.approval_required_actions[0]
        assert recommendation.requires_approval is True
        assert recommendation.risk_level.value == "high"

    def test_non_approval_action_routed_to_recommended(self):
        norm = normalize_labos_context(
            _ctx(
                reactors=[{"reactor_id": "R1", "status": "warning"}],
                action_catalog=[
                    {
                        "action_name": "open_reactor_detail",
                        "risk_level": "low",
                        "requires_approval": False,
                    }
                ],
            )
        )
        bundle = RecommendationBundle()
        build_action(
            bundle,
            normalized=norm,
            intended_action="open_reactor_detail",
            target_entity_type="reactor",
            target_entity_id="R1",
            rationale="needs attention",
            priority_bucket=PriorityBucket.HIGH,
        )
        assert len(bundle.recommended_actions) == 1
        assert bundle.approval_required_actions == []


class TestRespectsSafetyContext:
    def test_safety_alert_on_target_defers_action(self):
        norm = normalize_labos_context(
            _ctx(
                reactors=[{"reactor_id": "R1", "status": "warning"}],
                safety_alerts=[
                    {
                        "alert_id": "A1",
                        "severity": "critical",
                        "target_type": "reactor",
                        "target_id": "R1",
                    }
                ],
                action_catalog=[
                    {"action_name": "run_calibration", "requires_approval": False}
                ],
            )
        )
        bundle = RecommendationBundle()
        build_action(
            bundle,
            normalized=norm,
            intended_action="run_calibration",
            target_entity_type="reactor",
            target_entity_id="R1",
            rationale="overdue",
            priority_bucket=PriorityBucket.HIGH,
        )
        assert bundle.recommended_actions == []
        assert bundle.approval_required_actions == []
        assert len(bundle.deferred_actions) == 1
        assert (
            bundle.deferred_actions[0].deferral_reason == DeferralReason.SAFETY_CONTEXT
        )

    def test_offline_reactor_defers_action(self):
        norm = normalize_labos_context(
            _ctx(
                reactors=[{"reactor_id": "R1", "status": "offline"}],
                action_catalog=[
                    {"action_name": "run_calibration", "requires_approval": False}
                ],
            )
        )
        bundle = RecommendationBundle()
        build_action(
            bundle,
            normalized=norm,
            intended_action="run_calibration",
            target_entity_type="reactor",
            target_entity_id="R1",
            rationale="overdue",
            priority_bucket=PriorityBucket.HIGH,
        )
        assert bundle.recommended_actions == []
        assert (
            bundle.deferred_actions[0].deferral_reason == DeferralReason.SAFETY_CONTEXT
        )
        assert "offline" in bundle.deferred_actions[0].detail

    def test_allow_on_unsafe_target_overrides_defer(self):
        # Diagnostic intents (e.g. "open_reactor_detail") need to still
        # surface when the target is unsafe — that's precisely when
        # operators want to investigate.  Opt-in flag is how use cases
        # declare "this intent is safe even on unhealthy targets."
        norm = normalize_labos_context(
            _ctx(
                reactors=[{"reactor_id": "R1", "status": "offline"}],
                action_catalog=[
                    {
                        "action_name": "open_reactor_detail",
                        "requires_approval": False,
                    }
                ],
            )
        )
        bundle = RecommendationBundle()
        build_action(
            bundle,
            normalized=norm,
            intended_action="open_reactor_detail",
            target_entity_type="reactor",
            target_entity_id="R1",
            rationale="offline — investigate",
            priority_bucket=PriorityBucket.HIGH,
            allow_on_unsafe_target=True,
        )
        assert len(bundle.recommended_actions) == 1
        assert bundle.deferred_actions == []
