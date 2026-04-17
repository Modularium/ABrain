"""Manifest-driven input and output validation for execution adapters.

Phase 2 — "Eingabe-/Ausgabe-Schemas erzwingen".

Input validation
----------------
``validate_required_metadata`` enforces the ``required_metadata_keys`` contract
declared in an ``AdapterManifest`` against an ``AgentDescriptor``.

Output validation
-----------------
``validate_result`` enforces structural invariants on an ``ExecutionResult``
and the ``required_result_metadata_keys`` contract declared in the manifest.

``result_warnings`` returns soft capability-based warnings when an adapter
declares it supports cost or token reporting but the result omits those fields.

All functions are pure: no side effects, no registry access, no singletons.
They raise ``ValueError`` (same type as adapter-specific checks) so callers
see a uniform error surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.decision.agent_descriptor import AgentDescriptor
from core.execution.adapters.manifest import AdapterManifest

if TYPE_CHECKING:
    from core.execution.adapters.base import ExecutionResult


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def missing_metadata_keys(
    manifest: AdapterManifest, descriptor: AgentDescriptor
) -> list[str]:
    """Return the required metadata keys absent from ``descriptor.metadata``.

    Returns an empty list when all required keys are present.
    """
    return [
        key
        for key in manifest.required_metadata_keys
        if key not in descriptor.metadata
    ]


def validate_required_metadata(
    manifest: AdapterManifest, descriptor: AgentDescriptor
) -> None:
    """Raise ``ValueError`` if any required metadata key is absent.

    Raises
    ------
    ValueError
        When one or more required keys are missing, naming the adapter,
        the descriptor, and the absent keys.
    """
    absent = missing_metadata_keys(manifest, descriptor)
    if absent:
        raise ValueError(
            f"Adapter '{manifest.adapter_name}' requires metadata keys "
            f"{absent!r} but agent '{descriptor.agent_id}' is missing them."
        )


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------


def missing_result_metadata_keys(
    manifest: AdapterManifest, result: "ExecutionResult"
) -> list[str]:
    """Return ``required_result_metadata_keys`` absent from a success result.

    Error results (``success=False``) are exempt: error paths may short-circuit
    before populating result metadata.  Returns an empty list for error results.
    """
    if not result.success:
        return []
    return [
        key
        for key in manifest.required_result_metadata_keys
        if key not in result.metadata
    ]


def validate_result(
    manifest: AdapterManifest, result: "ExecutionResult"
) -> None:
    """Raise ``ValueError`` when an ``ExecutionResult`` violates structural contracts.

    Checks (in order):
    1. ``agent_id`` must be non-empty.
    2. If ``success=True``: ``error`` must be ``None``.
    3. If ``success=False``: ``error`` must be present with a non-empty
       ``error_code``.
    4. On success: all ``manifest.required_result_metadata_keys`` must be
       present in ``result.metadata``.

    Raises
    ------
    ValueError
        On the first violated contract, with a message naming the adapter.
    """
    adapter = manifest.adapter_name

    if not result.agent_id:
        raise ValueError(
            f"Adapter '{adapter}' returned a result with an empty agent_id."
        )

    if result.success and result.error is not None:
        raise ValueError(
            f"Adapter '{adapter}' returned success=True but also set error="
            f"{result.error!r}. Success results must have error=None."
        )

    if not result.success:
        if result.error is None:
            raise ValueError(
                f"Adapter '{adapter}' returned success=False without an error "
                f"object. Failure results must set error with a non-empty error_code."
            )
        if not str(result.error.error_code).strip():
            raise ValueError(
                f"Adapter '{adapter}' returned success=False with an empty "
                f"error_code. Failure results must have a non-empty error_code."
            )

    absent = missing_result_metadata_keys(manifest, result)
    if absent:
        raise ValueError(
            f"Adapter '{adapter}' returned a success result missing required "
            f"result metadata keys {absent!r}."
        )


def result_warnings(
    manifest: AdapterManifest, result: "ExecutionResult"
) -> list[str]:
    """Return soft capability-based warnings for a result.

    These warnings indicate that the adapter declared a capability
    (cost or token reporting) but the result does not include the
    corresponding field.  They are non-fatal — callers may attach them to
    the result's warning list for observability.

    Only checked for success results; error results are exempt.
    """
    if not result.success:
        return []
    warnings: list[str] = []
    caps = manifest.capabilities
    if caps.supports_cost_reporting and result.cost is None:
        warnings.append(
            f"Adapter '{manifest.adapter_name}' declares supports_cost_reporting "
            f"but result.cost is None."
        )
    if caps.supports_token_reporting and result.token_count is None:
        warnings.append(
            f"Adapter '{manifest.adapter_name}' declares supports_token_reporting "
            f"but result.token_count is None."
        )
    return warnings


def budget_warnings(
    manifest: AdapterManifest, result: "ExecutionResult"
) -> list[str]:
    """Return soft budget-violation warnings for a result.

    Checks the three budget fields declared in ``manifest.budget`` against
    the corresponding fields on ``result``.  A violation is emitted when the
    result field is populated *and* exceeds the declared limit.

    All violations are non-fatal warnings: cost, duration and token counts are
    only known post-execution, so enforcement is advisory.  Operators that need
    hard limits must enforce them at the infrastructure level (pre-execution
    timeout, spending caps in provider dashboards).

    Called for both success and error results so that runaway executions are
    visible in the trace even when the adapter ultimately fails.
    """
    warnings: list[str] = []
    budget = manifest.budget
    name = manifest.adapter_name

    if (
        budget.max_cost_usd is not None
        and result.cost is not None
        and result.cost > budget.max_cost_usd
    ):
        warnings.append(
            f"Adapter '{name}' exceeded max_cost_usd budget: "
            f"{result.cost:.4f} > {budget.max_cost_usd:.4f} USD."
        )

    if (
        budget.max_duration_ms is not None
        and result.duration_ms is not None
        and result.duration_ms > budget.max_duration_ms
    ):
        warnings.append(
            f"Adapter '{name}' exceeded max_duration_ms budget: "
            f"{result.duration_ms} > {budget.max_duration_ms} ms."
        )

    if (
        budget.max_tokens is not None
        and result.token_count is not None
        and result.token_count > budget.max_tokens
    ):
        warnings.append(
            f"Adapter '{name}' exceeded max_tokens budget: "
            f"{result.token_count} > {budget.max_tokens} tokens."
        )

    return warnings
