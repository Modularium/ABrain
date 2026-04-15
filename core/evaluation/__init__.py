"""Canonical evaluation layer for ABrain — read-only replay and compliance.

This module provides controlled, dry-run evaluation of stored decision traces
against the current routing and governance logic.  It does **not** execute
actions, write new traces, or create approvals.

Public surface
--------------
- :class:`TraceEvaluator` — orchestrates per-trace and batch evaluation
- :class:`TraceEvaluationResult` — full evaluation of one stored trace
- :class:`BatchEvaluationReport` — baseline metrics across many traces
- :class:`RoutingReplayResult` — per-step routing comparison
- :class:`PolicyReplayResult` — per-step policy compliance comparison
- :class:`StepEvaluationResult` — combined per-step view
"""

from .harness import TraceEvaluator
from .models import (
    BatchEvaluationReport,
    PolicyReplayResult,
    PolicyReplayVerdict,
    RoutingReplayResult,
    RoutingReplayVerdict,
    StepEvaluationResult,
    TraceEvaluationResult,
)

__all__ = [
    "BatchEvaluationReport",
    "PolicyReplayResult",
    "PolicyReplayVerdict",
    "RoutingReplayResult",
    "RoutingReplayVerdict",
    "StepEvaluationResult",
    "TraceEvaluationResult",
    "TraceEvaluator",
]
