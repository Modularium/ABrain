"""Tests for Phase 3 R4: SQLiteRetriever.

Coverage:
1. Protocol conformance — SQLiteRetriever satisfies RetrievalPort
2. Retrieve from store — basic keyword match
3. Retrieve — no match returns empty list
4. Retrieve — source registered but no stored chunks → no results
5. Retrieve — source with chunks but not in registry → no results
6. Retrieve — max_results cap
7. Retrieve — trust-level filtering via allowed_trust_levels
8. Retrieve — empty allowed_trust_levels returns all trust levels
9. Retrieve — boundary annotations applied (UNTRUSTED warns)
10. Retrieve — multi-source ranking by score
11. End-to-end: IngestionPipeline → SQLiteRetriever
"""

from __future__ import annotations

import pytest

from core.retrieval.document_store import SQLiteDocumentStore
from core.retrieval.ingestion import IngestionPipeline, IngestionRequest
from core.retrieval.models import KnowledgeSource, RetrievalQuery, RetrievalScope, SourceTrust
from core.retrieval.registry import KnowledgeSourceRegistry
from core.retrieval.retriever import RetrievalPort, SQLiteRetriever

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source(
    source_id: str = "src",
    trust: SourceTrust = SourceTrust.TRUSTED,
) -> KnowledgeSource:
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


@pytest.fixture
def store(tmp_path):
    return SQLiteDocumentStore(tmp_path / "test.sqlite3")


@pytest.fixture
def registry():
    return KnowledgeSourceRegistry()


@pytest.fixture
def retriever(store):
    return SQLiteRetriever(store)


def _setup(
    store: SQLiteDocumentStore,
    registry: KnowledgeSourceRegistry,
    chunks: list[str],
    source_id: str = "src",
    trust: SourceTrust = SourceTrust.TRUSTED,
) -> None:
    src = _source(source_id=source_id, trust=trust)
    registry.register(src)
    store.store_chunks(source_id, chunks)


# ---------------------------------------------------------------------------
# 1. Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_sqlite_retriever_satisfies_retrieval_port(self, store):
        assert isinstance(SQLiteRetriever(store), RetrievalPort)


# ---------------------------------------------------------------------------
# 2. Basic keyword match
# ---------------------------------------------------------------------------


class TestBasicRetrieval:
    def test_returns_matching_chunk(self, store, registry, retriever):
        _setup(store, registry, ["hello world content"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert len(results) == 1
        assert "hello" in results[0].content

    def test_result_carries_source_id_and_trust(self, store, registry, retriever):
        _setup(store, registry, ["hello world"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert results[0].source_id == "src"
        assert results[0].trust == SourceTrust.TRUSTED

    def test_result_score_is_positive(self, store, registry, retriever):
        _setup(store, registry, ["hello world"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert results[0].score > 0.0


# ---------------------------------------------------------------------------
# 3. No match returns empty
# ---------------------------------------------------------------------------


class TestNoMatch:
    def test_no_match_returns_empty_list(self, store, registry, retriever):
        _setup(store, registry, ["completely unrelated"])
        results = retriever.retrieve(_query("hello world"), registry)
        assert results == []


# ---------------------------------------------------------------------------
# 4. Source registered but no stored chunks
# ---------------------------------------------------------------------------


class TestRegisteredNoChunks:
    def test_registered_source_without_chunks_returns_no_results(
        self, store, registry, retriever
    ):
        registry.register(_source())
        # no store.store_chunks call
        results = retriever.retrieve(_query("hello world"), registry)
        assert results == []


# ---------------------------------------------------------------------------
# 5. Source has chunks but not in registry
# ---------------------------------------------------------------------------


class TestChunksWithoutRegistration:
    def test_unregistered_source_chunks_are_skipped(self, store, registry, retriever):
        store.store_chunks("ghost", ["hello world"])
        # ghost is NOT registered
        results = retriever.retrieve(_query("hello world"), registry)
        assert results == []


# ---------------------------------------------------------------------------
# 6. max_results cap
# ---------------------------------------------------------------------------


class TestMaxResults:
    def test_results_capped_by_max_results(self, store, registry, retriever):
        _setup(store, registry, [f"hello world chunk {i}" for i in range(10)])
        results = retriever.retrieve(_query("hello world", max_results=3), registry)
        assert len(results) <= 3

    def test_returns_all_when_fewer_than_max(self, store, registry, retriever):
        _setup(store, registry, ["hello world"])
        results = retriever.retrieve(_query("hello world", max_results=10), registry)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# 7. Trust-level filtering
# ---------------------------------------------------------------------------


class TestTrustFiltering:
    def test_allowed_trust_filters_out_mismatched_source(
        self, store, registry, retriever
    ):
        _setup(store, registry, ["hello world"], trust=SourceTrust.INTERNAL)
        results = retriever.retrieve(
            _query("hello world", allowed=[SourceTrust.TRUSTED]), registry
        )
        assert results == []

    def test_allowed_trust_includes_matching_source(self, store, registry, retriever):
        _setup(store, registry, ["hello world"], trust=SourceTrust.TRUSTED)
        results = retriever.retrieve(
            _query("hello world", allowed=[SourceTrust.TRUSTED]), registry
        )
        assert len(results) == 1


# ---------------------------------------------------------------------------
# 8. Empty allowed_trust returns all trust levels
# ---------------------------------------------------------------------------


class TestEmptyAllowedTrust:
    def test_empty_allowed_returns_all_levels(self, store, registry, retriever):
        for sid, trust in [
            ("t", SourceTrust.TRUSTED),
            ("i", SourceTrust.INTERNAL),
        ]:
            _setup(store, registry, ["hello world"], source_id=sid, trust=trust)
        results = retriever.retrieve(_query("hello world", allowed=[]), registry)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# 9. Boundary annotations
# ---------------------------------------------------------------------------


class TestBoundaryAnnotations:
    def test_untrusted_result_carries_warning(self, store, registry, retriever):
        _setup(store, registry, ["hello world"], trust=SourceTrust.UNTRUSTED)
        results = retriever.retrieve(
            _query("hello world", scope=RetrievalScope.ASSISTANCE), registry
        )
        assert len(results) == 1
        assert results[0].warnings

    def test_trusted_result_has_no_warnings(self, store, registry, retriever):
        _setup(store, registry, ["hello world"], trust=SourceTrust.TRUSTED)
        results = retriever.retrieve(
            _query("hello world", scope=RetrievalScope.ASSISTANCE), registry
        )
        assert results[0].warnings == []


# ---------------------------------------------------------------------------
# 10. Multi-source ranking
# ---------------------------------------------------------------------------


class TestRanking:
    def test_higher_overlap_ranks_first(self, store, registry, retriever):
        _setup(store, registry, ["hello world extra words"], source_id="partial")
        _setup(
            store, registry,
            ["hello world foo"],
            source_id="full",
            trust=SourceTrust.INTERNAL,
        )
        # query "hello world foo" (3 tokens)
        # "hello world extra words" → 2/3 ≈ 0.67
        # "hello world foo" → 3/3 = 1.0
        results = retriever.retrieve(_query("hello world foo"), registry)
        assert results[0].source_id == "full"

    def test_results_sorted_descending_by_score(self, store, registry, retriever):
        _setup(store, registry, ["hello world"])
        results = retriever.retrieve(_query("hello world"), registry)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# 11. End-to-end: IngestionPipeline → SQLiteRetriever
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_ingested_content_is_retrievable(self, store, registry):
        src = _source()
        registry.register(src)
        pipeline = IngestionPipeline(registry, store)
        pipeline.ingest(IngestionRequest(source_id="src", content="hello world"))
        retriever = SQLiteRetriever(store)
        results = retriever.retrieve(_query("hello world"), registry)
        assert len(results) == 1
        assert results[0].source_id == "src"

    def test_re_ingested_content_replaces_previous(self, store, registry):
        src = _source()
        registry.register(src)
        pipeline = IngestionPipeline(registry, store)
        pipeline.ingest(IngestionRequest(source_id="src", content="original content"))
        pipeline.ingest(IngestionRequest(source_id="src", content="updated content"))
        retriever = SQLiteRetriever(store)
        # "original" should not appear
        results = retriever.retrieve(_query("original"), registry)
        assert results == []
        # "updated" should appear
        results = retriever.retrieve(_query("updated"), registry)
        assert len(results) == 1

    def test_multi_paragraph_ingest_retrievable_per_chunk(self, store, registry):
        src = _source()
        registry.register(src)
        pipeline = IngestionPipeline(registry, store)
        pipeline.ingest(
            IngestionRequest(
                source_id="src",
                content="first paragraph content\n\nsecond paragraph content",
            )
        )
        retriever = SQLiteRetriever(store)
        results = retriever.retrieve(_query("first paragraph"), registry)
        assert any("first" in r.content for r in results)
