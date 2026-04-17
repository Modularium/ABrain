"""Retrieval port and in-memory reference implementation.

Phase 3 — "Retrieval- und Wissensschicht", Step R2.

``RetrievalPort`` is the abstract interface every backend must satisfy.
``InMemoryRetriever`` is a lightweight keyword-overlap implementation used in
tests and local development — it requires no external dependencies.

Design invariants
-----------------
- ``RetrievalPort`` is a ``typing.Protocol`` — structural typing, no ABC.
- ``InMemoryRetriever`` applies trust-level filtering from the registry,
  scores by word-overlap, respects ``query.max_results``, and calls
  ``RetrievalBoundary.annotate_results()`` before returning.
- No heavy dependencies (no numpy, no vector store, no LLM calls).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .boundaries import RetrievalBoundary
from .models import KnowledgeSource, RetrievalQuery, RetrievalResult, SourceTrust
from .registry import KnowledgeSourceRegistry


@runtime_checkable
class RetrievalPort(Protocol):
    """Abstract interface for retrieval backends.

    Any object implementing this protocol can be used as a retrieval
    backend in the orchestration layer.
    """

    def retrieve(
        self,
        query: RetrievalQuery,
        registry: KnowledgeSourceRegistry,
    ) -> list[RetrievalResult]:
        """Return results for ``query`` from sources in ``registry``.

        Implementations must:
        - Respect ``query.allowed_trust_levels`` — if non-empty, only
          return results from sources whose trust level is in the list.
        - Return at most ``query.max_results`` results.
        - Not mutate ``query`` or any registered source.

        Governance annotations (warnings) are the retriever's responsibility
        or may be delegated to ``RetrievalBoundary.annotate_results()``.
        """
        ...


class InMemoryRetriever:
    """Keyword-overlap retriever backed by an in-process document store.

    Intended for tests and local development.  Persistence, embedding,
    and semantic search are out of scope.

    Usage
    -----
    >>> retriever = InMemoryRetriever()
    >>> retriever.add_documents("source-id", ["chunk one", "chunk two"])
    >>> results = retriever.retrieve(query, registry)
    """

    def __init__(self) -> None:
        self._docs: dict[str, list[str]] = {}
        self._boundary = RetrievalBoundary()

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def add_documents(self, source_id: str, chunks: list[str]) -> None:
        """Add text chunks for a source.

        Replaces any previously stored chunks for ``source_id``.
        The source must be registered in the registry at retrieval time
        (not at indexing time) to allow flexible test setups.
        """
        self._docs[source_id] = list(chunks)

    def remove_documents(self, source_id: str) -> None:
        """Remove all stored chunks for ``source_id``.

        Raises
        ------
        KeyError
            When ``source_id`` has no stored documents.
        """
        if source_id not in self._docs:
            raise KeyError(f"No documents stored for source '{source_id}'.")
        del self._docs[source_id]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: RetrievalQuery,
        registry: KnowledgeSourceRegistry,
    ) -> list[RetrievalResult]:
        """Return annotated results scored by keyword overlap.

        Only sources present in both the document store and the registry
        are considered.  If ``query.allowed_trust_levels`` is non-empty,
        sources whose trust level is not in the list are skipped.
        """
        query_tokens = _tokenize(query.query_text)
        allowed = set(query.allowed_trust_levels)

        candidates: list[tuple[float, str, str, KnowledgeSource]] = []

        for source_id, chunks in self._docs.items():
            if not registry.is_registered(source_id):
                continue
            source = registry.get(source_id)
            if allowed and source.trust not in allowed:
                continue

            for chunk in chunks:
                score = _overlap_score(query_tokens, _tokenize(chunk))
                if score > 0.0:
                    candidates.append((score, source_id, chunk, source))

        candidates.sort(key=lambda t: t[0], reverse=True)
        top = candidates[: query.max_results]

        raw_results = [
            RetrievalResult(
                source_id=source_id,
                trust=source.trust,
                content=chunk,
                score=score,
                provenance=source.provenance,
            )
            for score, source_id, chunk, source in top
        ]

        return self._boundary.annotate_results(raw_results, query)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> set[str]:
    """Return lowercase word tokens from *text*."""
    return {w.lower().strip(".,!?;:\"'()[]{}") for w in text.split() if w.strip()}


def _overlap_score(query_tokens: set[str], doc_tokens: set[str]) -> float:
    """Jaccard-style overlap: |intersection| / |query|.

    Returns 0.0 when the query token set is empty.
    """
    if not query_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / len(query_tokens)
