"""Durable document store for the ABrain retrieval layer.

Phase 3 — "Retrieval- und Wissensschicht", Step R3.

``DocumentStore`` is the abstract protocol every storage backend must satisfy.
``SQLiteDocumentStore`` is the canonical production implementation, following
the same SQLite-backed pattern as ``TraceStore`` and ``ApprovalStore``.

Design invariants
-----------------
- ``DocumentStore`` is a ``typing.Protocol`` — structural typing, no ABC.
- ``SQLiteDocumentStore`` is the single persistent truth for ingested document
  chunks.  It mirrors the schema-on-first-connect pattern of ``TraceStore``.
- Chunk IDs are deterministic: ``<source_id>:<chunk_index>`` — idempotent
  re-ingestion of the same source replaces rather than duplicates chunks.
- No retrieval scoring logic lives here — this is a pure storage layer.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class DocumentStore(Protocol):
    """Abstract interface for document chunk storage backends.

    Any object implementing this protocol can be used as the persistence
    layer for ``IngestionPipeline`` and retrieval backends.
    """

    def store_chunks(
        self,
        source_id: str,
        chunks: list[str],
        *,
        metadata: dict | None = None,
    ) -> int:
        """Persist *chunks* for *source_id*, replacing any previous chunks.

        Returns the number of chunks stored.
        """
        ...

    def get_chunks(self, source_id: str) -> list[str]:
        """Return all stored chunks for *source_id*, in index order.

        Returns an empty list when no chunks are stored.
        """
        ...

    def delete_chunks(self, source_id: str) -> int:
        """Delete all stored chunks for *source_id*.

        Returns the number of chunks deleted.  Returns 0 when nothing was stored.
        """
        ...

    def list_sources(self) -> list[str]:
        """Return source_ids that have at least one stored chunk."""
        ...


# ---------------------------------------------------------------------------
# SQLite implementation
# ---------------------------------------------------------------------------


class SQLiteDocumentStore:
    """SQLite-backed document chunk store.

    Usage
    -----
    >>> store = SQLiteDocumentStore("runtime/abrain_documents.sqlite3")
    >>> store.store_chunks("src-1", ["chunk one", "chunk two"])
    2
    >>> store.get_chunks("src-1")
    ['chunk one', 'chunk two']
    >>> store.delete_chunks("src-1")
    2

    Schema
    ------
    ``document_chunks`` table:

    +---------------+------+---------+
    | column        | type | notes   |
    +---------------+------+---------+
    | chunk_id      | TEXT | PK, deterministic: ``<source_id>:<index>`` |
    | source_id     | TEXT | FK-like, indexed |
    | chunk_index   | INT  | 0-based position within source |
    | content       | TEXT | raw chunk text |
    | ingested_at   | TEXT | ISO-8601 UTC |
    | metadata_json | TEXT | JSON object |
    +---------------+------+---------+

    Idempotency
    -----------
    ``store_chunks`` first deletes all existing chunks for ``source_id``,
    then inserts the new ones.  This makes re-ingestion safe and deterministic.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store_chunks(
        self,
        source_id: str,
        chunks: list[str],
        *,
        metadata: dict | None = None,
    ) -> int:
        """Replace all stored chunks for *source_id* with *chunks*.

        Returns the number of chunks stored.
        """
        if not source_id or not source_id.strip():
            raise ValueError("source_id must not be empty")
        meta_json = json.dumps(metadata or {}, sort_keys=True)
        now = _utcnow()
        rows = [
            (
                f"{source_id}:{i}",
                source_id,
                i,
                chunk,
                now,
                meta_json,
            )
            for i, chunk in enumerate(chunks)
        ]
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM document_chunks WHERE source_id = ?", (source_id,)
            )
            conn.executemany(
                """
                INSERT INTO document_chunks
                    (chunk_id, source_id, chunk_index, content, ingested_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(chunks)

    def get_chunks(self, source_id: str) -> list[str]:
        """Return stored chunks for *source_id* in index order."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT content FROM document_chunks
                WHERE source_id = ?
                ORDER BY chunk_index ASC
                """,
                (source_id,),
            )
            return [row[0] for row in cursor.fetchall()]

    def delete_chunks(self, source_id: str) -> int:
        """Delete all chunks for *source_id*.  Returns count deleted."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM document_chunks WHERE source_id = ?", (source_id,)
            )
            return cursor.rowcount

    def list_sources(self) -> list[str]:
        """Return distinct source_ids with at least one stored chunk."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT source_id FROM document_chunks ORDER BY source_id"
            )
            return [row[0] for row in cursor.fetchall()]

    def chunk_count(self, source_id: str) -> int:
        """Return number of stored chunks for *source_id*."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM document_chunks WHERE source_id = ?",
                (source_id,),
            )
            return cursor.fetchone()[0]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id      TEXT PRIMARY KEY,
                    source_id     TEXT NOT NULL,
                    chunk_index   INTEGER NOT NULL,
                    content       TEXT NOT NULL,
                    ingested_at   TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_source_id
                ON document_chunks (source_id)
                """
            )
