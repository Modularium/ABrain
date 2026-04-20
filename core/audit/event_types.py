"""Canonical span-event type constants for the ABrain audit trail.

Values mirror the free-form strings already emitted through
``core.audit.context.add_span_event`` so that introducing the constants does
not change any persisted trace payload.  New call sites (strategy decision,
plan creation, evaluation) should import from here instead of inlining
literals.
"""

from __future__ import annotations

# Strategy decision layer (PR1).
DECISION_CREATED = "decision_created"

# Planning layer (reserved for PR2).
PLAN_CREATED = "plan_created"

# Execution orchestrator (reserved for PR3).
STEP_EXECUTED = "step_executed"
EXECUTION_FAILED = "execution_failed"

# Approval gates — values match the strings already emitted by
# ``core/orchestration/orchestrator.py``.  Kept here so downstream code can
# reference the constants without coupling to the orchestrator module.
APPROVAL_REQUESTED = "approval_requested"
APPROVAL_GRANTED = "approval_granted"

# Runtime evaluator (reserved for PR4).
EVALUATION_COMPLETED = "evaluation_completed"

__all__ = [
    "APPROVAL_GRANTED",
    "APPROVAL_REQUESTED",
    "DECISION_CREATED",
    "EVALUATION_COMPLETED",
    "EXECUTION_FAILED",
    "PLAN_CREATED",
    "STEP_EXECUTED",
]
