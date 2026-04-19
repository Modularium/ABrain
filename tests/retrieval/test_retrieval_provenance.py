"""§6.4 Data Governance — ProvenanceScanner tests."""

from __future__ import annotations

import pytest

from core.retrieval import (
    KnowledgeSource,
    KnowledgeSourceRegistry,
    ProvenanceFinding,
    ProvenancePolicy,
    ProvenanceReport,
    ProvenanceScanner,
    ProvenanceSourceStatus,
    ProvenanceTotals,
    SourceTrust,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source(
    source_id: str,
    *,
    trust: SourceTrust = SourceTrust.TRUSTED,
    provenance: str | None = None,
    license: str | None = None,
    pii_risk: bool = False,
    retention_days: int | None = None,
) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=source_id,
        display_name=source_id.replace("-", " ").title(),
        trust=trust,
        source_type="document",
        provenance=provenance,
        license=license,
        pii_risk=pii_risk,
        retention_days=retention_days,
    )


def _registry(*sources: KnowledgeSource) -> KnowledgeSourceRegistry:
    registry = KnowledgeSourceRegistry()
    for source in sources:
        registry.register(source)
    return registry


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


class TestPolicy:
    def test_default_policy_matches_registry_registration_checks(self):
        policy = ProvenancePolicy()
        assert set(policy.require_provenance_for) == {
            SourceTrust.EXTERNAL,
            SourceTrust.UNTRUSTED,
        }
        assert set(policy.require_license_for) == {
            SourceTrust.EXTERNAL,
            SourceTrust.UNTRUSTED,
        }
        assert policy.require_retention_for_pii is True
        assert policy.require_retention_for_all is False

    def test_trust_lists_are_deduped(self):
        policy = ProvenancePolicy(
            require_provenance_for=[
                SourceTrust.EXTERNAL,
                SourceTrust.EXTERNAL,
                SourceTrust.INTERNAL,
            ],
            require_license_for=[SourceTrust.UNTRUSTED, SourceTrust.UNTRUSTED],
        )
        assert policy.require_provenance_for == [
            SourceTrust.EXTERNAL,
            SourceTrust.INTERNAL,
        ]
        assert policy.require_license_for == [SourceTrust.UNTRUSTED]

    def test_policy_extra_forbid(self):
        with pytest.raises(ValueError):
            ProvenancePolicy(rogue="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Clean registry — all compliant
# ---------------------------------------------------------------------------


class TestCleanRegistry:
    def test_fully_declared_sources_are_compliant(self):
        registry = _registry(
            _source("internal", trust=SourceTrust.INTERNAL),
            _source(
                "ext-api",
                trust=SourceTrust.EXTERNAL,
                provenance="https://example.com",
                license="MIT",
            ),
            _source(
                "pii-ok",
                trust=SourceTrust.TRUSTED,
                pii_risk=True,
                retention_days=30,
            ),
        )
        report = ProvenanceScanner(registry=registry).scan()

        assert isinstance(report, ProvenanceReport)
        assert report.totals.sources_scanned == 3
        assert report.totals.compliant_sources == 3
        assert report.totals.sources_with_findings == 0
        assert report.totals.finding_counts == {}
        assert all(status.compliant for status in report.statuses)

    def test_empty_registry_scans_to_empty_report(self):
        scanner = ProvenanceScanner(registry=KnowledgeSourceRegistry())
        report = scanner.scan()
        assert report.totals.sources_scanned == 0
        assert report.statuses == []
        assert report.totals.finding_counts == {}


# ---------------------------------------------------------------------------
# Individual finding kinds
# ---------------------------------------------------------------------------


class TestFindingKinds:
    def test_license_missing_for_external_source(self):
        # Registry requires provenance for EXTERNAL, not license — so we can
        # register an EXTERNAL source without a license.
        registry = _registry(
            _source(
                "vendor-api",
                trust=SourceTrust.EXTERNAL,
                provenance="https://vendor.example",
            ),
        )
        report = ProvenanceScanner(registry=registry).scan()
        status = report.statuses[0]
        assert not status.compliant
        kinds = [f.kind for f in status.findings]
        assert kinds == ["license_missing"]
        assert report.totals.finding_counts == {"license_missing": 1}

    def test_retention_missing_for_pii(self):
        registry = _registry(
            _source(
                "user-chat",
                trust=SourceTrust.INTERNAL,
                pii_risk=True,
            ),
        )
        report = ProvenanceScanner(registry=registry).scan()
        assert [f.kind for f in report.statuses[0].findings] == [
            "retention_missing_for_pii"
        ]

    def test_provenance_missing_fires_when_policy_requires_for_internal(self):
        # Registry accepts INTERNAL sources without provenance. A tightened
        # policy that requires provenance for INTERNAL catches them post-hoc.
        registry = _registry(_source("notes", trust=SourceTrust.INTERNAL))
        policy = ProvenancePolicy(
            require_provenance_for=[
                SourceTrust.EXTERNAL,
                SourceTrust.UNTRUSTED,
                SourceTrust.INTERNAL,
            ],
        )
        report = ProvenanceScanner(registry=registry, policy=policy).scan()
        assert [f.kind for f in report.statuses[0].findings] == [
            "provenance_missing"
        ]

    def test_require_retention_for_all_catches_non_pii_source(self):
        registry = _registry(_source("docs", trust=SourceTrust.INTERNAL))
        policy = ProvenancePolicy(require_retention_for_all=True)
        report = ProvenanceScanner(registry=registry, policy=policy).scan()
        assert [f.kind for f in report.statuses[0].findings] == [
            "retention_missing"
        ]

    def test_require_retention_for_all_does_not_double_report_pii_sources(self):
        registry = _registry(
            _source("user-chat", trust=SourceTrust.INTERNAL, pii_risk=True),
        )
        policy = ProvenancePolicy(require_retention_for_all=True)
        report = ProvenanceScanner(registry=registry, policy=policy).scan()
        # PII rule takes precedence — no "retention_missing" on top of it.
        kinds = [f.kind for f in report.statuses[0].findings]
        assert kinds == ["retention_missing_for_pii"]


# ---------------------------------------------------------------------------
# Multiple findings per source, report-level aggregation
# ---------------------------------------------------------------------------


class TestAggregation:
    def test_source_can_accumulate_multiple_findings(self):
        # EXTERNAL with provenance (required by registry) but no license,
        # flagged as PII but missing retention → 2 findings.
        registry = _registry(
            _source(
                "ext-pii",
                trust=SourceTrust.EXTERNAL,
                provenance="https://vendor.example",
                pii_risk=True,
            ),
        )
        report = ProvenanceScanner(registry=registry).scan()
        kinds = sorted(f.kind for f in report.statuses[0].findings)
        assert kinds == ["license_missing", "retention_missing_for_pii"]
        assert not report.statuses[0].compliant

    def test_report_totals_aggregate_across_sources(self):
        registry = _registry(
            _source(
                "ext-1",
                trust=SourceTrust.EXTERNAL,
                provenance="https://a.example",
            ),
            _source(
                "ext-2",
                trust=SourceTrust.EXTERNAL,
                provenance="https://b.example",
                license="Apache-2.0",
            ),
            _source(
                "pii-unbounded",
                trust=SourceTrust.INTERNAL,
                pii_risk=True,
            ),
        )
        report = ProvenanceScanner(registry=registry).scan()

        assert report.totals.sources_scanned == 3
        assert report.totals.compliant_sources == 1
        assert report.totals.sources_with_findings == 2
        assert report.totals.finding_counts == {
            "license_missing": 1,
            "retention_missing_for_pii": 1,
        }

    def test_statuses_include_every_registered_source_even_when_clean(self):
        registry = _registry(
            _source("clean", trust=SourceTrust.TRUSTED),
            _source(
                "dirty", trust=SourceTrust.EXTERNAL, provenance="https://x.io"
            ),
        )
        report = ProvenanceScanner(registry=registry).scan()
        assert {s.source_id for s in report.statuses} == {"clean", "dirty"}


# ---------------------------------------------------------------------------
# Read-only behaviour
# ---------------------------------------------------------------------------


class TestReadOnly:
    def test_scan_does_not_mutate_registry(self):
        registry = _registry(
            _source(
                "ext",
                trust=SourceTrust.EXTERNAL,
                provenance="https://e.example",
            ),
        )
        before = [s.model_copy() for s in registry.list_all()]
        scanner = ProvenanceScanner(registry=registry)
        scanner.scan()
        scanner.scan()
        after = registry.list_all()
        assert len(after) == len(before)
        for b, a in zip(before, after):
            assert b == a

    def test_scan_is_deterministic_for_stable_registry(self):
        registry = _registry(
            _source(
                "ext",
                trust=SourceTrust.EXTERNAL,
                provenance="https://e.example",
            ),
        )
        scanner = ProvenanceScanner(registry=registry)
        first = scanner.scan()
        second = scanner.scan()
        # generated_at differs; the analytical payload does not.
        assert first.statuses == second.statuses
        assert first.totals == second.totals


# ---------------------------------------------------------------------------
# Schema hardening
# ---------------------------------------------------------------------------


class TestSchemaHardening:
    def test_finding_extra_forbid(self):
        with pytest.raises(ValueError):
            ProvenanceFinding(
                kind="license_missing",
                message="x",
                rogue="nope",  # type: ignore[call-arg]
            )

    def test_source_status_extra_forbid(self):
        with pytest.raises(ValueError):
            ProvenanceSourceStatus(
                source_id="x",
                trust=SourceTrust.TRUSTED,
                pii_risk=False,
                has_provenance=True,
                has_license=True,
                retention_days=None,
                findings=[],
                compliant=True,
                rogue="nope",  # type: ignore[call-arg]
            )

    def test_totals_extra_forbid(self):
        with pytest.raises(ValueError):
            ProvenanceTotals(
                sources_scanned=0,
                compliant_sources=0,
                sources_with_findings=0,
                rogue="x",  # type: ignore[call-arg]
            )

    def test_report_extra_forbid(self):
        with pytest.raises(ValueError):
            ProvenanceReport(
                generated_at="2026-04-19T00:00:00+00:00",  # type: ignore[arg-type]
                policy=ProvenancePolicy(),
                statuses=[],
                totals=ProvenanceTotals(
                    sources_scanned=0,
                    compliant_sources=0,
                    sources_with_findings=0,
                ),
                rogue="x",  # type: ignore[call-arg]
            )
