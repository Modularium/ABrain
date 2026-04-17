"""Retrieval governance boundary — query validation and trust enforcement.

Phase 3 — "Retrieval- und Wissensschicht", Step R1.

``RetrievalBoundary`` is the single policy enforcement point for all
retrieval operations in ABrain.  It enforces:

1. Scope restriction — no "critical_action" scope exists; planning scope has
   tighter trust requirements than explanation/assistance scopes.
2. Trust/scope matrix — UNTRUSTED sources are forbidden for planning scope;
   EXTERNAL sources trigger advisory warnings in planning scope.
3. Query validation — empty or oversized queries are rejected before any
   backend call.
4. Result annotation — warnings are injected into results when lower-trust
   content is returned so downstream consumers can decide how much weight
   to give the content.

Design invariants
-----------------
- Pure stateless class — no backend calls, no singletons, no side effects.
- Does not implement retrieval — it wraps whatever backend is provided later.
- Raises ``RetrievalPolicyViolation`` (not a generic exception) so callers can
  distinguish governance blocks from retrieval errors.
- Never suppresses or modifies ``content`` — only adds ``warnings``.
"""

from __future__ import annotations

from .models import RetrievalQuery, RetrievalResult, RetrievalScope, SourceTrust


class RetrievalPolicyViolation(RuntimeError):
    """Raised when a retrieval query violates a governance rule.

    Analogous to ``PolicyViolationError`` in the governance layer.  Callers
    should catch this explicitly rather than relying on a generic exception.
    """

    def __init__(self, reason: str, query: RetrievalQuery) -> None:
        self.reason = reason
        self.query = query
        super().__init__(reason)


# ---------------------------------------------------------------------------
# Trust/scope permission matrix
# ---------------------------------------------------------------------------

# Maps (scope, trust) → (permitted: bool, warning: str | None)
# "permitted" means the query may proceed.
# "warning" is injected into results when not None.
_TRUST_SCOPE_MATRIX: dict[
    tuple[RetrievalScope, SourceTrust], tuple[bool, str | None]
] = {
    # EXPLANATION — open scope; all trust levels allowed
    (RetrievalScope.EXPLANATION, SourceTrust.TRUSTED): (True, None),
    (RetrievalScope.EXPLANATION, SourceTrust.INTERNAL): (True, None),
    (RetrievalScope.EXPLANATION, SourceTrust.EXTERNAL): (True, None),
    (RetrievalScope.EXPLANATION, SourceTrust.UNTRUSTED): (
        True,
        "Result from UNTRUSTED source used for explanation — verify before citing.",
    ),
    # ASSISTANCE — open scope; all trust levels allowed
    (RetrievalScope.ASSISTANCE, SourceTrust.TRUSTED): (True, None),
    (RetrievalScope.ASSISTANCE, SourceTrust.INTERNAL): (True, None),
    (RetrievalScope.ASSISTANCE, SourceTrust.EXTERNAL): (True, None),
    (RetrievalScope.ASSISTANCE, SourceTrust.UNTRUSTED): (
        True,
        "Result from UNTRUSTED source used for assistance — treat as advisory only.",
    ),
    # PLANNING — restricted scope
    (RetrievalScope.PLANNING, SourceTrust.TRUSTED): (True, None),
    (RetrievalScope.PLANNING, SourceTrust.INTERNAL): (True, None),
    (RetrievalScope.PLANNING, SourceTrust.EXTERNAL): (
        True,
        "Result from EXTERNAL source used for planning — validate provenance before acting on this.",
    ),
    (RetrievalScope.PLANNING, SourceTrust.UNTRUSTED): (
        False,
        None,  # Not reached — violation raised before result is produced
    ),
}


class RetrievalBoundary:
    """Stateless governance boundary for retrieval operations.

    Usage
    -----
    1. Call ``validate_query()`` before dispatching to the retrieval backend.
       Raises ``RetrievalPolicyViolation`` if the query violates a rule.
    2. Call ``annotate_results()`` on the raw backend results to inject
       trust warnings before returning to callers.

    Both methods are pure and free of side effects.
    """

    def validate_query(self, query: RetrievalQuery) -> None:
        """Validate that the query is permitted under governance rules.

        Raises
        ------
        RetrievalPolicyViolation
            When ``allowed_trust_levels`` contains ``UNTRUSTED`` and ``scope``
            is ``PLANNING`` — UNTRUSTED content must not inform planning.
        """
        if (
            query.scope == RetrievalScope.PLANNING
            and SourceTrust.UNTRUSTED in query.allowed_trust_levels
        ):
            raise RetrievalPolicyViolation(
                reason=(
                    f"UNTRUSTED sources are forbidden for scope '{query.scope}'. "
                    f"Use scope 'explanation' or 'assistance' for untrusted content, "
                    f"or restrict allowed_trust_levels to TRUSTED/INTERNAL/EXTERNAL."
                ),
                query=query,
            )

    def annotate_results(
        self, results: list[RetrievalResult], query: RetrievalQuery
    ) -> list[RetrievalResult]:
        """Inject governance warnings into results where the trust/scope matrix requires it.

        Does not modify ``content`` or ``score``.  Only appends to
        ``result.warnings``.  Returns the annotated list.

        For each result, looks up the (scope, trust) pair in the matrix.
        If a warning string is defined, it is appended to ``result.warnings``
        (only once — duplicate warnings are skipped).
        """
        annotated: list[RetrievalResult] = []
        for result in results:
            key = (query.scope, result.trust)
            _, warning = _TRUST_SCOPE_MATRIX.get(key, (True, None))
            if warning and warning not in result.warnings:
                updated = result.model_copy(
                    update={"warnings": result.warnings + [warning]}
                )
                annotated.append(updated)
            else:
                annotated.append(result)
        return annotated

    def check_planning_scope_trust(
        self, results: list[RetrievalResult], query: RetrievalQuery
    ) -> list[str]:
        """Return advisory messages for any result that would be problematic.

        Used as a lightweight pre-flight check without mutating results.
        Returns a list of warning strings; empty list means all results are
        within safe governance bounds for the given scope.
        """
        warnings: list[str] = []
        for result in results:
            key = (query.scope, result.trust)
            permitted, warning = _TRUST_SCOPE_MATRIX.get(key, (True, None))
            if not permitted:
                warnings.append(
                    f"Source '{result.source_id}' (trust={result.trust}) is not "
                    f"permitted for scope '{query.scope}'."
                )
            elif warning:
                warnings.append(warning)
        return warnings
