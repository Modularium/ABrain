"""Tests for Phase 3 R3: IngestionPipeline and chunking logic.

Coverage:
1. IngestionRequest validation — empty content, whitespace, field limits
2. _split_chunks — paragraph splitting, hard-split, empty paragraphs
3. IngestionPipeline.ingest — happy path (trusted, clean source)
4. IngestionPipeline.ingest — unknown source_id raises KeyError
5. IngestionPipeline.ingest — chunks stored in DocumentStore
6. IngestionPipeline.ingest — advisory warnings: PII, license, UNTRUSTED
7. IngestionPipeline.ingest — re-ingest same source replaces chunks
8. IngestionPipeline.ingest — task_id echoed in result
"""

from __future__ import annotations

import pytest

from core.retrieval.document_store import SQLiteDocumentStore
from core.retrieval.ingestion import (
    IngestionPipeline,
    IngestionRequest,
    IngestionResult,
    _split_chunks,
)
from core.retrieval.models import KnowledgeSource, SourceTrust
from core.retrieval.registry import KnowledgeSourceRegistry

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source(
    source_id: str = "src",
    trust: SourceTrust = SourceTrust.TRUSTED,
    pii_risk: bool = False,
    license: str | None = None,
    retention_days: int | None = None,
) -> KnowledgeSource:
    kwargs: dict = {
        "source_id": source_id,
        "display_name": source_id,
        "trust": trust,
        "source_type": "document",
        "pii_risk": pii_risk,
        "license": license,
        "retention_days": retention_days,
    }
    if trust in (SourceTrust.EXTERNAL, SourceTrust.UNTRUSTED):
        kwargs["provenance"] = "https://example.com"
    return KnowledgeSource.model_validate(kwargs)


@pytest.fixture
def registry():
    return KnowledgeSourceRegistry()


@pytest.fixture
def store(tmp_path):
    return SQLiteDocumentStore(tmp_path / "test.sqlite3")


@pytest.fixture
def pipeline(registry, store):
    registry.register(_source())
    return IngestionPipeline(registry, store)


# ---------------------------------------------------------------------------
# 1. IngestionRequest validation
# ---------------------------------------------------------------------------


class TestIngestionRequestValidation:
    def test_valid_request(self):
        req = IngestionRequest(source_id="src", content="hello world")
        assert req.source_id == "src"
        assert req.content == "hello world"

    def test_empty_content_raises(self):
        with pytest.raises(Exception):
            IngestionRequest(source_id="src", content="")

    def test_whitespace_content_raises(self):
        with pytest.raises(Exception):
            IngestionRequest(source_id="src", content="   ")

    def test_content_is_stripped(self):
        req = IngestionRequest(source_id="src", content="  hello  ")
        assert req.content == "hello"

    def test_default_max_chunk_size(self):
        req = IngestionRequest(source_id="src", content="x")
        assert req.max_chunk_size == 1024

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            IngestionRequest(source_id="src", content="x", unknown_field="y")


# ---------------------------------------------------------------------------
# 2. _split_chunks
# ---------------------------------------------------------------------------


class TestSplitChunks:
    def test_single_paragraph_returned_as_one_chunk(self):
        chunks = _split_chunks("hello world", 1024)
        assert chunks == ["hello world"]

    def test_two_paragraphs_split_on_double_newline(self):
        chunks = _split_chunks("para one\n\npara two", 1024)
        assert chunks == ["para one", "para two"]

    def test_empty_paragraphs_discarded(self):
        chunks = _split_chunks("a\n\n\n\nb", 1024)
        assert chunks == ["a", "b"]

    def test_long_paragraph_hard_split(self):
        content = "x" * 200
        chunks = _split_chunks(content, 100)
        assert len(chunks) == 2
        assert all(len(c) <= 100 for c in chunks)

    def test_exactly_max_chunk_size_not_split(self):
        content = "x" * 100
        chunks = _split_chunks(content, 100)
        assert chunks == [content]

    def test_mixed_short_and_long_paragraphs(self):
        short = "short para"
        long_para = "y" * 300
        chunks = _split_chunks(f"{short}\n\n{long_para}", 100)
        assert chunks[0] == short
        assert all(len(c) <= 100 for c in chunks[1:])

    def test_whitespace_only_paragraph_discarded(self):
        chunks = _split_chunks("a\n\n   \n\nb", 1024)
        assert chunks == ["a", "b"]


# ---------------------------------------------------------------------------
# 3. IngestionPipeline.ingest — happy path
# ---------------------------------------------------------------------------


class TestIngestHappyPath:
    def test_ingest_returns_ingestion_result(self, pipeline):
        req = IngestionRequest(source_id="src", content="hello world")
        result = pipeline.ingest(req)
        assert isinstance(result, IngestionResult)

    def test_ingest_returns_correct_source_id(self, pipeline):
        result = pipeline.ingest(IngestionRequest(source_id="src", content="x"))
        assert result.source_id == "src"

    def test_ingest_returns_chunk_count(self, pipeline):
        result = pipeline.ingest(
            IngestionRequest(source_id="src", content="para one\n\npara two")
        )
        assert result.chunks_stored == 2

    def test_trusted_clean_source_no_warnings(self, pipeline):
        result = pipeline.ingest(IngestionRequest(source_id="src", content="hello"))
        assert result.warnings == []


# ---------------------------------------------------------------------------
# 4. Unknown source raises
# ---------------------------------------------------------------------------


class TestUnknownSource:
    def test_ingest_unknown_source_raises_key_error(self, registry, store):
        pipeline = IngestionPipeline(registry, store)
        with pytest.raises(KeyError):
            pipeline.ingest(IngestionRequest(source_id="ghost", content="hello"))


# ---------------------------------------------------------------------------
# 5. Chunks stored in DocumentStore
# ---------------------------------------------------------------------------


class TestChunksStoredInStore:
    def test_chunks_are_retrievable_after_ingest(self, registry, store):
        registry.register(_source())
        pipeline = IngestionPipeline(registry, store)
        pipeline.ingest(
            IngestionRequest(source_id="src", content="para one\n\npara two")
        )
        chunks = store.get_chunks("src")
        assert chunks == ["para one", "para two"]

    def test_chunk_count_matches_result(self, registry, store):
        registry.register(_source())
        pipeline = IngestionPipeline(registry, store)
        result = pipeline.ingest(
            IngestionRequest(source_id="src", content="a\n\nb\n\nc")
        )
        assert store.chunk_count("src") == result.chunks_stored


# ---------------------------------------------------------------------------
# 6. Advisory warnings
# ---------------------------------------------------------------------------


class TestAdvisoryWarnings:
    def test_pii_without_retention_warns(self, registry, store):
        registry.register(_source(source_id="pii-src", pii_risk=True))
        pipeline = IngestionPipeline(registry, store)
        result = pipeline.ingest(IngestionRequest(source_id="pii-src", content="x"))
        assert any("pii" in w.lower() or "retention" in w.lower() for w in result.warnings)

    def test_pii_with_retention_no_pii_warning(self, registry, store):
        registry.register(_source(source_id="pii-src", pii_risk=True, retention_days=30))
        pipeline = IngestionPipeline(registry, store)
        result = pipeline.ingest(IngestionRequest(source_id="pii-src", content="x"))
        assert not any("pii" in w.lower() for w in result.warnings)

    def test_external_without_license_warns(self, registry, store):
        registry.register(_source(source_id="ext-src", trust=SourceTrust.EXTERNAL))
        pipeline = IngestionPipeline(registry, store)
        result = pipeline.ingest(IngestionRequest(source_id="ext-src", content="x"))
        assert any("license" in w.lower() for w in result.warnings)

    def test_untrusted_always_warns(self, registry, store):
        registry.register(
            _source(source_id="un-src", trust=SourceTrust.UNTRUSTED, license="MIT")
        )
        pipeline = IngestionPipeline(registry, store)
        result = pipeline.ingest(IngestionRequest(source_id="un-src", content="x"))
        assert any("UNTRUSTED" in w for w in result.warnings)

    def test_trusted_with_license_zero_warnings(self, registry, store):
        registry.register(_source(source_id="ok-src", license="MIT"))
        pipeline = IngestionPipeline(registry, store)
        result = pipeline.ingest(IngestionRequest(source_id="ok-src", content="x"))
        assert result.warnings == []


# ---------------------------------------------------------------------------
# 7. Re-ingest replaces chunks
# ---------------------------------------------------------------------------


class TestReIngest:
    def test_re_ingest_replaces_chunks_in_store(self, registry, store):
        registry.register(_source())
        pipeline = IngestionPipeline(registry, store)
        pipeline.ingest(IngestionRequest(source_id="src", content="original"))
        pipeline.ingest(IngestionRequest(source_id="src", content="updated"))
        assert store.get_chunks("src") == ["updated"]

    def test_re_ingest_returns_new_chunk_count(self, registry, store):
        registry.register(_source())
        pipeline = IngestionPipeline(registry, store)
        pipeline.ingest(IngestionRequest(source_id="src", content="a\n\nb\n\nc"))
        result = pipeline.ingest(IngestionRequest(source_id="src", content="only one"))
        assert result.chunks_stored == 1


# ---------------------------------------------------------------------------
# 8. task_id echoed
# ---------------------------------------------------------------------------


class TestTaskId:
    def test_task_id_echoed_in_result(self, pipeline):
        result = pipeline.ingest(
            IngestionRequest(source_id="src", content="x", task_id="task-42")
        )
        assert result.task_id == "task-42"

    def test_task_id_none_when_not_provided(self, pipeline):
        result = pipeline.ingest(IngestionRequest(source_id="src", content="x"))
        assert result.task_id is None
