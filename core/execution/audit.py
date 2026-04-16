"""Canonical execution audit event helpers.

Phase 2 — "Audit-Events für jeden Tool-Call standardisieren".

``canonical_execution_span_attributes`` assembles the standardised attribute
dict for the ``execution`` span emitted to ``TraceStore`` after every adapter
call.  It is a pure function: it reads from the completed ``ExecutionResult``
(which already carries ``risk_tier``, ``adapter_name``, ``source_type``, and
``execution_kind`` in its metadata after ``ExecutionEngine.execute()``) plus
two caller-supplied context values.

Canonical fields
----------------
agent_id       — which agent ran (from result.agent_id)
adapter_name   — canonical short name of the adapter (from result.metadata)
task_type      — task category supplied by the caller (from task context)
risk_tier      — governance risk tier from the adapter manifest (from result.metadata)
source_type    — AgentSourceType of the executing agent (from result.metadata)
execution_kind — AgentExecutionKind of the executing agent (from result.metadata)
success        — whether the execution succeeded
duration_ms    — execution latency in milliseconds (None when not reported)
cost           — monetary cost of the call (None when not reported)
token_count    — token usage (None when not reported)
warning_count  — total warning count (includes capability warnings appended by engine)
policy_effect  — governance outcome that permitted this execution ("allow", …)
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.execution.adapters.base import ExecutionResult

#: Ordered tuple of all canonical attribute keys for exhaustiveness checks.
CANONICAL_EXECUTION_SPAN_KEYS: tuple[str, ...] = (
    "agent_id",
    "adapter_name",
    "task_type",
    "risk_tier",
    "source_type",
    "execution_kind",
    "success",
    "duration_ms",
    "cost",
    "token_count",
    "warning_count",
    "policy_effect",
)


def canonical_execution_span_attributes(
    result: "ExecutionResult",
    *,
    task_type: str,
    policy_effect: str,
) -> dict[str, Any]:
    """Return the canonical span attribute dict for a completed adapter execution.

    Parameters
    ----------
    result:
        The ``ExecutionResult`` returned by ``ExecutionEngine.execute()``.
        Must have ``risk_tier``, ``adapter_name``, ``source_type``, and
        ``execution_kind`` populated in ``result.metadata`` (done by the
        engine before this function is called).
    task_type:
        Task category string extracted from the task context.
    policy_effect:
        The governance effect that permitted this execution (e.g. ``"allow"``).

    Returns
    -------
    dict[str, Any]
        Keys are exactly ``CANONICAL_EXECUTION_SPAN_KEYS``.
    """
    return {
        "agent_id": result.agent_id,
        "adapter_name": result.metadata.get("adapter_name", ""),
        "task_type": task_type,
        "risk_tier": result.metadata.get("risk_tier", ""),
        "source_type": result.metadata.get("source_type", ""),
        "execution_kind": result.metadata.get("execution_kind", ""),
        "success": result.success,
        "duration_ms": result.duration_ms,
        "cost": result.cost,
        "token_count": result.token_count,
        "warning_count": len(result.warnings),
        "policy_effect": policy_effect,
    }
