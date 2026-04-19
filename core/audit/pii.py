"""PII detection policy — §6.4 Data Governance.

Stateless, regex-driven detector that classifies personally identifiable
information in string fields, plus a thin composition helper that scans
the records referenced by a ``RetentionReport``.

Scope-narrow:

- **Detection, not redaction.** The detector reports *where* and *what
  kind* of PII lives in a string, but emits a fixed placeholder
  (``"[email]"``, ``"[ipv4]"``, …) in place of the match. The original
  bytes never leave the detector, so dumping a ``PiiScanResult`` to
  disk or a log cannot re-leak PII.
- **No mutation.** Stores and ``RetentionReport`` instances are
  read-only inputs.
- **No audit stack.** The detector does not write to any log; callers
  own the audit trail, identical to the retention pruner's contract.
- **No second policy surface for retention.** ``PiiPolicy`` is
  orthogonal to ``RetentionPolicy`` — detection does not re-evaluate
  retention windows, and retention does not re-evaluate PII.

Stdlib + pydantic only.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.approval.store import ApprovalStore
from core.audit.retention import RetentionReport
from core.audit.trace_store import TraceStore

PiiCategory = Literal[
    "email",
    "ipv4",
    "ipv6",
    "phone",
    "credit_card",
    "iban",
    "api_key",
]

_BUILTIN_PATTERNS: dict[PiiCategory, str] = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "ipv6": r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b",
    "phone": r"\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{2,4}[\s\-.]?\d{2,4}[\s\-.]?\d{0,4}",
    "credit_card": r"\b(?:\d[ -]?){13,19}\b",
    "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
    "api_key": r"\b(?:sk-|xoxb-|xoxp-|AKIA|ghp_|gho_|github_pat_)[A-Za-z0-9_-]{8,}\b",
}

DEFAULT_PII_CATEGORIES: tuple[PiiCategory, ...] = (
    "email",
    "ipv4",
    "credit_card",
    "iban",
    "api_key",
)
"""Conservative default set — high-precision categories only.

``ipv6`` and ``phone`` are excluded because their regexes are inherently
prone to false positives on non-PII numeric content. Callers can opt in
via ``PiiPolicy(enabled_categories=[...])``.
"""


class PiiPattern(BaseModel):
    """Custom pattern supplied by a caller — tagged with its own category name."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=64)
    pattern: str = Field(min_length=1, max_length=1024)
    description: str = Field(default="", max_length=512)

    @field_validator("category")
    @classmethod
    def _no_builtin_clash(cls, value: str) -> str:
        if value in _BUILTIN_PATTERNS:
            raise ValueError(
                f"category '{value}' collides with a built-in PII category"
            )
        return value

    @field_validator("pattern")
    @classmethod
    def _must_compile(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"invalid regex: {exc}") from exc
        return value


class PiiPolicy(BaseModel):
    """Frozen PII detection policy.

    Declares which built-in categories are active plus any caller-defined
    patterns. Orthogonal to ``RetentionPolicy``: no retention window,
    no deletion rules.
    """

    model_config = ConfigDict(extra="forbid")

    enabled_categories: list[PiiCategory] = Field(
        default_factory=lambda: list(DEFAULT_PII_CATEGORIES),
        description="Built-in categories to detect. Empty list = none of the built-ins active.",
    )
    custom_patterns: list[PiiPattern] = Field(default_factory=list)

    @field_validator("enabled_categories")
    @classmethod
    def _dedupe(cls, values: list[PiiCategory]) -> list[PiiCategory]:
        seen: set[str] = set()
        deduped: list[PiiCategory] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                deduped.append(value)
        return deduped


class PiiMatch(BaseModel):
    """One detected PII occurrence — redacted placeholder only, never raw bytes."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=64)
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)
    placeholder: str = Field(
        min_length=1,
        max_length=64,
        description="Fixed mask (e.g. '[email]'). Never contains raw PII.",
    )


class PiiFinding(BaseModel):
    """PII matches found within a single logical field of a record."""

    model_config = ConfigDict(extra="forbid")

    source_path: str = Field(
        min_length=1,
        max_length=256,
        description="Dotted path identifying the scanned field (e.g. 'approval.reason').",
    )
    matches: list[PiiMatch]


class PiiScanResult(BaseModel):
    """Aggregate result of a scan over one or more text fields."""

    model_config = ConfigDict(extra="forbid")

    scanned_fields: int = Field(ge=0)
    findings: list[PiiFinding] = Field(default_factory=list)
    category_counts: dict[str, int] = Field(default_factory=dict)


class PiiDetector:
    """Stateless PII scanner driven by a ``PiiPolicy``.

    The detector compiles the policy's patterns once at construction time
    and exposes read-only scan methods. It holds no per-call state and
    is safe to share across threads.
    """

    def __init__(self, *, policy: PiiPolicy) -> None:
        self.policy = policy
        self._compiled: list[tuple[str, re.Pattern[str]]] = []
        for category in policy.enabled_categories:
            self._compiled.append((category, re.compile(_BUILTIN_PATTERNS[category])))
        for custom in policy.custom_patterns:
            self._compiled.append((custom.category, re.compile(custom.pattern)))

    def scan_text(self, text: str) -> list[PiiMatch]:
        """Return redacted matches ordered by position of first occurrence."""
        if not text:
            return []
        matches: list[PiiMatch] = []
        for category, regex in self._compiled:
            placeholder = f"[{category}]"
            for hit in regex.finditer(text):
                matches.append(
                    PiiMatch(
                        category=category,
                        span_start=hit.start(),
                        span_end=hit.end(),
                        placeholder=placeholder,
                    )
                )
        matches.sort(key=lambda m: (m.span_start, m.span_end))
        return matches

    def scan_fields(self, fields: dict[str, str]) -> PiiScanResult:
        """Scan a mapping of ``{source_path: text}``.

        Empty / missing strings are counted toward ``scanned_fields`` but
        never emit a finding.
        """
        findings: list[PiiFinding] = []
        category_counts: dict[str, int] = {}
        for path, text in fields.items():
            if not isinstance(text, str) or not text:
                continue
            matches = self.scan_text(text)
            if matches:
                findings.append(PiiFinding(source_path=path, matches=matches))
                for match in matches:
                    category_counts[match.category] = (
                        category_counts.get(match.category, 0) + 1
                    )
        return PiiScanResult(
            scanned_fields=len(fields),
            findings=findings,
            category_counts=category_counts,
        )


class PiiCandidateAnnotation(BaseModel):
    """PII findings scoped to one retention candidate."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["trace", "approval"]
    record_id: str
    finding_count: int = Field(ge=0)
    result: PiiScanResult


class PiiRetentionAnnotation(BaseModel):
    """Per-candidate PII annotations for a ``RetentionReport``.

    Produced by :func:`annotate_retention_candidates`. Read-only and
    additive — does not mutate the source report.
    """

    model_config = ConfigDict(extra="forbid")

    total_candidates: int = Field(ge=0)
    candidates_with_findings: int = Field(ge=0)
    annotations: list[PiiCandidateAnnotation] = Field(default_factory=list)
    category_counts: dict[str, int] = Field(default_factory=dict)


def annotate_retention_candidates(
    *,
    detector: PiiDetector,
    report: RetentionReport,
    trace_store: TraceStore,
    approval_store: ApprovalStore,
) -> PiiRetentionAnnotation:
    """Scan each candidate in ``report`` for PII.

    Trace candidates contribute ``workflow_name``, ``status``, per-span
    ``name`` / attribute string values, and span event messages.
    Approval candidates contribute ``task_summary``, ``reason``, and
    ``proposed_action_summary``.

    The function is fully read-only: neither store is mutated, and the
    report is never rewritten. Missing records (concurrent deletion) are
    skipped — their annotation entry is still emitted with an empty
    ``result`` so the caller can reconcile IDs.
    """
    annotations: list[PiiCandidateAnnotation] = []
    category_counts: dict[str, int] = {}
    with_findings = 0

    for candidate in report.candidates:
        if candidate.kind == "trace":
            fields = _collect_trace_fields(trace_store, candidate.record_id)
        else:
            fields = _collect_approval_fields(approval_store, candidate.record_id)
        result = detector.scan_fields(fields)
        annotations.append(
            PiiCandidateAnnotation(
                kind=candidate.kind,
                record_id=candidate.record_id,
                finding_count=len(result.findings),
                result=result,
            )
        )
        if result.findings:
            with_findings += 1
        for category, count in result.category_counts.items():
            category_counts[category] = category_counts.get(category, 0) + count

    return PiiRetentionAnnotation(
        total_candidates=len(report.candidates),
        candidates_with_findings=with_findings,
        annotations=annotations,
        category_counts=category_counts,
    )


def _collect_trace_fields(
    trace_store: TraceStore, trace_id: str
) -> dict[str, str]:
    snapshot = trace_store.get_trace(trace_id)
    if snapshot is None:
        return {}
    fields: dict[str, str] = {
        f"trace:{trace_id}.workflow_name": snapshot.trace.workflow_name,
        f"trace:{trace_id}.status": snapshot.trace.status,
    }
    for key, value in snapshot.trace.metadata.items():
        if isinstance(value, str):
            fields[f"trace:{trace_id}.metadata.{key}"] = value
    for span in snapshot.spans:
        prefix = f"trace:{trace_id}.span:{span.span_id}"
        fields[f"{prefix}.name"] = span.name
        for attr_key, attr_value in span.attributes.items():
            if isinstance(attr_value, str):
                fields[f"{prefix}.attributes.{attr_key}"] = attr_value
        for index, event in enumerate(span.events):
            fields[f"{prefix}.events[{index}].message"] = event.message
    return fields


def _collect_approval_fields(
    approval_store: ApprovalStore, approval_id: str
) -> dict[str, str]:
    request = approval_store.get_request(approval_id)
    if request is None:
        return {}
    return {
        f"approval:{approval_id}.task_summary": request.task_summary,
        f"approval:{approval_id}.reason": request.reason,
        f"approval:{approval_id}.proposed_action_summary": request.proposed_action_summary,
    }


__all__ = [
    "DEFAULT_PII_CATEGORIES",
    "PiiCandidateAnnotation",
    "PiiCategory",
    "PiiDetector",
    "PiiFinding",
    "PiiMatch",
    "PiiPattern",
    "PiiPolicy",
    "PiiRetentionAnnotation",
    "PiiScanResult",
    "annotate_retention_candidates",
]
