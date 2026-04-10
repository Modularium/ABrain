"""Best-effort trace context helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

from .trace_models import ExplainabilityRecord
from .trace_store import TraceStore

logger = logging.getLogger(__name__)


class TraceContext:
    """Best-effort helper around :class:`TraceStore` for runtime tracing."""

    def __init__(
        self,
        store: TraceStore | None,
        trace_id: str | None,
        *,
        workflow_name: str | None = None,
    ) -> None:
        self.store = store
        self.trace_id = trace_id
        self.workflow_name = workflow_name
        self.warnings: list[str] = []

    @property
    def enabled(self) -> bool:
        return self.store is not None and self.trace_id is not None

    @classmethod
    def create(
        cls,
        store: TraceStore | None,
        *,
        workflow_name: str,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> "TraceContext":
        if store is None:
            return cls(None, None, workflow_name=workflow_name)
        try:
            record = store.create_trace(
                workflow_name,
                task_id=task_id,
                metadata=metadata,
                trace_id=trace_id,
            )
            return cls(store, record.trace_id, workflow_name=workflow_name)
        except Exception as exc:  # pragma: no cover - defensive containment
            context = cls(None, None, workflow_name=workflow_name)
            context._record_warning("trace_create_failed", exc)
            return context

    @classmethod
    def attach(
        cls,
        store: TraceStore | None,
        *,
        trace_id: str | None,
        workflow_name: str | None = None,
    ) -> "TraceContext":
        if store is None or trace_id is None:
            return cls(None, None, workflow_name=workflow_name)
        try:
            if store.get_trace(trace_id) is None:
                raise KeyError(f"unknown trace_id: {trace_id}")
            return cls(store, trace_id, workflow_name=workflow_name)
        except Exception as exc:  # pragma: no cover - defensive containment
            context = cls(None, None, workflow_name=workflow_name)
            context._record_warning("trace_attach_failed", exc)
            return context

    def start_child_span(
        self,
        *,
        span_type: str,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str | None:
        if not self.enabled:
            return None
        try:
            span = self.store.start_span(
                self.trace_id,
                span_type=span_type,
                name=name,
                parent_span_id=parent_span_id,
                attributes=attributes,
            )
            return span.span_id
        except Exception as exc:  # pragma: no cover - defensive containment
            self._record_warning("trace_start_span_failed", exc)
            return None

    def finish_span(
        self,
        span_id: str | None,
        *,
        status: str,
        attributes: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled or span_id is None:
            return
        try:
            self.store.finish_span(
                span_id,
                status=status,
                attributes=attributes,
                error=error,
            )
        except Exception as exc:  # pragma: no cover - defensive containment
            self._record_warning("trace_finish_span_failed", exc)

    def add_span_event(
        self,
        span_id: str | None,
        *,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled or span_id is None:
            return
        try:
            self.store.add_event(
                span_id,
                event_type=event_type,
                message=message,
                payload=payload,
            )
        except Exception as exc:  # pragma: no cover - defensive containment
            self._record_warning("trace_add_event_failed", exc)

    def record_error(
        self,
        span_id: str | None,
        error: Exception,
        *,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if span_id is not None:
            self.add_span_event(
                span_id,
                event_type="error",
                message=message,
                payload={
                    **(payload or {}),
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                },
            )
            self.finish_span(
                span_id,
                status="failed",
                error={
                    "error_type": error.__class__.__name__,
                    "error": str(error),
                },
            )

    def store_explainability(self, record: ExplainabilityRecord) -> None:
        if not self.enabled:
            return
        try:
            self.store.store_explainability(record)
        except Exception as exc:  # pragma: no cover - defensive containment
            self._record_warning("trace_explainability_failed", exc)

    def finish_trace(self, *, status: str, metadata: dict[str, Any] | None = None) -> None:
        if not self.enabled:
            return
        try:
            self.store.finish_trace(
                self.trace_id,
                status=status,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive containment
            self._record_warning("trace_finish_failed", exc)

    def summary(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "workflow_name": self.workflow_name,
            "enabled": self.enabled,
            "warnings": list(self.warnings),
        }

    def _record_warning(self, code: str, exc: Exception) -> None:
        warning = f"{code}:{exc.__class__.__name__}"
        self.warnings.append(warning)
        logger.warning(
            json.dumps(
                {
                    "event": code,
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "trace_id": self.trace_id,
                    "workflow_name": self.workflow_name,
                },
                sort_keys=True,
            )
        )


def create_trace_context(
    store: TraceStore | None,
    *,
    workflow_name: str,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> TraceContext:
    return TraceContext.create(
        store,
        workflow_name=workflow_name,
        task_id=task_id,
        metadata=metadata,
        trace_id=trace_id,
    )


def attach_trace_context(
    store: TraceStore | None,
    *,
    trace_id: str | None,
    workflow_name: str | None = None,
) -> TraceContext:
    return TraceContext.attach(
        store,
        trace_id=trace_id,
        workflow_name=workflow_name,
    )


def start_child_span(
    trace_context: TraceContext | None,
    *,
    span_type: str,
    name: str,
    parent_span_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> str | None:
    if trace_context is None:
        return None
    return trace_context.start_child_span(
        span_type=span_type,
        name=name,
        parent_span_id=parent_span_id,
        attributes=attributes,
    )


def finish_span(
    trace_context: TraceContext | None,
    span_id: str | None,
    *,
    status: str,
    attributes: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    if trace_context is None:
        return
    trace_context.finish_span(
        span_id,
        status=status,
        attributes=attributes,
        error=error,
    )


def record_error(
    trace_context: TraceContext | None,
    span_id: str | None,
    error: Exception,
    *,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if trace_context is None:
        return
    trace_context.record_error(span_id, error, message=message, payload=payload)


def add_span_event(
    trace_context: TraceContext | None,
    span_id: str | None,
    *,
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if trace_context is None:
        return
    trace_context.add_span_event(
        span_id,
        event_type=event_type,
        message=message,
        payload=payload,
    )
