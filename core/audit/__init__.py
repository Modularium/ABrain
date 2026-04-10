"""Audit, trace and explainability helpers for ABrain."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from core.audit_log import AuditEntry, AuditLog

from .context import (
    TraceContext,
    add_span_event,
    attach_trace_context,
    create_trace_context,
    finish_span,
    record_error,
    start_child_span,
)
from .trace_models import (
    ExplainabilityRecord,
    SpanRecord,
    TraceEvent,
    TraceRecord,
    TraceSnapshot,
)
from .trace_store import TraceStore

_audit = AuditLog(log_dir=os.getenv("AUDIT_LOG_DIR", "audit"))


def audit_action(
    actor: str,
    action: str,
    context_id: str,
    detail: dict[str, Any],
    signature: str | None = None,
) -> str:
    """Write a legacy JSONL audit entry and return its id."""
    entry = AuditEntry(
        timestamp=datetime.utcnow().isoformat(),
        actor=actor,
        action=action,
        context_id=context_id,
        detail=detail,
        signature=signature,
    )
    return _audit.write(entry)


__all__ = [
    "ExplainabilityRecord",
    "SpanRecord",
    "TraceContext",
    "TraceEvent",
    "TraceRecord",
    "TraceSnapshot",
    "TraceStore",
    "add_span_event",
    "attach_trace_context",
    "audit_action",
    "create_trace_context",
    "finish_span",
    "record_error",
    "start_child_span",
]
