"""Knowledge source registry — the single list of retrievable corpora.

Phase 3 — "Retrieval- und Wissensschicht", Step R2.

``KnowledgeSourceRegistry`` is the canonical authority for which
``KnowledgeSource`` objects are available to the retrieval layer.  It
enforces governance invariants at registration time so that the retriever
only ever sees pre-validated sources.

Governance rules enforced at registration
-----------------------------------------
1. ``source_id`` must be unique — re-registering a different source under the
   same id is rejected with ``RegistrationError``.  Idempotent re-registration
   of the *exact same* source object is a no-op.
2. ``EXTERNAL`` and ``UNTRUSTED`` sources must declare ``provenance`` — without
   a traceable origin, audit attribution is impossible.
3. Sources with ``pii_risk=True`` should declare ``retention_days``.  This is
   an advisory check: registration succeeds, but a warning is returned so the
   operator can act on it.

Design invariants
-----------------
- Pure in-process store, no persistence.  Persistence is a Phase-3 ingestion
  concern (R3 and later).
- Thread-safety is *not* guaranteed; callers must synchronise if needed.
- ``extra="forbid"`` is on ``KnowledgeSource`` (from R1 models), so invalid
  sources are rejected before reaching this registry.
"""

from __future__ import annotations

from .models import KnowledgeSource, SourceTrust


class RegistrationError(ValueError):
    """Raised when a source fails governance validation at registration time."""


class KnowledgeSourceRegistry:
    """Manage the set of retrievable knowledge sources.

    Attributes
    ----------
    sources:
        Read-only view of registered sources keyed by ``source_id``.

    Usage
    -----
    >>> registry = KnowledgeSourceRegistry()
    >>> registry.register(source)           # raises RegistrationError on conflict
    >>> src = registry.get("my-source")    # raises KeyError if absent
    >>> all_sources = registry.list_all()
    >>> trusted = registry.list_by_trust(SourceTrust.TRUSTED)
    """

    def __init__(self) -> None:
        self._sources: dict[str, KnowledgeSource] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, source: KnowledgeSource) -> list[str]:
        """Register a knowledge source and return advisory warnings.

        Idempotent: registering the exact same ``KnowledgeSource`` object
        (same ``source_id`` AND same content) is a no-op and returns no warnings.

        Parameters
        ----------
        source:
            The ``KnowledgeSource`` to register.

        Returns
        -------
        list[str]
            Advisory warnings (non-empty when, for example, a PII source lacks
            a retention policy).  Registration succeeds even when warnings are
            returned.

        Raises
        ------
        RegistrationError
            When the ``source_id`` is already registered under a *different*
            source, or when a governance invariant is violated (e.g. EXTERNAL
            source without provenance).
        """
        existing = self._sources.get(source.source_id)
        if existing is not None:
            if existing == source:
                return []
            raise RegistrationError(
                f"Source '{source.source_id}' is already registered under a "
                f"different definition.  Deregister it first or use a new source_id."
            )

        self._validate_governance(source)
        self._sources[source.source_id] = source
        return self._advisory_warnings(source)

    def deregister(self, source_id: str) -> None:
        """Remove a source from the registry.

        Raises
        ------
        KeyError
            When ``source_id`` is not registered.
        """
        if source_id not in self._sources:
            raise KeyError(f"Source '{source_id}' is not registered.")
        del self._sources[source_id]

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, source_id: str) -> KnowledgeSource:
        """Return the registered source for ``source_id``.

        Raises
        ------
        KeyError
            When ``source_id`` is not registered.
        """
        try:
            return self._sources[source_id]
        except KeyError:
            raise KeyError(f"Source '{source_id}' is not registered.")

    def is_registered(self, source_id: str) -> bool:
        """Return True if ``source_id`` is in the registry."""
        return source_id in self._sources

    def list_all(self) -> list[KnowledgeSource]:
        """Return all registered sources in registration order."""
        return list(self._sources.values())

    def list_by_trust(self, trust: SourceTrust) -> list[KnowledgeSource]:
        """Return all registered sources with the given trust level."""
        return [s for s in self._sources.values() if s.trust == trust]

    def __len__(self) -> int:
        return len(self._sources)

    # ------------------------------------------------------------------
    # Internal governance checks
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_governance(source: KnowledgeSource) -> None:
        """Raise ``RegistrationError`` for hard governance violations."""
        if source.trust in (SourceTrust.EXTERNAL, SourceTrust.UNTRUSTED):
            if not source.provenance:
                raise RegistrationError(
                    f"Source '{source.source_id}' has trust={source.trust!r} "
                    f"but no provenance declared.  EXTERNAL and UNTRUSTED sources "
                    f"must supply provenance for audit attribution."
                )

    @staticmethod
    def _advisory_warnings(source: KnowledgeSource) -> list[str]:
        """Return non-fatal advisory messages for the registered source."""
        warnings: list[str] = []
        if source.pii_risk and source.retention_days is None:
            warnings.append(
                f"Source '{source.source_id}' has pii_risk=True but no "
                f"retention_days declared.  Define a retention policy to comply "
                f"with data-governance requirements."
            )
        if source.trust in (SourceTrust.EXTERNAL, SourceTrust.UNTRUSTED):
            if source.license is None:
                warnings.append(
                    f"Source '{source.source_id}' has trust={source.trust!r} "
                    f"but no license declared.  Verify licensing before using "
                    f"this source in production."
                )
        return warnings
