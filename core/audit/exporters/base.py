"""Base exporter contract for optional trace exports."""

from __future__ import annotations

from core.audit.trace_models import TraceSnapshot


class BaseTraceExporter:
    """Optional exporter interface for future OTel-like sinks."""

    def export(self, snapshot: TraceSnapshot) -> None:
        raise NotImplementedError
