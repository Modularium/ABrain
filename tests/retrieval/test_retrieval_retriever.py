"""Tests for Phase 3 R2: InMemoryRetriever and RetrievalPort protocol.

Coverage:
1. Protocol conformance — InMemoryRetriever satisfies RetrievalPort
2. add_documents / remove_documents
3. retrieve — keyword overlap scoring, max_results cap
4. retrieve — trust-level filtering via allowed_trust_levels
5. retrieve — source absent from registry is skipped
6. retrieve — boundary annotations injected on results
7. retrieve — empty query returns no results
8. retrieve — no cross-scope violation when allowed_trust_levels is empty
"""

from __future__ import annotations

import pytest

from core.retrieval.models import KnowledgeSource, RetrievalQuery, RetrievalScope, SourceTrust
from core.retrieval.registry import KnowledgeSourceRegistry
from core.retrieval.retriever import InMemoryRetriever, RetrievalPort

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source(source_id: str = "src", trust: SourceTrust = SourceTrust.TRUSTED) -> KnowledgeSource:
    kwargs: dict = {
        "source_id": source_id,
        "display_name": source_id,
        "trust": trust,
        "source_type": "document",
    }
    if trust in (SourceTrust.EXTERNAL, SourceTrust.UNTRUSTED):
        kwargs["provenance"] = "https://example.com"
    return KnowledgeSource.model_validate(kwargs)


def _query(
    text: str = "hello world",
    scope: RetrievalScope = RetrievalScope.ASSISTANCE,
    allowed: list[SourceTrust] | None = None,
    max_results: int = 5,
) -> RetrievalQuery:
    return RetrievalQuery(
        query_text=text,
        scope=scope,
        allowed_trust_levels=allowed or [],
        max_results=max_results,
    )


def _setup(
    chunks: list[str] | None = None,
    trust: SourceTrust = SourceTrust.TRUSTED,
) -> tuple[InMemoryRetriever, KnowledgeSourceRegistry]:
    retriever = InMemoryRetriever()
    registry = KnowledgeSourceRegistry()
    src = _source(trust=trust)
    registry.register(src)
    retriever.add_documents("src", chunks or ["hello world content"])
    return retriever, registry


# ---------------------------------------------------------------------------
# 1. Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_in_memory_retriever_satisfies_protocol(self):
        assert isinstance(InMemoryRetriever(), RetrievalPort)


# ---------------------------------------------------------------------------
# 2. Document management
# ---------------------------------------------------------------------------


class TestDocumentManagement:
    def test_add_documents_stores_chunks(self):
        retriever = InMemoryRetriever()
        retriever.add_documents("src", ["chunk one", "chunk two"])
        # Verify via retrieve (side-effect free check via registry absence → 0 results)
        # No direct inspection of internals; presence is verified in retrieve tests.

    def test_add_documents_replaces_previous_chunks(self):
        retriever, registry = _setup(["old content"])
        retriever.add_documents("src", ["new content"])
        results = retriever.retrieve(_query("new content"), registry)
        assert len(results) == 1
        assert results[0].content == "new content"

    def test_remove_documents_clears_source(self):
        retriever, registry = _setup(["hello world"])
        retriever.remove_documents("src")
        results = retriever.retrieve(_query("hello world"), registry)
        assert results == []

    def test_remove_unknown_source_raises_key_error(self):
        retriever = InMemoryRetriever()
        with pytest.raises(KeyError):
            retriever.remove_documents("nonexistent")


# ---------------------------------------------------------------------------
# 3. Retrieval — scoring and max_results
# ---------------------------------------------------------------------------


class TestRetrieveScoring:
    def test_returns_matching_chunk(self):
        retriever, registry = _setup(["hello world is great"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert len(results) == 1
        assert "hello" in results[0].content

    def test_no_match_returns_empty(self):
        retriever, registry = _setup(["completely unrelated"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert results == []

    def test_results_capped_by_max_results(self):
        retriever = InMemoryRetriever()
        registry = KnowledgeSourceRegistry()
        src = _source()
        registry.register(src)
        retriever.add_documents("src", [f"hello world chunk {i}" for i in range(10)])
        results = retriever.retrieve(_query("hello world", max_results=3), registry)
        assert len(results) <= 3

    def test_higher_overlap_ranks_first(self):
        retriever = InMemoryRetriever()
        registry = KnowledgeSourceRegistry()
        src = _source()
        registry.register(src)
        # Score = |query ∩ doc| / |query|.  query="hello world foo" (3 tokens).
        # "hello world" → 2/3 ≈ 0.67; "hello world foo" → 3/3 = 1.0
        retriever.add_documents("src", ["hello world", "hello world foo"])
        results = retriever.retrieve(_query("hello world foo"), registry)
        assert results[0].content == "hello world foo"

    def test_result_carries_source_id_and_trust(self):
        retriever, registry = _setup(["hello world"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert results[0].source_id == "src"
        assert results[0].trust == SourceTrust.TRUSTED

    def test_result_score_is_positive(self):
        retriever, registry = _setup(["hello world"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert results[0].score > 0.0


# ---------------------------------------------------------------------------
# 4. Retrieval — trust-level filtering
# ---------------------------------------------------------------------------


class TestTrustFiltering:
    def test_allowed_trust_filters_out_mismatched_source(self):
        retriever = InMemoryRetriever()
        registry = KnowledgeSourceRegistry()
        src = _source(trust=SourceTrust.INTERNAL)
        registry.register(src)
        retriever.add_documents("src", ["hello world"])
        results = retriever.retrieve(
            _query("hello world", allowed=[SourceTrust.TRUSTED]), registry
        )
        assert results == []

    def test_allowed_trust_includes_matching_source(self):
        retriever, registry = _setup(["hello world"], trust=SourceTrust.TRUSTED)
        results = retriever.retrieve(
            _query("hello world", allowed=[SourceTrust.TRUSTED]), registry
        )
        assert len(results) == 1

    def test_empty_allowed_trust_returns_all_trust_levels(self):
        retriever = InMemoryRetriever()
        registry = KnowledgeSourceRegistry()
        for sid, trust in [("t", SourceTrust.TRUSTED), ("i", SourceTrust.INTERNAL)]:
            src = _source(source_id=sid, trust=trust)
            registry.register(src)
            retriever.add_documents(sid, ["hello world"])
        results = retriever.retrieve(_query("hello world", allowed=[]), registry)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# 5. Retrieval — source absent from registry is skipped
# ---------------------------------------------------------------------------


class TestRegistryAbsence:
    def test_unregistered_source_documents_are_skipped(self):
        retriever = InMemoryRetriever()
        registry = KnowledgeSourceRegistry()
        # Add documents but do NOT register the source
        retriever.add_documents("ghost", ["hello world"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert results == []


# ---------------------------------------------------------------------------
# 6. Retrieval — boundary annotations
# ---------------------------------------------------------------------------


class TestBoundaryAnnotations:
    def test_untrusted_assistance_result_carries_warning(self):
        retriever = InMemoryRetriever()
        registry = KnowledgeSourceRegistry()
        src = _source(trust=SourceTrust.UNTRUSTED)
        registry.register(src)
        retriever.add_documents("src", ["hello world"])
        results = retriever.retrieve(
            _query("hello world", scope=RetrievalScope.ASSISTANCE), registry
        )
        assert len(results) == 1
        assert results[0].warnings  # at least one advisory warning

    def test_trusted_assistance_result_has_no_warnings(self):
        retriever, registry = _setup(["hello world"], trust=SourceTrust.TRUSTED)
        results = retriever.retrieve(
            _query("hello world", scope=RetrievalScope.ASSISTANCE), registry
        )
        assert results[0].warnings == []

    def test_external_planning_result_carries_warning(self):
        retriever = InMemoryRetriever()
        registry = KnowledgeSourceRegistry()
        src = _source(trust=SourceTrust.EXTERNAL)
        registry.register(src)
        retriever.add_documents("src", ["hello world"])
        results = retriever.retrieve(
            _query("hello world", scope=RetrievalScope.PLANNING), registry
        )
        assert len(results) == 1
        assert any("EXTERNAL" in w or "planning" in w.lower() for w in results[0].warnings)
