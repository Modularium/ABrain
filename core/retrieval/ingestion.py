"""Ingestion pipeline for the ABrain retrieval layer.

Phase 3 — "Retrieval- und Wissensschicht", Step R3.

``IngestionPipeline`` is the single controlled entry-point for storing content
into the retrieval layer.  It validates governance constraints from the source
registry, splits content into chunks, and persists them via a ``DocumentStore``.

Design invariants
-----------------
- All content enters the retrieval layer only through ``IngestionPipeline``.
- The pipeline does NOT modify content — it only splits and stores.
- Governance is advisory at ingest time (warnings returned, never silently
  swallowed).  Hard violations (unregistered source) raise immediately.
- Chunking is deterministic: same input always produces the same chunks.
- No LLM calls, no network I/O, no heavy dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .document_store import DocumentStore
from .models import KnowledgeSource, SourceTrust
from .registry import KnowledgeSourceRegistry


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class IngestionRequest(BaseModel):
    """Request to ingest content into a knowledge source.

    Attributes
    ----------
    source_id:
        The registered ``KnowledgeSource`` to ingest into.
    content:
        Raw text content to ingest.  May not be empty.
    max_chunk_size:
        Maximum character length per chunk.  Content is split on paragraph
        boundaries (double-newline) first; lines exceeding ``max_chunk_size``
        are hard-split at that boundary.  Defaults to 1024.
    task_id:
        Optional task identifier for audit attribution.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1)
    max_chunk_size: int = Field(default=1024, ge=64, le=32768)
    task_id: str | None = Field(default=None, max_length=128)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content must not be empty or whitespace-only")
        return normalized


class IngestionResult(BaseModel):
    """Result of a completed ingestion operation.

    Attributes
    ----------
    source_id:
        The knowledge source content was ingested into.
    chunks_stored:
        Number of chunks written to the document store.
    warnings:
        Advisory messages from governance checks.  Non-empty does not
        mean ingestion failed — it means the operator should review.
    ingested_at:
        ISO-8601 UTC timestamp of the ingestion.
    task_id:
        Echoed from the request for audit attribution.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str
    chunks_stored: int
    warnings: list[str] = Field(default_factory=list)
    ingested_at: str = Field(default_factory=_utcnow)
    task_id: str | None = None


# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------


def _split_chunks(content: str, max_chunk_size: int) -> list[str]:
    """Split *content* into chunks no larger than *max_chunk_size* characters.

    Strategy:
    1. Split on double-newline (paragraph boundary) to preserve semantic units.
    2. Any paragraph that still exceeds ``max_chunk_size`` is hard-split.
    3. Empty paragraphs are discarded.
    """
    paragraphs = [p.strip() for p in content.split("\n\n")]
    chunks: list[str] = []
    for para in paragraphs:
        if not para:
            continue
        if len(para) <= max_chunk_size:
            chunks.append(para)
        else:
            # Hard-split long paragraph
            start = 0
            while start < len(para):
                chunks.append(para[start : start + max_chunk_size])
                start += max_chunk_size
    return chunks


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class IngestionPipeline:
    """Governance-aware ingestion pipeline.

    The pipeline validates source governance rules before storing anything,
    applies the chunking strategy, and delegates persistence to the provided
    ``DocumentStore``.

    Usage
    -----
    >>> pipeline = IngestionPipeline(registry, store)
    >>> result = pipeline.ingest(IngestionRequest(source_id="src-1", content="..."))
    >>> result.chunks_stored
    3
    >>> result.warnings
    []
    """

    def __init__(
        self,
        registry: KnowledgeSourceRegistry,
        store: DocumentStore,
    ) -> None:
        self._registry = registry
        self._store = store

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        """Validate, chunk, and store content for the requested source.

        Parameters
        ----------
        request:
            The validated ``IngestionRequest``.

        Returns
        -------
        IngestionResult
            The outcome with chunk count and advisory warnings.

        Raises
        ------
        KeyError
            When ``request.source_id`` is not registered in the registry.
        """
        source = self._registry.get(request.source_id)
        warnings = _governance_warnings(source)

        chunks = _split_chunks(request.content, request.max_chunk_size)
        stored = self._store.store_chunks(
            request.source_id,
            chunks,
            metadata={"task_id": request.task_id, "source_trust": source.trust},
        )

        return IngestionResult(
            source_id=request.source_id,
            chunks_stored=stored,
            warnings=warnings,
            task_id=request.task_id,
        )


# ---------------------------------------------------------------------------
# Internal governance helpers
# ---------------------------------------------------------------------------


def _governance_warnings(source: KnowledgeSource) -> list[str]:
    """Return advisory warnings for the source at ingest time."""
    warnings: list[str] = []

    if source.pii_risk and source.retention_days is None:
        warnings.append(
            f"Source '{source.source_id}' has pii_risk=True but no retention_days "
            f"declared.  Ensure a data-retention policy is in place before "
            f"storing PII-bearing content."
        )

    if source.trust in (SourceTrust.EXTERNAL, SourceTrust.UNTRUSTED):
        if source.license is None:
            warnings.append(
                f"Source '{source.source_id}' has trust={source.trust!r} "
                f"but no license declared.  Verify licensing before ingesting "
                f"this content into production."
            )

    if source.trust == SourceTrust.UNTRUSTED:
        warnings.append(
            f"Source '{source.source_id}' is UNTRUSTED.  Ingested content "
            f"must only be used for explanation/assistance scopes — never "
            f"for planning or direct action."
        )

    return warnings
