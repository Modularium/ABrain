"""Routing audit integration — dispatch attribution in TraceStore.

Phase 4 — "System-Level MoE und hybrides Modellrouting", Step M4.

``RoutingAuditor`` emits structured spans to the canonical ``TraceStore``
whenever a model dispatch completes or fails.  This makes every routing
decision attributable in the audit trail and enables KPI comparisons
between LOCAL/internal and external/hosted model paths.

Recorded KPIs per dispatch
--------------------------
- ``routing.request.purpose``           requested model purpose
- ``routing.request.prefer_local``      local-preference hint
- ``routing.request.require_tool_use``  capability requirement
- ``routing.request.require_structured_output``  capability requirement
- ``routing.request.task_id``           task attribution
- ``routing.result.model_id``           selected model
- ``routing.result.provider``           selected provider
- ``routing.result.tier``               selected tier (LOCAL/SMALL/MEDIUM/LARGE)
- ``routing.result.fallback_used``      whether any constraint was relaxed
- ``routing.result.fallback_reason``    which constraint was relaxed, or None
- ``routing.result.cost_per_1k_tokens`` actual cost if descriptor provided
- ``routing.result.p95_latency_ms``     actual latency if descriptor provided

Design invariants
-----------------
- ``TraceStore`` is the single Trace/Audit truth.  No second audit path.
- ``RoutingAuditor`` is NOT embedded in ``ModelDispatcher``.  The orchestration
  layer (or any caller with a trace context) calls the auditor after dispatch.
  This keeps the routing layer free of trace coupling.
- If no ``TraceStore`` is available (``store=None``), all methods are no-ops
  and return ``None``.  Dispatch always works without an auditor.
- Span attributes follow the canonical S19 convention:
  ``<subsystem>.<operation>.<attribute>``.
- Errors in audit emission are silently swallowed — they must never propagate
  to interrupt a routing decision.
- Analogous to ``RetrievalAuditor`` (R6) in structure and conventions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .dispatcher import ModelRoutingRequest, ModelRoutingResult

if TYPE_CHECKING:
    from core.audit.trace_store import TraceStore
    from core.audit.trace_models import SpanRecord
    from .models import ModelDescriptor

logger = logging.getLogger(__name__)


class RoutingAuditor:
    """Emit routing spans to ``TraceStore`` for dispatch attribution and KPI tracking.

    Usage
    -----
    >>> auditor = RoutingAuditor(trace_store)
    >>> # After a successful dispatch:
    >>> auditor.record_dispatch(trace_id, request, result)
    >>> # Optionally pass the selected descriptor for cost/latency KPIs:
    >>> auditor.record_dispatch(trace_id, request, result, descriptor=desc)
    >>> # After a NoModelAvailableError:
    >>> auditor.record_routing_failure(trace_id, request, error)

    When no ``TraceStore`` is provided (``store=None``), all calls are no-ops.
    """

    #: Span type used for all routing spans — keeps them queryable.
    SPAN_TYPE = "routing"

    def __init__(self, store: TraceStore | None) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_dispatch(
        self,
        trace_id: str,
        request: ModelRoutingRequest,
        result: ModelRoutingResult,
        *,
        descriptor: ModelDescriptor | None = None,
        parent_span_id: str | None = None,
    ) -> SpanRecord | None:
        """Record a completed routing decision as a finished span.

        Parameters
        ----------
        trace_id:
            The trace this dispatch belongs to.
        request:
            The ``ModelRoutingRequest`` that was dispatched.
        result:
            The ``ModelRoutingResult`` returned by ``ModelDispatcher.dispatch``.
        descriptor:
            Optional — the ``ModelDescriptor`` of the selected model.  When
            provided, actual ``cost_per_1k_tokens`` and ``p95_latency_ms``
            values are recorded for cost/latency KPI comparisons.
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
            name="routing.dispatch",
            parent_span_id=parent_span_id,
            start_attrs=_request_attributes(request),
            finish_attrs=_result_attributes(result, descriptor),
            status="ok",
        )

    def record_routing_failure(
        self,
        trace_id: str,
        request: ModelRoutingRequest,
        error: Exception,
        *,
        parent_span_id: str | None = None,
    ) -> SpanRecord | None:
        """Record a routing failure (``NoModelAvailableError``) as a finished span.

        Call this in the ``except NoModelAvailableError`` handler so that
        dispatch failures are attributable in the audit trail.

        Parameters
        ----------
        trace_id:
            The trace this failed dispatch belongs to.
        request:
            The ``ModelRoutingRequest`` that could not be fulfilled.
        error:
            The ``NoModelAvailableError`` (or any exception) that was raised.
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
            "routing.failure.reason": str(error)[:512],
            "routing.result.model_id": None,
            "routing.result.provider": None,
            "routing.result.tier": None,
            "routing.result.fallback_used": False,
            "routing.result.fallback_reason": None,
            "routing.result.cost_per_1k_tokens": None,
            "routing.result.p95_latency_ms": None,
        }
        return self._emit(
            trace_id=trace_id,
            name="routing.failed",
            parent_span_id=parent_span_id,
            start_attrs=_request_attributes(request),
            finish_attrs=finish_attrs,
            status="failed",
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
                "routing.audit_emit_failed trace_id=%s error=%s",
                trace_id,
                exc,
            )
            return None


# ---------------------------------------------------------------------------
# Attribute builders
# ---------------------------------------------------------------------------


def _request_attributes(request: ModelRoutingRequest) -> dict[str, Any]:
    """Span start-time attributes from the routing request."""
    return {
        "routing.request.purpose": str(request.purpose),
        "routing.request.task_id": request.task_id,
        "routing.request.prefer_local": request.prefer_local,
        "routing.request.require_tool_use": request.require_tool_use,
        "routing.request.require_structured_output": request.require_structured_output,
    }


def _result_attributes(
    result: ModelRoutingResult,
    descriptor: ModelDescriptor | None,
) -> dict[str, Any]:
    """Span finish-time attributes from the routing result.

    When a ``ModelDescriptor`` is provided, actual cost and latency values
    are included for KPI comparison between internal (LOCAL) and external paths.
    """
    attrs: dict[str, Any] = {
        "routing.result.model_id": result.model_id,
        "routing.result.provider": str(result.provider),
        "routing.result.tier": str(result.tier),
        "routing.result.fallback_used": result.fallback_used,
        "routing.result.fallback_reason": result.fallback_reason,
        "routing.result.cost_per_1k_tokens": (
            descriptor.cost_per_1k_tokens if descriptor is not None else None
        ),
        "routing.result.p95_latency_ms": (
            descriptor.p95_latency_ms if descriptor is not None else None
        ),
    }
    return attrs
