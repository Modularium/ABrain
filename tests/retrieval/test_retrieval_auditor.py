"""Tests for Phase 3 R6: RetrievalAuditor — source attribution in TraceStore.

Coverage:
1. record_retrieval — span is created in TraceStore with correct type/name
2. record_retrieval — span attributes contain query scope and task_id
3. record_retrieval — span attributes contain result count and source list
4. record_retrieval — source list carries source_id, trust, provenance per result
5. record_retrieval — warnings count aggregated across results
6. record_retrieval — span status is "ok"
7. record_retrieval — returns SpanRecord
8. record_retrieval — no store → returns None (no-op)
9. record_injection_block — span created with name "retrieval.blocked"
10. record_injection_block — injection_blocked=True in attributes
11. record_injection_block — violation reason truncated and stored
12. record_injection_block — span status is "blocked"
13. record_injection_block — no store → returns None
14. parent_span_id threaded through to TraceStore
15. TraceStore error during emit is swallowed (no exception propagation)
"""

from __future__ import annotations

import pytest

from core.audit.trace_store import TraceStore
from core.retrieval.auditor import RetrievalAuditor
from core.retrieval.boundaries import RetrievalPolicyViolation
from core.retrieval.models import (
    KnowledgeSource,
    RetrievalQuery,
    RetrievalResult,
    RetrievalScope,
    SourceTrust,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def trace_store(tmp_path):
    return TraceStore(tmp_path / "traces.sqlite3")


@pytest.fixture
def trace_id(trace_store):
    record = trace_store.create_trace("test-workflow", task_id="task-1")
    return record.trace_id


def _query(
    scope: RetrievalScope = RetrievalScope.ASSISTANCE,
    task_id: str | None = "task-1",
) -> RetrievalQuery:
    return RetrievalQuery(
        query_text="hello world",
        scope=scope,
        task_id=task_id,
    )


def _result(
    source_id: str = "src",
    trust: SourceTrust = SourceTrust.TRUSTED,
    provenance: str | None = None,
    warnings: list[str] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        source_id=source_id,
        trust=trust,
        content="some content",
        score=0.8,
        provenance=provenance,
        warnings=warnings or [],
    )


# ---------------------------------------------------------------------------
# 1–7. record_retrieval — successful retrieval
# ---------------------------------------------------------------------------


class TestRecordRetrieval:
    def test_returns_span_record(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [_result()])
        assert span is not None

    def test_span_type_is_retrieval(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [_result()])
        assert span.span_type == "retrieval"

    def test_span_name_is_retrieval_query(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [_result()])
        assert span.name == "retrieval.query"

    def test_span_status_is_ok(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [_result()])
        assert span.status == "ok"

    def test_span_attributes_contain_scope(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(scope=RetrievalScope.PLANNING), [_result()])
        assert span.attributes["retrieval.query.scope"] == RetrievalScope.PLANNING

    def test_span_attributes_contain_task_id(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(task_id="task-99"), [_result()])
        assert span.attributes["retrieval.query.task_id"] == "task-99"

    def test_span_attributes_contain_result_count(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [_result(), _result(source_id="src2")])
        assert span.attributes["retrieval.results.count"] == 2

    def test_span_attributes_source_list_correct(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        r = _result(source_id="doc-1", trust=SourceTrust.INTERNAL, provenance="file://docs")
        span = auditor.record_retrieval(trace_id, _query(), [r])
        sources = span.attributes["retrieval.results.sources"]
        assert len(sources) == 1
        assert sources[0]["source_id"] == "doc-1"
        assert sources[0]["trust"] == SourceTrust.INTERNAL
        assert sources[0]["provenance"] == "file://docs"

    def test_span_attributes_empty_results(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [])
        assert span.attributes["retrieval.results.count"] == 0
        assert span.attributes["retrieval.results.sources"] == []

    def test_warnings_count_aggregated(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        r1 = _result(warnings=["warn1"])
        r2 = _result(source_id="src2", warnings=["warn2", "warn3"])
        span = auditor.record_retrieval(trace_id, _query(), [r1, r2])
        assert span.attributes["retrieval.warnings.count"] == 3

    def test_injection_blocked_false_on_success(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [_result()])
        assert span.attributes["retrieval.injection_blocked"] is False

    def test_span_is_persisted_in_trace_store(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        span = auditor.record_retrieval(trace_id, _query(), [_result()])
        snapshot = trace_store.get_trace(trace_id)
        span_ids = {s.span_id for s in snapshot.spans}
        assert span.span_id in span_ids


# ---------------------------------------------------------------------------
# 8. No store → no-op
# ---------------------------------------------------------------------------


class TestNoStore:
    def test_record_retrieval_no_store_returns_none(self):
        auditor = RetrievalAuditor(None)
        result = auditor.record_retrieval("trace-1", _query(), [_result()])
        assert result is None

    def test_record_injection_block_no_store_returns_none(self):
        auditor = RetrievalAuditor(None)
        violation = RetrievalPolicyViolation("blocked", _query())
        result = auditor.record_injection_block("trace-1", _query(), violation)
        assert result is None


# ---------------------------------------------------------------------------
# 9–13. record_injection_block
# ---------------------------------------------------------------------------


class TestRecordInjectionBlock:
    def test_span_name_is_retrieval_blocked(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        violation = RetrievalPolicyViolation("injection detected", _query())
        span = auditor.record_injection_block(trace_id, _query(), violation)
        assert span.name == "retrieval.blocked"

    def test_span_type_is_retrieval(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        violation = RetrievalPolicyViolation("blocked", _query())
        span = auditor.record_injection_block(trace_id, _query(), violation)
        assert span.span_type == "retrieval"

    def test_span_status_is_blocked(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        violation = RetrievalPolicyViolation("blocked", _query())
        span = auditor.record_injection_block(trace_id, _query(), violation)
        assert span.status == "blocked"

    def test_injection_blocked_attribute_true(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        violation = RetrievalPolicyViolation("blocked", _query())
        span = auditor.record_injection_block(trace_id, _query(), violation)
        assert span.attributes["retrieval.injection_blocked"] is True

    def test_injection_reason_stored(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        violation = RetrievalPolicyViolation("injection reason text", _query())
        span = auditor.record_injection_block(trace_id, _query(), violation)
        assert "injection reason text" in span.attributes["retrieval.injection_reason"]

    def test_result_count_is_zero_on_block(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        violation = RetrievalPolicyViolation("blocked", _query())
        span = auditor.record_injection_block(trace_id, _query(), violation)
        assert span.attributes["retrieval.results.count"] == 0

    def test_violation_reason_truncated_to_512(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        long_reason = "x" * 1000
        violation = RetrievalPolicyViolation(long_reason, _query())
        span = auditor.record_injection_block(trace_id, _query(), violation)
        assert len(span.attributes["retrieval.injection_reason"]) <= 512


# ---------------------------------------------------------------------------
# 14. parent_span_id threaded through
# ---------------------------------------------------------------------------


class TestParentSpanId:
    def test_parent_span_id_set_on_record_retrieval(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        parent = trace_store.start_span(
            trace_id, span_type="orchestration", name="parent.span"
        )
        span = auditor.record_retrieval(
            trace_id, _query(), [_result()], parent_span_id=parent.span_id
        )
        assert span.parent_span_id == parent.span_id

    def test_parent_span_id_set_on_injection_block(self, trace_store, trace_id):
        auditor = RetrievalAuditor(trace_store)
        parent = trace_store.start_span(
            trace_id, span_type="orchestration", name="parent.span"
        )
        violation = RetrievalPolicyViolation("blocked", _query())
        span = auditor.record_injection_block(
            trace_id, _query(), violation, parent_span_id=parent.span_id
        )
        assert span.parent_span_id == parent.span_id


# ---------------------------------------------------------------------------
# 15. TraceStore error is swallowed
# ---------------------------------------------------------------------------


class TestErrorSwallowed:
    def test_bad_trace_id_does_not_raise(self, trace_store):
        auditor = RetrievalAuditor(trace_store)
        # "nonexistent-trace" is not in the store — span insert will still
        # succeed (TraceStore allows orphan spans) or fail; either way
        # the auditor must not propagate.
        try:
            auditor.record_retrieval("nonexistent-trace", _query(), [_result()])
        except Exception as exc:
            pytest.fail(f"RetrievalAuditor should not raise: {exc}")
