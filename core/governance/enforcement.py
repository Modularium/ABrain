"""Deterministic policy enforcement helpers."""

from __future__ import annotations

from .policy_models import PolicyDecision


class PolicyViolationError(RuntimeError):
    """Raised when runtime governance denies a selected action."""

    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        super().__init__(decision.reason)


def enforce_policy(decision: PolicyDecision) -> str:
    """Return an enforcement result or raise when the action is denied."""
    if decision.effect == "deny":
        raise PolicyViolationError(decision)
    if decision.effect == "require_approval":
        return "approval_required"
    return "allowed"
