"""Provenance and license governance scanner — §6.4 Data Governance.

Read-only governance report over ``KnowledgeSourceRegistry``. For each
registered source, the scanner evaluates a frozen ``ProvenancePolicy``
and produces a typed ``ProvenanceReport`` listing compliance findings
(missing provenance, missing license, missing retention policy).

Analogous to ``RetentionScanner`` but for the retrieval data layer
rather than the audit stores. Composes cleanly with the existing
registry — it does not re-implement registration-time validation; it
extends visibility to the *current* state of all registered sources
under an operator-defined policy that can be tightened post-hoc.

Strictly read-only:

- no writes to the registry;
- no second governance source of truth — the registry remains canonical;
- no audit-log write — the caller owns the operator audit trail;
- no overlap with ``RetentionPolicy``: this policy evaluates **source
  metadata** (provenance / license / retention-declaration presence),
  not record age.

Stdlib + pydantic only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import KnowledgeSource, SourceTrust
from .registry import KnowledgeSourceRegistry

ProvenanceFindingKind = Literal[
    "provenance_missing",
    "license_missing",
    "retention_missing_for_pii",
    "retention_missing",
]


class ProvenancePolicy(BaseModel):
    """Frozen governance policy for the provenance scanner.

    Every field narrows or expands what the scanner counts as a
    finding. Defaults mirror the registry's registration-time checks
    (provenance / license for EXTERNAL and UNTRUSTED; retention for
    PII sources) so a default scan reports the same surface area as
    registration, but can be tightened by an operator.
    """

    model_config = ConfigDict(extra="forbid")

    require_provenance_for: list[SourceTrust] = Field(
        default_factory=lambda: [SourceTrust.EXTERNAL, SourceTrust.UNTRUSTED],
        description="Trust levels where missing provenance is a finding.",
    )
    require_license_for: list[SourceTrust] = Field(
        default_factory=lambda: [SourceTrust.EXTERNAL, SourceTrust.UNTRUSTED],
        description="Trust levels where missing license is a finding.",
    )
    require_retention_for_pii: bool = Field(
        default=True,
        description="Flag sources with pii_risk=True and no retention_days.",
    )
    require_retention_for_all: bool = Field(
        default=False,
        description="Flag *every* source without retention_days, regardless of PII.",
    )

    @field_validator("require_provenance_for", "require_license_for")
    @classmethod
    def _dedupe(cls, values: list[SourceTrust]) -> list[SourceTrust]:
        seen: set[SourceTrust] = set()
        deduped: list[SourceTrust] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                deduped.append(value)
        return deduped


class ProvenanceFinding(BaseModel):
    """One compliance finding on one source."""

    model_config = ConfigDict(extra="forbid")

    kind: ProvenanceFindingKind
    message: str = Field(min_length=1, max_length=512)


class ProvenanceSourceStatus(BaseModel):
    """Per-source compliance snapshot.

    ``compliant`` is ``True`` when ``findings`` is empty. The explicit
    booleans (``has_provenance`` / ``has_license``) and the raw
    ``retention_days`` are included so downstream tooling can render
    a governance table without re-reading the registry.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=128)
    trust: SourceTrust
    pii_risk: bool
    has_provenance: bool
    has_license: bool
    retention_days: int | None = Field(default=None, ge=1)
    findings: list[ProvenanceFinding] = Field(default_factory=list)
    compliant: bool


class ProvenanceTotals(BaseModel):
    """Aggregate counts for a provenance report."""

    model_config = ConfigDict(extra="forbid")

    sources_scanned: int = Field(ge=0)
    compliant_sources: int = Field(ge=0)
    sources_with_findings: int = Field(ge=0)
    finding_counts: dict[str, int] = Field(default_factory=dict)


class ProvenanceReport(BaseModel):
    """Scanner output: per-source compliance statuses plus policy context."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    policy: ProvenancePolicy
    statuses: list[ProvenanceSourceStatus] = Field(default_factory=list)
    totals: ProvenanceTotals


class ProvenanceScanner:
    """Scan a ``KnowledgeSourceRegistry`` for provenance/license findings.

    Parameters
    ----------
    registry:
        Canonical ``KnowledgeSourceRegistry``. Read-only usage
        (``list_all``).
    policy:
        Frozen ``ProvenancePolicy`` instance.
    """

    def __init__(
        self,
        *,
        registry: KnowledgeSourceRegistry,
        policy: ProvenancePolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or ProvenancePolicy()

    def scan(self) -> ProvenanceReport:
        """Evaluate every registered source and produce a report."""
        statuses: list[ProvenanceSourceStatus] = []
        finding_counts: dict[str, int] = {}
        compliant = 0
        with_findings = 0

        for source in self.registry.list_all():
            findings = self._evaluate(source)
            is_compliant = not findings
            if is_compliant:
                compliant += 1
            else:
                with_findings += 1
            for finding in findings:
                finding_counts[finding.kind] = (
                    finding_counts.get(finding.kind, 0) + 1
                )
            statuses.append(
                ProvenanceSourceStatus(
                    source_id=source.source_id,
                    trust=source.trust,
                    pii_risk=source.pii_risk,
                    has_provenance=source.provenance is not None,
                    has_license=source.license is not None,
                    retention_days=source.retention_days,
                    findings=findings,
                    compliant=is_compliant,
                )
            )

        return ProvenanceReport(
            generated_at=datetime.now(UTC),
            policy=self.policy,
            statuses=statuses,
            totals=ProvenanceTotals(
                sources_scanned=len(statuses),
                compliant_sources=compliant,
                sources_with_findings=with_findings,
                finding_counts=finding_counts,
            ),
        )

    def _evaluate(self, source: KnowledgeSource) -> list[ProvenanceFinding]:
        findings: list[ProvenanceFinding] = []

        if (
            source.trust in self.policy.require_provenance_for
            and source.provenance is None
        ):
            findings.append(
                ProvenanceFinding(
                    kind="provenance_missing",
                    message=(
                        f"Source '{source.source_id}' (trust={source.trust.value}) "
                        f"has no provenance declared."
                    ),
                )
            )

        if (
            source.trust in self.policy.require_license_for
            and source.license is None
        ):
            findings.append(
                ProvenanceFinding(
                    kind="license_missing",
                    message=(
                        f"Source '{source.source_id}' (trust={source.trust.value}) "
                        f"has no license declared."
                    ),
                )
            )

        if (
            self.policy.require_retention_for_pii
            and source.pii_risk
            and source.retention_days is None
        ):
            findings.append(
                ProvenanceFinding(
                    kind="retention_missing_for_pii",
                    message=(
                        f"Source '{source.source_id}' has pii_risk=True but no "
                        f"retention_days declared."
                    ),
                )
            )

        if (
            self.policy.require_retention_for_all
            and source.retention_days is None
            # Avoid double-reporting when the PII-specific rule already fired.
            and not (self.policy.require_retention_for_pii and source.pii_risk)
        ):
            findings.append(
                ProvenanceFinding(
                    kind="retention_missing",
                    message=(
                        f"Source '{source.source_id}' has no retention_days "
                        f"declared."
                    ),
                )
            )

        return findings


__all__ = [
    "ProvenanceFinding",
    "ProvenanceFindingKind",
    "ProvenancePolicy",
    "ProvenanceReport",
    "ProvenanceScanner",
    "ProvenanceSourceStatus",
    "ProvenanceTotals",
]
