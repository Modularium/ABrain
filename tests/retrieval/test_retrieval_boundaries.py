"""Tests for Phase 3 R1: retrieval governance boundary.

Coverage:
1. validate_query — UNTRUSTED+PLANNING raises RetrievalPolicyViolation
2. validate_query — all other scope/trust combinations permitted
3. annotate_results — warnings injected for UNTRUSTED in explanation/assistance
4. annotate_results — EXTERNAL in PLANNING gets warning
5. annotate_results — TRUSTED/INTERNAL never get warnings
6. annotate_results — duplicate warnings not inserted
7. check_planning_scope_trust — advisory messages without mutation
8. RetrievalPolicyViolation carries query reference
"""

from __future__ import annotations

import pytest

from core.retrieval.boundaries import RetrievalBoundary, RetrievalPolicyViolation
from core.retrieval.models import (
    RetrievalQuery,
    RetrievalResult,
    RetrievalScope,
    SourceTrust,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _query(scope: RetrievalScope, trust_levels: list[SourceTrust]) -> RetrievalQuery:
    return RetrievalQuery(
        query_text="test query",
        scope=scope,
        allowed_trust_levels=trust_levels,
    )


def _result(trust: SourceTrust, source_id: str = "src") -> RetrievalResult:
    return RetrievalResult(
        source_id=source_id,
        trust=trust,
        content="Test content from source.",
        score=0.8,
    )


boundary = RetrievalBoundary()


# ---------------------------------------------------------------------------
# 1. validate_query — UNTRUSTED + PLANNING is the only hard block
# ---------------------------------------------------------------------------


class TestValidateQuery:
    def test_untrusted_planning_raises_policy_violation(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.UNTRUSTED])
        with pytest.raises(RetrievalPolicyViolation):
            boundary.validate_query(q)

    def test_untrusted_planning_mixed_with_trusted_still_raises(self):
        q = _query(
            RetrievalScope.PLANNING,
            [SourceTrust.TRUSTED, SourceTrust.UNTRUSTED],
        )
        with pytest.raises(RetrievalPolicyViolation):
            boundary.validate_query(q)

    def test_policy_violation_carries_query_reference(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.UNTRUSTED])
        with pytest.raises(RetrievalPolicyViolation) as exc_info:
            boundary.validate_query(q)
        assert exc_info.value.query is q

    def test_policy_violation_reason_mentions_scope_and_trust(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.UNTRUSTED])
        with pytest.raises(RetrievalPolicyViolation) as exc_info:
            boundary.validate_query(q)
        assert "UNTRUSTED" in exc_info.value.reason
        assert "planning" in exc_info.value.reason

    def test_untrusted_explanation_is_permitted(self):
        q = _query(RetrievalScope.EXPLANATION, [SourceTrust.UNTRUSTED])
        boundary.validate_query(q)  # must not raise

    def test_untrusted_assistance_is_permitted(self):
        q = _query(RetrievalScope.ASSISTANCE, [SourceTrust.UNTRUSTED])
        boundary.validate_query(q)  # must not raise

    def test_external_planning_is_permitted(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.EXTERNAL])
        boundary.validate_query(q)  # must not raise

    def test_trusted_planning_is_permitted(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.TRUSTED])
        boundary.validate_query(q)  # must not raise

    def test_internal_planning_is_permitted(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.INTERNAL])
        boundary.validate_query(q)  # must not raise

    def test_empty_trust_levels_with_planning_is_permitted(self):
        q = _query(RetrievalScope.PLANNING, [])
        boundary.validate_query(q)  # empty list means no filter; backend decides


# ---------------------------------------------------------------------------
# 2. annotate_results — warning injection
# ---------------------------------------------------------------------------


class TestAnnotateResults:
    def test_trusted_explanation_no_warning(self):
        q = _query(RetrievalScope.EXPLANATION, [SourceTrust.TRUSTED])
        results = [_result(SourceTrust.TRUSTED)]
        annotated = boundary.annotate_results(results, q)
        assert annotated[0].warnings == []

    def test_internal_planning_no_warning(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.INTERNAL])
        results = [_result(SourceTrust.INTERNAL)]
        annotated = boundary.annotate_results(results, q)
        assert annotated[0].warnings == []

    def test_untrusted_explanation_gets_warning(self):
        q = _query(RetrievalScope.EXPLANATION, [SourceTrust.UNTRUSTED])
        results = [_result(SourceTrust.UNTRUSTED)]
        annotated = boundary.annotate_results(results, q)
        assert len(annotated[0].warnings) == 1
        assert "UNTRUSTED" in annotated[0].warnings[0]

    def test_untrusted_assistance_gets_warning(self):
        q = _query(RetrievalScope.ASSISTANCE, [SourceTrust.UNTRUSTED])
        results = [_result(SourceTrust.UNTRUSTED)]
        annotated = boundary.annotate_results(results, q)
        assert len(annotated[0].warnings) == 1
        assert "advisory" in annotated[0].warnings[0].lower() or "untrusted" in annotated[0].warnings[0].lower()

    def test_external_planning_gets_warning(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.EXTERNAL])
        results = [_result(SourceTrust.EXTERNAL)]
        annotated = boundary.annotate_results(results, q)
        assert len(annotated[0].warnings) == 1
        assert "EXTERNAL" in annotated[0].warnings[0] or "planning" in annotated[0].warnings[0]

    def test_trusted_planning_no_warning(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.TRUSTED])
        results = [_result(SourceTrust.TRUSTED)]
        annotated = boundary.annotate_results(results, q)
        assert annotated[0].warnings == []

    def test_duplicate_warning_not_inserted_twice(self):
        q = _query(RetrievalScope.EXPLANATION, [SourceTrust.UNTRUSTED])
        existing_warning = "Result from UNTRUSTED source used for explanation — verify before citing."
        r = RetrievalResult(
            source_id="src",
            trust=SourceTrust.UNTRUSTED,
            content="Content.",
            score=0.5,
            warnings=[existing_warning],
        )
        annotated = boundary.annotate_results([r], q)
        assert annotated[0].warnings.count(existing_warning) == 1

    def test_original_results_not_mutated(self):
        q = _query(RetrievalScope.EXPLANATION, [SourceTrust.UNTRUSTED])
        original = _result(SourceTrust.UNTRUSTED)
        original_warnings = list(original.warnings)
        boundary.annotate_results([original], q)
        assert original.warnings == original_warnings

    def test_mixed_trust_results_annotated_correctly(self):
        q = _query(
            RetrievalScope.EXPLANATION,
            [SourceTrust.TRUSTED, SourceTrust.UNTRUSTED],
        )
        results = [
            _result(SourceTrust.TRUSTED, source_id="trusted-src"),
            _result(SourceTrust.UNTRUSTED, source_id="untrusted-src"),
        ]
        annotated = boundary.annotate_results(results, q)
        assert annotated[0].warnings == []
        assert len(annotated[1].warnings) == 1

    def test_empty_result_list_returns_empty(self):
        q = _query(RetrievalScope.EXPLANATION, [])
        annotated = boundary.annotate_results([], q)
        assert annotated == []


# ---------------------------------------------------------------------------
# 3. check_planning_scope_trust — advisory without mutation
# ---------------------------------------------------------------------------


class TestCheckPlanningScopeTrust:
    def test_trusted_results_in_planning_produce_no_warnings(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.TRUSTED])
        warns = boundary.check_planning_scope_trust(
            [_result(SourceTrust.TRUSTED)], q
        )
        assert warns == []

    def test_external_results_in_planning_produce_warning(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.EXTERNAL])
        warns = boundary.check_planning_scope_trust(
            [_result(SourceTrust.EXTERNAL)], q
        )
        assert len(warns) == 1

    def test_untrusted_results_in_planning_produce_violation_message(self):
        q = _query(RetrievalScope.PLANNING, [])
        warns = boundary.check_planning_scope_trust(
            [_result(SourceTrust.UNTRUSTED)], q
        )
        assert len(warns) == 1
        assert "not permitted" in warns[0].lower() or "untrusted" in warns[0].lower()

    def test_check_does_not_mutate_results(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.EXTERNAL])
        r = _result(SourceTrust.EXTERNAL)
        original_warnings = list(r.warnings)
        boundary.check_planning_scope_trust([r], q)
        assert r.warnings == original_warnings

    def test_multiple_results_all_checked(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.TRUSTED, SourceTrust.EXTERNAL])
        results = [
            _result(SourceTrust.TRUSTED),
            _result(SourceTrust.EXTERNAL),
            _result(SourceTrust.INTERNAL),
        ]
        warns = boundary.check_planning_scope_trust(results, q)
        assert len(warns) == 1


# ---------------------------------------------------------------------------
# 4. RetrievalPolicyViolation — error contract
# ---------------------------------------------------------------------------


class TestRetrievalPolicyViolation:
    def test_is_runtime_error(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.UNTRUSTED])
        exc = RetrievalPolicyViolation(reason="blocked", query=q)
        assert isinstance(exc, RuntimeError)

    def test_reason_is_message(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.UNTRUSTED])
        exc = RetrievalPolicyViolation(reason="blocked: untrusted", query=q)
        assert str(exc) == "blocked: untrusted"

    def test_query_is_accessible(self):
        q = _query(RetrievalScope.PLANNING, [SourceTrust.UNTRUSTED])
        exc = RetrievalPolicyViolation(reason="blocked", query=q)
        assert exc.query is q
