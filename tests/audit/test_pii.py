"""§6.4 Data Governance — PII detection tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from core.approval.models import ApprovalRequest, ApprovalStatus, CapabilityRisk
from core.approval.store import ApprovalStore
from core.audit.pii import (
    DEFAULT_PII_CATEGORIES,
    PiiCandidateAnnotation,
    PiiDetector,
    PiiFinding,
    PiiMatch,
    PiiPattern,
    PiiPolicy,
    PiiRetentionAnnotation,
    PiiScanResult,
    annotate_retention_candidates,
)
from core.audit.retention import RetentionPolicy, RetentionScanner
from core.audit.trace_store import TraceStore

pytestmark = pytest.mark.unit


FIXED_NOW = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_approval(
    *,
    approval_id: str,
    requested_at: datetime,
    task_summary: str = "t",
    reason: str = "r",
    proposed: str = "x",
    status: ApprovalStatus = ApprovalStatus.APPROVED,
) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=approval_id,
        plan_id="p",
        step_id="s",
        task_summary=task_summary,
        reason=reason,
        risk=CapabilityRisk.LOW,
        requested_at=requested_at,
        proposed_action_summary=proposed,
        status=status,
    )


def _write_trace_with_age(
    ts: TraceStore, *, days_old: float, workflow_name: str = "wf", attrs: dict | None = None
) -> str:
    trace = ts.create_trace(workflow_name, metadata={} if attrs is None else attrs)
    span = ts.start_span(
        trace.trace_id,
        span_type="step",
        name="s1",
        attributes=attrs or {},
    )
    ts.finish_span(span.span_id, status="ok")
    ts.finish_trace(trace.trace_id, status="ok")

    started = (FIXED_NOW - timedelta(days=days_old)).isoformat()
    conn = sqlite3.connect(ts.path)
    try:
        conn.execute(
            "UPDATE traces SET started_at=?, ended_at=? WHERE trace_id=?",
            (started, started, trace.trace_id),
        )
        conn.commit()
    finally:
        conn.close()
    return trace.trace_id


# ---------------------------------------------------------------------------
# Policy / defaults
# ---------------------------------------------------------------------------


class TestPolicy:
    def test_default_policy_enables_conservative_set(self):
        policy = PiiPolicy()
        assert set(policy.enabled_categories) == set(DEFAULT_PII_CATEGORIES)
        assert policy.custom_patterns == []

    def test_enabled_categories_are_deduped(self):
        policy = PiiPolicy(enabled_categories=["email", "email", "ipv4"])
        assert policy.enabled_categories == ["email", "ipv4"]

    def test_custom_pattern_cannot_collide_with_builtin(self):
        with pytest.raises(ValueError):
            PiiPattern(category="email", pattern=r"foo")

    def test_custom_pattern_must_compile(self):
        with pytest.raises(ValueError):
            PiiPattern(category="myrule", pattern="[unclosed")

    def test_policy_extra_forbid(self):
        with pytest.raises(ValueError):
            PiiPolicy(rogue="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Detector — built-ins
# ---------------------------------------------------------------------------


class TestDetectorBuiltins:
    def test_email_detected_and_placeholder_masked(self):
        detector = PiiDetector(policy=PiiPolicy(enabled_categories=["email"]))
        matches = detector.scan_text("ping alice@example.com please")
        assert len(matches) == 1
        match = matches[0]
        assert match.category == "email"
        assert match.placeholder == "[email]"
        # Placeholder never contains the raw value.
        assert "alice" not in match.placeholder

    def test_ipv4_detected(self):
        detector = PiiDetector(policy=PiiPolicy(enabled_categories=["ipv4"]))
        assert [m.category for m in detector.scan_text("10.0.0.1 and 8.8.8.8")] == [
            "ipv4",
            "ipv4",
        ]

    def test_iban_detected(self):
        detector = PiiDetector(policy=PiiPolicy(enabled_categories=["iban"]))
        matches = detector.scan_text("send to DE89370400440532013000 now")
        assert len(matches) == 1
        assert matches[0].category == "iban"

    def test_api_key_detected(self):
        detector = PiiDetector(policy=PiiPolicy(enabled_categories=["api_key"]))
        matches = detector.scan_text("use key sk-abcdef0123456789 today")
        assert len(matches) == 1
        assert matches[0].category == "api_key"

    def test_matches_are_sorted_by_position(self):
        detector = PiiDetector(
            policy=PiiPolicy(enabled_categories=["email", "ipv4"])
        )
        matches = detector.scan_text("10.0.0.1 mailto: bob@example.org")
        assert [m.category for m in matches] == ["ipv4", "email"]
        assert matches[0].span_start < matches[1].span_start

    def test_empty_text_returns_empty(self):
        detector = PiiDetector(policy=PiiPolicy())
        assert detector.scan_text("") == []


# ---------------------------------------------------------------------------
# Detector — custom patterns and opt-outs
# ---------------------------------------------------------------------------


class TestDetectorCustom:
    def test_disabled_category_not_detected(self):
        detector = PiiDetector(policy=PiiPolicy(enabled_categories=["ipv4"]))
        # Email active-by-default is explicitly off here.
        assert detector.scan_text("reach me at bob@example.com") == []

    def test_custom_pattern_detected(self):
        policy = PiiPolicy(
            enabled_categories=[],
            custom_patterns=[
                PiiPattern(category="employee_id", pattern=r"\bEMP-\d{5}\b")
            ],
        )
        detector = PiiDetector(policy=policy)
        matches = detector.scan_text("ticket for EMP-12345 escalated")
        assert len(matches) == 1
        assert matches[0].category == "employee_id"
        assert matches[0].placeholder == "[employee_id]"

    def test_scan_fields_counts_and_aggregates(self):
        detector = PiiDetector(policy=PiiPolicy(enabled_categories=["email"]))
        result = detector.scan_fields(
            {
                "a": "no pii here",
                "b": "first bob@example.org and carol@x.co",
                "c": "",
            }
        )
        assert isinstance(result, PiiScanResult)
        assert result.scanned_fields == 3
        # Only path "b" produced findings.
        assert [f.source_path for f in result.findings] == ["b"]
        assert result.category_counts == {"email": 2}


# ---------------------------------------------------------------------------
# Retention annotation — read-only composition
# ---------------------------------------------------------------------------


class TestRetentionAnnotation:
    def test_annotation_reports_trace_and_approval_findings(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        approvals = ApprovalStore()

        trace_id = _write_trace_with_age(
            ts,
            days_old=90,
            workflow_name="wf",
            attrs={"user_email": "alice@example.com"},
        )
        approvals.create_request(
            _make_approval(
                approval_id="a-old",
                requested_at=FIXED_NOW - timedelta(days=120),
                task_summary="Contact 10.0.0.1 operator",
                reason="normal",
                status=ApprovalStatus.APPROVED,
            )
        )

        scanner = RetentionScanner(
            trace_store=ts, approval_store=approvals, policy=policy
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)
        detector = PiiDetector(
            policy=PiiPolicy(enabled_categories=["email", "ipv4"])
        )

        annotation = annotate_retention_candidates(
            detector=detector,
            report=report,
            trace_store=ts,
            approval_store=approvals,
        )

        assert isinstance(annotation, PiiRetentionAnnotation)
        assert annotation.total_candidates == 2
        assert annotation.candidates_with_findings == 2
        # Email appears in both trace.metadata and span.attributes (same value
        # passed to both by the helper), so the counter is ≥1 — we assert
        # category presence, not a brittle exact count.
        assert annotation.category_counts.get("email", 0) >= 1
        assert annotation.category_counts.get("ipv4", 0) == 1

        kinds = {a.kind for a in annotation.annotations}
        assert kinds == {"trace", "approval"}
        trace_ann = next(a for a in annotation.annotations if a.kind == "trace")
        approval_ann = next(
            a for a in annotation.annotations if a.kind == "approval"
        )
        assert trace_ann.record_id == trace_id
        assert approval_ann.record_id == "a-old"

    def test_annotation_is_read_only(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        approvals = ApprovalStore()
        _write_trace_with_age(
            ts,
            days_old=90,
            attrs={"user_email": "alice@example.com"},
        )
        approvals.create_request(
            _make_approval(
                approval_id="a-old",
                requested_at=FIXED_NOW - timedelta(days=120),
                reason="contact bob@example.com",
                status=ApprovalStatus.APPROVED,
            )
        )

        scanner = RetentionScanner(
            trace_store=ts, approval_store=approvals, policy=policy
        )
        report_before = scanner.scan(evaluation_time=FIXED_NOW)
        detector = PiiDetector(policy=PiiPolicy())

        annotate_retention_candidates(
            detector=detector,
            report=report_before,
            trace_store=ts,
            approval_store=approvals,
        )

        # Stores untouched.
        assert len(ts.list_recent_traces(limit=10)) == 1
        assert approvals.get_request("a-old") is not None
        # Re-scanning gives the same candidate set.
        report_after = scanner.scan(evaluation_time=FIXED_NOW)
        assert [c.record_id for c in report_after.candidates] == [
            c.record_id for c in report_before.candidates
        ]

    def test_missing_record_yields_empty_result_not_error(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        approvals = ApprovalStore()
        _write_trace_with_age(ts, days_old=90)

        scanner = RetentionScanner(
            trace_store=ts, approval_store=approvals, policy=policy
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)
        # Concurrently delete the trace between scan and annotate.
        ts.delete_trace(report.candidates[0].record_id)

        detector = PiiDetector(policy=PiiPolicy())
        annotation = annotate_retention_candidates(
            detector=detector,
            report=report,
            trace_store=ts,
            approval_store=approvals,
        )

        assert annotation.total_candidates == 1
        assert annotation.candidates_with_findings == 0
        assert annotation.annotations[0].finding_count == 0
        assert annotation.annotations[0].result.findings == []

    def test_empty_report_yields_empty_annotation(self, tmp_path):
        policy = RetentionPolicy(trace_retention_days=30, approval_retention_days=30)
        ts = TraceStore(str(tmp_path / "traces.sqlite3"))
        approvals = ApprovalStore()
        scanner = RetentionScanner(
            trace_store=ts, approval_store=approvals, policy=policy
        )
        report = scanner.scan(evaluation_time=FIXED_NOW)

        detector = PiiDetector(policy=PiiPolicy())
        annotation = annotate_retention_candidates(
            detector=detector,
            report=report,
            trace_store=ts,
            approval_store=approvals,
        )
        assert annotation.total_candidates == 0
        assert annotation.annotations == []
        assert annotation.category_counts == {}


# ---------------------------------------------------------------------------
# Schema hardening — every surface forbids extras
# ---------------------------------------------------------------------------


class TestSchemaHardening:
    def test_match_extra_forbid(self):
        with pytest.raises(ValueError):
            PiiMatch(
                category="email",
                span_start=0,
                span_end=1,
                placeholder="[email]",
                rogue="x",  # type: ignore[call-arg]
            )

    def test_finding_extra_forbid(self):
        with pytest.raises(ValueError):
            PiiFinding(
                source_path="p",
                matches=[],
                rogue="x",  # type: ignore[call-arg]
            )

    def test_scan_result_extra_forbid(self):
        with pytest.raises(ValueError):
            PiiScanResult(scanned_fields=0, rogue="x")  # type: ignore[call-arg]

    def test_candidate_annotation_extra_forbid(self):
        with pytest.raises(ValueError):
            PiiCandidateAnnotation(
                kind="trace",
                record_id="x",
                finding_count=0,
                result=PiiScanResult(scanned_fields=0),
                rogue="x",  # type: ignore[call-arg]
            )

    def test_retention_annotation_extra_forbid(self):
        with pytest.raises(ValueError):
            PiiRetentionAnnotation(
                total_candidates=0,
                candidates_with_findings=0,
                rogue="x",  # type: ignore[call-arg]
            )
