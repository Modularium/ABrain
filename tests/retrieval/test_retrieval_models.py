"""Tests for Phase 3 R1: retrieval data models.

Coverage:
1. SourceTrust enum values and ordering
2. RetrievalScope enum values (no critical_action)
3. KnowledgeSource model — validation, normalization, extra-field rejection
4. RetrievalQuery model — validation, normalization, deduplication, extra-field rejection
5. RetrievalResult model — validation, default timestamps, extra-field rejection
"""

from __future__ import annotations

import pytest

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


def _source(**kwargs) -> KnowledgeSource:
    defaults = {
        "source_id": "src-test",
        "display_name": "Test Source",
        "trust": SourceTrust.TRUSTED,
        "source_type": "document",
    }
    defaults.update(kwargs)
    return KnowledgeSource.model_validate(defaults)


def _query(**kwargs) -> RetrievalQuery:
    defaults = {"query_text": "What is ABrain?", "scope": RetrievalScope.EXPLANATION}
    defaults.update(kwargs)
    return RetrievalQuery.model_validate(defaults)


def _result(**kwargs) -> RetrievalResult:
    defaults = {
        "source_id": "src-test",
        "trust": SourceTrust.TRUSTED,
        "content": "ABrain is a policy-driven orchestration system.",
        "score": 0.95,
    }
    defaults.update(kwargs)
    return RetrievalResult.model_validate(defaults)


# ---------------------------------------------------------------------------
# 1. SourceTrust — enum coverage and no unknown values
# ---------------------------------------------------------------------------


class TestSourceTrust:
    def test_all_four_trust_levels_exist(self):
        assert SourceTrust.TRUSTED == "trusted"
        assert SourceTrust.INTERNAL == "internal"
        assert SourceTrust.EXTERNAL == "external"
        assert SourceTrust.UNTRUSTED == "untrusted"

    def test_no_action_trust_level(self):
        assert not hasattr(SourceTrust, "CRITICAL") or SourceTrust.TRUSTED != "critical"
        with pytest.raises(ValueError):
            SourceTrust("privileged")

    def test_string_equality(self):
        assert SourceTrust.TRUSTED == "trusted"
        assert SourceTrust.UNTRUSTED != "trusted"


# ---------------------------------------------------------------------------
# 2. RetrievalScope — restricted to safe scopes
# ---------------------------------------------------------------------------


class TestRetrievalScope:
    def test_three_safe_scopes_exist(self):
        assert RetrievalScope.EXPLANATION == "explanation"
        assert RetrievalScope.ASSISTANCE == "assistance"
        assert RetrievalScope.PLANNING == "planning"

    def test_no_critical_action_scope(self):
        with pytest.raises(ValueError):
            RetrievalScope("critical_action")

    def test_no_execution_scope(self):
        with pytest.raises(ValueError):
            RetrievalScope("execution")

    def test_no_action_scope(self):
        with pytest.raises(ValueError):
            RetrievalScope("action")


# ---------------------------------------------------------------------------
# 3. KnowledgeSource model
# ---------------------------------------------------------------------------


class TestKnowledgeSource:
    def test_minimal_valid_source(self):
        src = _source()
        assert src.source_id == "src-test"
        assert src.trust == SourceTrust.TRUSTED
        assert src.pii_risk is False
        assert src.license is None
        assert src.retention_days is None

    def test_full_source_accepted(self):
        src = _source(
            provenance="https://docs.example.com",
            pii_risk=True,
            license="Apache-2.0",
            retention_days=90,
        )
        assert src.pii_risk is True
        assert src.license == "Apache-2.0"
        assert src.retention_days == 90

    def test_empty_source_id_rejected(self):
        with pytest.raises(Exception):
            _source(source_id="")

    def test_whitespace_source_id_rejected(self):
        with pytest.raises(Exception):
            _source(source_id="   ")

    def test_whitespace_source_id_stripped(self):
        src = KnowledgeSource(
            source_id="  src-1  ",
            display_name="Test",
            trust=SourceTrust.INTERNAL,
            source_type="document",
        )
        assert src.source_id == "src-1"

    def test_empty_display_name_rejected(self):
        with pytest.raises(Exception):
            _source(display_name="")

    def test_empty_source_type_rejected(self):
        with pytest.raises(Exception):
            _source(source_type="")

    def test_zero_retention_days_rejected(self):
        with pytest.raises(Exception):
            _source(retention_days=0)

    def test_negative_retention_days_rejected(self):
        with pytest.raises(Exception):
            _source(retention_days=-1)

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            KnowledgeSource(
                source_id="x",
                display_name="x",
                trust=SourceTrust.TRUSTED,
                source_type="document",
                hidden_capability="bypass",
            )

    def test_whitespace_only_provenance_becomes_none(self):
        src = _source(provenance="   ")
        assert src.provenance is None

    def test_all_trust_levels_accepted(self):
        for trust in SourceTrust:
            src = _source(trust=trust)
            assert src.trust == trust


# ---------------------------------------------------------------------------
# 4. RetrievalQuery model
# ---------------------------------------------------------------------------


class TestRetrievalQuery:
    def test_minimal_valid_query(self):
        q = _query()
        assert q.query_text == "What is ABrain?"
        assert q.scope == RetrievalScope.EXPLANATION
        assert q.allowed_trust_levels == []
        assert q.max_results == 5

    def test_empty_query_text_rejected(self):
        with pytest.raises(Exception):
            _query(query_text="")

    def test_whitespace_only_query_rejected(self):
        with pytest.raises(Exception):
            _query(query_text="   ")

    def test_query_text_stripped(self):
        q = _query(query_text="  hello  ")
        assert q.query_text == "hello"

    def test_max_results_minimum_is_one(self):
        with pytest.raises(Exception):
            _query(max_results=0)

    def test_max_results_maximum_is_fifty(self):
        with pytest.raises(Exception):
            _query(max_results=51)

    def test_max_results_boundary_values_accepted(self):
        q1 = _query(max_results=1)
        q50 = _query(max_results=50)
        assert q1.max_results == 1
        assert q50.max_results == 50

    def test_duplicate_trust_levels_deduplicated(self):
        q = _query(
            allowed_trust_levels=[
                SourceTrust.TRUSTED,
                SourceTrust.INTERNAL,
                SourceTrust.TRUSTED,
            ]
        )
        assert q.allowed_trust_levels == [SourceTrust.TRUSTED, SourceTrust.INTERNAL]

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            RetrievalQuery(
                query_text="hello",
                scope=RetrievalScope.EXPLANATION,
                bypass_governance=True,
            )

    def test_all_scopes_accepted(self):
        for scope in RetrievalScope:
            q = _query(scope=scope)
            assert q.scope == scope

    def test_task_id_optional(self):
        q = _query(task_id="task-123")
        assert q.task_id == "task-123"
        q2 = _query()
        assert q2.task_id is None


# ---------------------------------------------------------------------------
# 5. RetrievalResult model
# ---------------------------------------------------------------------------


class TestRetrievalResult:
    def test_minimal_valid_result(self):
        r = _result()
        assert r.source_id == "src-test"
        assert r.trust == SourceTrust.TRUSTED
        assert r.score == 0.95
        assert r.warnings == []
        assert r.provenance is None

    def test_score_must_be_in_unit_interval(self):
        with pytest.raises(Exception):
            _result(score=-0.01)
        with pytest.raises(Exception):
            _result(score=1.001)

    def test_score_boundary_values_accepted(self):
        r0 = _result(score=0.0)
        r1 = _result(score=1.0)
        assert r0.score == 0.0
        assert r1.score == 1.0

    def test_empty_content_rejected(self):
        with pytest.raises(Exception):
            _result(content="")

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            RetrievalResult(
                source_id="x",
                trust=SourceTrust.TRUSTED,
                content="x",
                score=0.5,
                injected_field="bypass",
            )

    def test_retrieved_at_is_populated_by_default(self):
        r = _result()
        assert r.retrieved_at
        assert "T" in r.retrieved_at  # ISO format

    def test_warnings_list_is_empty_by_default(self):
        r = _result()
        assert r.warnings == []

    def test_warnings_can_be_set(self):
        r = _result(warnings=["advisory: untrusted source"])
        assert len(r.warnings) == 1

    def test_all_trust_levels_accepted_in_result(self):
        for trust in SourceTrust:
            r = _result(trust=trust)
            assert r.trust == trust
