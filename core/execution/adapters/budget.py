"""Adapter runtime budget limits and static isolation requirements.

Phase 2 — "Kosten- und Latenzbudgets pro Adapter einführen" and
           "Sandboxing-/Isolation-Regeln definieren".

``AdapterBudget``
    Soft budget ceilings declared per adapter.  All limits are optional; None
    means unconstrained.  Enforcement is post-execution: ``budget_warnings()``
    in ``validation.py`` returns a list of violation messages that the engine
    appends to ``ExecutionResult.warnings``.  Pre-execution hard timeouts are
    an operator-level concern handled outside this module.

``IsolationRequirements``
    Static declarations of what the adapter needs from its deployment
    environment.  These are operator-facing facts, not runtime enforcement —
    the adapter states what it requires; the operator enforces it via
    containers, seccomp profiles, network policies, etc.  Declarations are
    surfaced in the manifest for policy review and audit.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AdapterBudget(BaseModel):
    """Per-adapter soft budget ceilings.

    Attributes
    ----------
    max_cost_usd:
        Maximum acceptable cost in USD for a single execution.  Exceeding this
        emits a warning on the result; the result is not rejected (enforcement
        is advisory for cost because cost is only known post-execution).
    max_duration_ms:
        Maximum acceptable wall-clock duration in milliseconds.  Exceeding
        this emits a warning; actual pre-execution timeout is the operator's
        responsibility (e.g. ``asyncio.wait_for``, subprocess ``timeout``).
    max_tokens:
        Maximum acceptable token count (input + output combined) for adapters
        that report token usage.  Exceeding this emits a warning.
    """

    model_config = ConfigDict(extra="forbid")

    max_cost_usd: float | None = Field(default=None, ge=0.0)
    max_duration_ms: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)


class IsolationRequirements(BaseModel):
    """Static isolation facts declared by an adapter.

    These describe what the adapter needs from its deployment environment.
    They are used for operator review, policy matching, and audit — not for
    in-process enforcement.

    Attributes
    ----------
    network_access_required:
        True if the adapter makes outbound network calls.  Corresponds to
        ``ExecutionCapabilities.requires_network`` on the same adapter.
    filesystem_write_required:
        True if the adapter writes to the local filesystem (directly or via
        a subprocess it spawns).
    process_spawn_required:
        True if the adapter spawns a subprocess.  Corresponds to
        ``ExecutionCapabilities.requires_local_process``.
    privileged_operation:
        True if the adapter may perform privileged operations (e.g. package
        installation, Docker-in-Docker, OS-level changes).
    """

    model_config = ConfigDict(extra="forbid")

    network_access_required: bool = False
    filesystem_write_required: bool = False
    process_spawn_required: bool = False
    privileged_operation: bool = False
