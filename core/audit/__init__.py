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
    ReplayDescriptor,
    ReplayStepInput,
    SpanRecord,
    TraceEvent,
    TraceRecord,
    TraceSnapshot,
)
from .trace_store import TraceStore
from .audit_export import (
    AUDIT_EXPORT_SCHEMA_VERSION,
    ApprovalExportEntry,
    AuditExport,
    AuditExporter,
    TraceExportEntry,
)
from .retention import (
    RetentionCandidate,
    RetentionPolicy,
    RetentionReport,
    RetentionScanner,
    RetentionTotals,
)
from .retention_pruner import (
    RetentionPruneOutcome,
    RetentionPruneResult,
    RetentionPruner,
)
from .pii import (
    DEFAULT_PII_CATEGORIES,
    PiiCandidateAnnotation,
    PiiCategory,
    PiiDetector,
    PiiFinding,
    PiiMatch,
    PiiPattern,
    PiiPolicy,
    PiiRetentionAnnotation,
    PiiScanResult,
    annotate_retention_candidates,
)

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
    "AUDIT_EXPORT_SCHEMA_VERSION",
    "ApprovalExportEntry",
    "AuditExport",
    "AuditExporter",
    "DEFAULT_PII_CATEGORIES",
    "ExplainabilityRecord",
    "PiiCandidateAnnotation",
    "PiiCategory",
    "PiiDetector",
    "PiiFinding",
    "PiiMatch",
    "PiiPattern",
    "PiiPolicy",
    "PiiRetentionAnnotation",
    "PiiScanResult",
    "ReplayDescriptor",
    "ReplayStepInput",
    "RetentionCandidate",
    "RetentionPolicy",
    "RetentionPruneOutcome",
    "RetentionPruneResult",
    "RetentionPruner",
    "RetentionReport",
    "RetentionScanner",
    "RetentionTotals",
    "SpanRecord",
    "TraceContext",
    "TraceEvent",
    "TraceExportEntry",
    "TraceRecord",
    "TraceSnapshot",
    "TraceStore",
    "add_span_event",
    "annotate_retention_candidates",
    "attach_trace_context",
    "audit_action",
    "create_trace_context",
    "finish_span",
    "record_error",
    "start_child_span",
]
