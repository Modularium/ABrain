"""Retrieval audit integration — source attribution in TraceStore.

Phase 3 — "Retrieval- und Wissensschicht", Step R6.

``RetrievalAuditor`` emits structured spans to the canonical ``TraceStore``
whenever a retrieval operation completes or is blocked.  This makes every
retrieval operation attributable in the audit trail.

Design invariants
-----------------
- ``TraceStore`` is the single Trace/Audit truth.  No second audit path.
- ``RetrievalAuditor`` is NOT embedded in the retrievers.  The orchestration
  layer (or any caller with a trace context) is responsible for calling the
  auditor.  This keeps the retrieval layer free of trace coupling.
- If no ``TraceStore`` is available (``store=None``), all methods are no-ops
  and return ``None``.  Retrieval always works without an auditor.
- Span attributes follow the canonical convention established in S19:
  ``<subsystem>.<operation>.<attribute>``.
- Errors in audit emission are silently swallowed — they must never
  propagate to interrupt a retrieval operation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .models import RetrievalQuery, RetrievalResult

if TYPE_CHECKING:
    from core.audit.trace_store import TraceStore
    from core.audit.trace_models import SpanRecord

logger = logging.getLogger(__name__)


class RetrievalAuditor:
    """Emit retrieval spans to ``TraceStore`` for source attribution.

    Usage
    -----
    >>> auditor = RetrievalAuditor(trace_store)
    >>> # After a successful retrieval:
    >>> auditor.record_retrieval(trace_id, query, results)
    >>> # After a RetrievalPolicyViolation (injection block):
    >>> auditor.record_injection_block(trace_id, query, violation)

    When no ``TraceStore`` is provided (``store=None``), all calls are no-ops.
    """

    #: Span type used for all retrieval spans — keeps them queryable.
    SPAN_TYPE = "retrieval"

    def __init__(self, store: TraceStore | None) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_retrieval(
        self,
        trace_id: str,
        query: RetrievalQuery,
        results: list[RetrievalResult],
        *,
        parent_span_id: str | None = None,
    ) -> SpanRecord | None:
        """Record a completed retrieval as a finished span.

        Parameters
        ----------
        trace_id:
            The trace this retrieval belongs to.
        query:
            The retrieval query (scope, task_id, query_text preserved for attribution).
        results:
            The final result list after boundary annotation and injection scan.
        parent_span_id:
            Optional parent span for nesting within a larger trace tree.

        Returns
        -------
        SpanRecord | None
            The finished span, or ``None`` when no store is configured or
            an error occurs during emission.
        """
        if self._store is None:
            return None
        return self._emit(
            trace_id=trace_id,
            name="retrieval.query",
            parent_span_id=parent_span_id,
            start_attrs=_query_attributes(query),
            finish_attrs=_result_attributes(results),
            status="ok",
            injection_blocked=False,
        )

    def record_injection_block(
        self,
        trace_id: str,
        query: RetrievalQuery,
        violation: Exception,
        *,
        parent_span_id: str | None = None,
    ) -> SpanRecord | None:
        """Record a retrieval that was blocked by prompt-injection detection.

        Call this in the ``except RetrievalPolicyViolation`` handler so that
        blocked attempts are attributable in the audit trail.

        Parameters
        ----------
        trace_id:
            The trace this blocked retrieval belongs to.
        query:
            The retrieval query that triggered the block.
        violation:
            The ``RetrievalPolicyViolation`` that was raised.
        parent_span_id:
            Optional parent span.

        Returns
        -------
        SpanRecord | None
            The finished span, or ``None`` when no store is configured.
        """
        if self._store is None:
            return None
        finish_attrs: dict[str, Any] = {
            "retrieval.results.count": 0,
            "retrieval.results.sources": [],
            "retrieval.warnings.count": 0,
            "retrieval.injection_blocked": True,
            "retrieval.injection_reason": str(violation)[:512],
        }
        return self._emit(
            trace_id=trace_id,
            name="retrieval.blocked",
            parent_span_id=parent_span_id,
            start_attrs=_query_attributes(query),
            finish_attrs=finish_attrs,
            status="blocked",
            injection_blocked=True,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(
        self,
        *,
        trace_id: str,
        name: str,
        parent_span_id: str | None,
        start_attrs: dict[str, Any],
        finish_attrs: dict[str, Any],
        status: str,
        injection_blocked: bool,
    ) -> SpanRecord | None:
        """Create and immediately finish a span.  Errors are swallowed."""
        try:
            span = self._store.start_span(
                trace_id,
                span_type=self.SPAN_TYPE,
                name=name,
                parent_span_id=parent_span_id,
                attributes=start_attrs,
            )
            return self._store.finish_span(
                span.span_id,
                status=status,
                attributes=finish_attrs,
            )
        except Exception as exc:
            logger.warning(
                "retrieval.audit_emit_failed trace_id=%s error=%s",
                trace_id,
                exc,
            )
            return None


# ---------------------------------------------------------------------------
# Attribute builders
# ---------------------------------------------------------------------------


def _query_attributes(query: RetrievalQuery) -> dict[str, Any]:
    """Span start-time attributes from the retrieval query."""
    return {
        "retrieval.query.scope": query.scope,
        "retrieval.query.task_id": query.task_id,
    }


def _result_attributes(results: list[RetrievalResult]) -> dict[str, Any]:
    """Span finish-time attributes from the retrieval results."""
    sources = [
        {
            "source_id": r.source_id,
            "trust": r.trust,
            "provenance": r.provenance,
        }
        for r in results
    ]
    warnings_count = sum(len(r.warnings) for r in results)
    return {
        "retrieval.results.count": len(results),
        "retrieval.results.sources": sources,
        "retrieval.warnings.count": warnings_count,
        "retrieval.injection_blocked": False,
    }
