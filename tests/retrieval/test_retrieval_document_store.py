"""Tests for Phase 3 R3: SQLiteDocumentStore and DocumentStore protocol.

Coverage:
1. Protocol conformance — SQLiteDocumentStore satisfies DocumentStore
2. store_chunks — happy path, returns count
3. store_chunks — idempotent re-ingest replaces previous chunks
4. store_chunks — empty source_id raises ValueError
5. get_chunks — returns chunks in index order
6. get_chunks — unknown source returns empty list
7. delete_chunks — removes stored chunks, returns count
8. delete_chunks — unknown source returns 0
9. list_sources — returns distinct source_ids
10. chunk_count — counts correctly after store/delete
"""

from __future__ import annotations

import pytest

from core.retrieval.document_store import DocumentStore, SQLiteDocumentStore

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    return SQLiteDocumentStore(tmp_path / "test.sqlite3")


# ---------------------------------------------------------------------------
# 1. Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_sqlite_document_store_satisfies_protocol(self, store):
        assert isinstance(store, DocumentStore)


# ---------------------------------------------------------------------------
# 2. store_chunks — happy path
# ---------------------------------------------------------------------------


class TestStoreChunks:
    def test_store_chunks_returns_count(self, store):
        count = store.store_chunks("src-1", ["a", "b", "c"])
        assert count == 3

    def test_store_empty_chunks_returns_zero(self, store):
        count = store.store_chunks("src-1", [])
        assert count == 0

    def test_store_single_chunk(self, store):
        count = store.store_chunks("src-1", ["only one"])
        assert count == 1

    def test_empty_source_id_raises(self, store):
        with pytest.raises(ValueError):
            store.store_chunks("", ["content"])

    def test_whitespace_source_id_raises(self, store):
        with pytest.raises(ValueError):
            store.store_chunks("   ", ["content"])


# ---------------------------------------------------------------------------
# 3. store_chunks — idempotent re-ingest
# ---------------------------------------------------------------------------


class TestIdempotentIngest:
    def test_re_ingest_replaces_previous_chunks(self, store):
        store.store_chunks("src-1", ["old-a", "old-b"])
        store.store_chunks("src-1", ["new-a"])
        chunks = store.get_chunks("src-1")
        assert chunks == ["new-a"]

    def test_re_ingest_does_not_grow_chunk_count(self, store):
        store.store_chunks("src-1", ["a", "b", "c"])
        store.store_chunks("src-1", ["x", "y"])
        assert store.chunk_count("src-1") == 2

    def test_re_ingest_with_empty_clears_previous(self, store):
        store.store_chunks("src-1", ["a", "b"])
        store.store_chunks("src-1", [])
        assert store.get_chunks("src-1") == []


# ---------------------------------------------------------------------------
# 4. get_chunks
# ---------------------------------------------------------------------------


class TestGetChunks:
    def test_returns_chunks_in_index_order(self, store):
        store.store_chunks("src-1", ["first", "second", "third"])
        assert store.get_chunks("src-1") == ["first", "second", "third"]

    def test_unknown_source_returns_empty_list(self, store):
        assert store.get_chunks("nonexistent") == []

    def test_two_sources_do_not_mix(self, store):
        store.store_chunks("src-a", ["alpha"])
        store.store_chunks("src-b", ["beta"])
        assert store.get_chunks("src-a") == ["alpha"]
        assert store.get_chunks("src-b") == ["beta"]


# ---------------------------------------------------------------------------
# 5. delete_chunks
# ---------------------------------------------------------------------------


class TestDeleteChunks:
    def test_delete_removes_chunks(self, store):
        store.store_chunks("src-1", ["a", "b"])
        store.delete_chunks("src-1")
        assert store.get_chunks("src-1") == []

    def test_delete_returns_count(self, store):
        store.store_chunks("src-1", ["a", "b", "c"])
        count = store.delete_chunks("src-1")
        assert count == 3

    def test_delete_unknown_source_returns_zero(self, store):
        assert store.delete_chunks("nonexistent") == 0

    def test_delete_only_affects_target_source(self, store):
        store.store_chunks("src-a", ["a"])
        store.store_chunks("src-b", ["b"])
        store.delete_chunks("src-a")
        assert store.get_chunks("src-b") == ["b"]


# ---------------------------------------------------------------------------
# 6. list_sources
# ---------------------------------------------------------------------------


class TestListSources:
    def test_empty_store_returns_empty_list(self, store):
        assert store.list_sources() == []

    def test_returns_all_distinct_source_ids(self, store):
        store.store_chunks("src-a", ["a"])
        store.store_chunks("src-b", ["b"])
        sources = store.list_sources()
        assert set(sources) == {"src-a", "src-b"}

    def test_deleted_source_not_in_list(self, store):
        store.store_chunks("src-a", ["a"])
        store.delete_chunks("src-a")
        assert store.list_sources() == []

    def test_source_listed_once_even_after_re_ingest(self, store):
        store.store_chunks("src-a", ["a"])
        store.store_chunks("src-a", ["b"])
        assert store.list_sources().count("src-a") == 1


# ---------------------------------------------------------------------------
# 7. chunk_count
# ---------------------------------------------------------------------------


class TestChunkCount:
    def test_count_zero_for_unknown_source(self, store):
        assert store.chunk_count("nonexistent") == 0

    def test_count_matches_stored(self, store):
        store.store_chunks("src-1", ["a", "b", "c"])
        assert store.chunk_count("src-1") == 3

    def test_count_after_delete_is_zero(self, store):
        store.store_chunks("src-1", ["a"])
        store.delete_chunks("src-1")
        assert store.chunk_count("src-1") == 0

    def test_count_after_re_ingest_reflects_new_count(self, store):
        store.store_chunks("src-1", ["a", "b", "c"])
        store.store_chunks("src-1", ["x"])
        assert store.chunk_count("src-1") == 1


# ---------------------------------------------------------------------------
# 8. Persistence — data survives reconnect
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_chunks_survive_reconnect(self, tmp_path):
        path = tmp_path / "persistent.sqlite3"
        store1 = SQLiteDocumentStore(path)
        store1.store_chunks("src-1", ["persist me"])
        store2 = SQLiteDocumentStore(path)
        assert store2.get_chunks("src-1") == ["persist me"]
