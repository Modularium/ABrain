"""Canonical data models for the ABrain retrieval layer.

Phase 3 — "Retrieval- und Wissensschicht", Step R1.

This module defines the single source of truth for all retrieval-related
types in ABrain.  No implementation logic lives here — only well-typed,
Pydantic-validated data contracts.

Design invariants
-----------------
- ``extra="forbid"`` on every model — governance fields must not drift silently.
- ``SourceTrust`` is the canonical trust taxonomy for all knowledge sources.
- ``RetrievalScope`` is intentionally restricted: there is no "critical_action"
  scope.  Retrieval results must never directly drive safety-critical decisions.
- ``KnowledgeSource`` represents a registered source with provenance.
- ``RetrievalQuery`` is the governance-aware query contract.
- ``RetrievalResult`` is the attributed, trust-labeled result contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceTrust(StrEnum):
    """Trust classification for a knowledge source.

    Levels are ordered from most to least trusted.  The classification
    determines which ``RetrievalScope`` operations are permitted with results
    from that source.

    TRUSTED
        First-party, verified content.  Examples: system documentation,
        internal codebase, validated training data.  Permitted for all scopes.
    INTERNAL
        Internal but less strictly controlled content.  Examples: internal
        wikis, engineering tickets, team notes.  Permitted for all scopes;
        provenance is always required.
    EXTERNAL
        Third-party content with controlled access.  Examples: licensed
        datasets, known public APIs, vendor documentation.  Permitted for
        explanation and assistance scopes; triggers a warning for planning scope.
    UNTRUSTED
        Unverified content.  Examples: public web, user-provided inputs,
        scraped pages.  Permitted only for explanation and assistance scopes;
        forbidden for planning scope.
    """

    TRUSTED = "trusted"
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNTRUSTED = "untrusted"


class RetrievalScope(StrEnum):
    """Permitted use-case scope for retrieval results.

    ABrain restricts retrieval to three safe scopes.  There is deliberately
    no "action" or "execution" scope: retrieval results must never be the
    direct, unmediated input to safety-critical actions.

    EXPLANATION
        Explain why a routing decision, approval outcome, or plan was chosen.
        Used in explainability and audit flows.  All trust levels permitted.
    ASSISTANCE
        General question answering, context provision, summaries.  All trust
        levels permitted with appropriate attribution.
    PLANNING
        Help sequence, prioritise, or structure a task.  Restricted to
        TRUSTED and INTERNAL sources; EXTERNAL triggers a warning; UNTRUSTED
        is forbidden.
    """

    EXPLANATION = "explanation"
    ASSISTANCE = "assistance"
    PLANNING = "planning"


class KnowledgeSource(BaseModel):
    """Registered knowledge source with governance metadata.

    A ``KnowledgeSource`` is the canonical declaration of a retrievable
    corpus.  It carries the provenance, trust, and data-governance facts
    needed for policy matching, audit attribution, and retention enforcement.

    Attributes
    ----------
    source_id:
        Stable, unique identifier for this source (slug format).
    display_name:
        Human-readable name for UI and audit display.
    trust:
        Governance trust classification.
    source_type:
        Category of content (e.g. "document", "code", "api", "web").
    provenance:
        Where the content came from — URL, filepath, vendor name, etc.
        Required for EXTERNAL and UNTRUSTED sources to enable audit attribution.
    pii_risk:
        True if the source may contain personally identifiable information.
        PII sources require explicit retention and access controls.
    license:
        SPDX identifier or free-text license description.  None means unknown.
        Unknown license on EXTERNAL sources triggers an operator warning.
    retention_days:
        Maximum number of days retrieved content from this source may be
        cached or stored.  None means no retention limit (operator's risk).
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    trust: SourceTrust
    source_type: str = Field(min_length=1, max_length=64)
    provenance: str | None = Field(default=None, max_length=2048)
    pii_risk: bool = False
    license: str | None = Field(default=None, max_length=256)
    retention_days: int | None = Field(default=None, ge=1)

    @field_validator("source_id", "display_name", "source_type")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty or whitespace-only")
        return normalized

    @field_validator("provenance")
    @classmethod
    def normalize_provenance(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RetrievalQuery(BaseModel):
    """Governance-aware retrieval query.

    A ``RetrievalQuery`` specifies not just what to retrieve but under which
    governance constraints.  ``scope`` and ``allowed_trust_levels`` are
    evaluated by ``RetrievalBoundary`` before any backend is called.

    Attributes
    ----------
    query_text:
        The natural-language or structured query.
    scope:
        The intended use of the retrieved content.  Must be one of the
        ``RetrievalScope`` values — there is no action scope.
    allowed_trust_levels:
        The set of ``SourceTrust`` levels the caller accepts.  If empty,
        all levels are conceptually permitted (governance enforcement
        still applies to the scope).
    task_id:
        Optional task identifier for audit attribution.
    max_results:
        Maximum number of results to return.  Defaults to 5.
    """

    model_config = ConfigDict(extra="forbid")

    query_text: str = Field(min_length=1, max_length=4096)
    scope: RetrievalScope
    allowed_trust_levels: list[SourceTrust] = Field(default_factory=list)
    task_id: str | None = Field(default=None, max_length=128)
    max_results: int = Field(default=5, ge=1, le=50)

    @field_validator("query_text")
    @classmethod
    def normalize_query_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query_text must not be empty or whitespace-only")
        return normalized

    @field_validator("allowed_trust_levels")
    @classmethod
    def deduplicate_trust_levels(cls, values: list[SourceTrust]) -> list[SourceTrust]:
        seen: set[SourceTrust] = set()
        result: list[SourceTrust] = []
        for v in values:
            if v not in seen:
                seen.add(v)
                result.append(v)
        return result


class RetrievalResult(BaseModel):
    """Attributed, trust-labeled retrieval result.

    Every ``RetrievalResult`` carries the source's trust classification and
    provenance so that downstream consumers can make informed decisions about
    how much weight to place on the content.  Results from lower-trust sources
    carry advisory warnings injected by ``RetrievalBoundary``.

    Attributes
    ----------
    source_id:
        Identifier of the ``KnowledgeSource`` this result came from.
    trust:
        Trust level of the source — always present, never inferred post-hoc.
    content:
        The retrieved text.  May not be empty.
    score:
        Relevance score in [0.0, 1.0].  Higher is more relevant.
    provenance:
        Originating URL, filepath, or document reference for attribution.
    retrieved_at:
        ISO-8601 UTC timestamp of when the result was retrieved.
    warnings:
        Advisory messages added by ``RetrievalBoundary`` (e.g. trust
        downgrade warnings, planning-scope restrictions).
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=128)
    trust: SourceTrust
    content: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    provenance: str | None = Field(default=None, max_length=2048)
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    warnings: list[str] = Field(default_factory=list)
