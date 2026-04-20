"""Recommendation engine for LabOS reasoning.

Every recommendation ABrain emits goes through :func:`build_action`.
That function takes an *intent* (the action name ABrain wants to
suggest) and a target entity, then:

1. Looks the intent up in the caller-supplied action catalogue.
2. If absent → emits a :class:`DeferredAction` with
   ``MISSING_ACTION_CATALOG_ENTRY`` instead of a
   :class:`RecommendedAction`.  **This enforces the
   "no invented actions" invariant.**
3. If present but ``requires_approval`` → emits a
   :class:`RecommendedAction` into the approval bucket.
4. If the target is in a safety-flagged state → emits a
   :class:`DeferredAction` with ``SAFETY_CONTEXT`` regardless of the
   requires_approval flag.

Use cases never build :class:`RecommendedAction` instances directly —
they always route through :func:`build_action` so the invariants hold.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .context_normalizer import NormalizedLabOsContext
from .schemas import (
    DeferralReason,
    DeferredAction,
    HealthStatus,
    PriorityBucket,
    RecommendedAction,
)


@dataclass
class RecommendationBundle:
    """Aggregated output of the recommendation engine for a use case."""

    recommended_actions: list[RecommendedAction] = field(default_factory=list)
    approval_required_actions: list[RecommendedAction] = field(default_factory=list)
    deferred_actions: list[DeferredAction] = field(default_factory=list)


def _target_is_unsafe(
    normalized: NormalizedLabOsContext,
    entity_type: str,
    entity_id: str,
) -> tuple[bool, str | None]:
    """Return ``(unsafe, reason)`` for a target in the LabOS snapshot."""
    if (entity_type, entity_id) in normalized.safety_alerts_by_target:
        return True, "active safety alert"
    if entity_type == "reactor":
        view = normalized.reactor_health.get(entity_id)
        if view is not None and view.effective_status == HealthStatus.OFFLINE:
            return True, "reactor offline"
    if entity_type == "module":
        module_view = normalized.module_health.get(entity_id)
        if module_view is not None:
            if module_view.module.offline:
                return True, "module offline"
            if module_view.effective_status == HealthStatus.INCIDENT:
                return True, "module in incident state"
    return False, None


def build_action(
    bundle: RecommendationBundle,
    *,
    normalized: NormalizedLabOsContext,
    intended_action: str,
    target_entity_type: str,
    target_entity_id: str,
    rationale: str,
    priority_bucket: PriorityBucket,
    contributing_signals: list[str] | None = None,
    allow_on_unsafe_target: bool = False,
) -> None:
    """Route one action intent into the correct :class:`RecommendationBundle` slot.

    This is the only supported way to add actions — it guarantees the
    ``no_invented_actions``, ``respects_approval`` and
    ``respects_safety_context`` invariants hold.
    """
    signals = list(contributing_signals or [])

    catalog_entry = normalized.action_catalog_by_name.get(intended_action)
    if catalog_entry is None:
        bundle.deferred_actions.append(
            DeferredAction(
                intended_action=intended_action,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                deferral_reason=DeferralReason.MISSING_ACTION_CATALOG_ENTRY,
                detail=(
                    f"action '{intended_action}' is not exposed by the "
                    "LabOS action catalog; ABrain will not recommend "
                    "inventing it"
                ),
            )
        )
        return

    # Safety-context check — if the target is in an unsafe state, hold the
    # action back unless the use case explicitly opted in.
    if not allow_on_unsafe_target:
        unsafe, unsafe_reason = _target_is_unsafe(
            normalized, target_entity_type, target_entity_id
        )
        if unsafe:
            bundle.deferred_actions.append(
                DeferredAction(
                    intended_action=intended_action,
                    target_entity_type=target_entity_type,
                    target_entity_id=target_entity_id,
                    deferral_reason=DeferralReason.SAFETY_CONTEXT,
                    detail=(
                        f"deferred — target is in an unsafe state "
                        f"({unsafe_reason}); operator must reassess"
                    ),
                )
            )
            return

    recommendation = RecommendedAction(
        action_name=catalog_entry.action_name,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        rationale=rationale,
        risk_level=catalog_entry.risk_level,
        requires_approval=catalog_entry.requires_approval,
        priority_bucket=priority_bucket,
        contributing_signals=signals,
    )
    if catalog_entry.requires_approval:
        bundle.approval_required_actions.append(recommendation)
    else:
        bundle.recommended_actions.append(recommendation)
