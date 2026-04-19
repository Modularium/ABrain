# §6.4 Data Governance — ProvenanceScanner review

**Branch:** `codex/phase-gov-provenance-scanner`
**Date:** 2026-04-19
**Scope:** read-only governance scanner over
`KnowledgeSourceRegistry` — produces a typed `ProvenanceReport` of
per-source provenance / license / retention compliance findings,
analogous in shape to `RetentionReport`.

Closes the §6.4 *"Provenienz und Lizenzstatus je Datenquelle"* line
item. The registry already validated these facts at **registration
time**; this scanner makes them **auditable post-hoc** under an
operator-controlled policy that can be tightened without re-registering
sources.

---

## 1. Roadmap position

`docs/ROADMAP_consolidated.md` §6.4 before this turn:

- [x] Datenschema für Training und Auswertung
- [ ] **Provenienz und Lizenzstatus je Datenquelle** ← this turn
- [x] PII-Strategie
- [x] Retention- und Löschkonzept (Scanner + Pruner)
- [ ] reproduzierbare Datensplits

The prior turn's recommendation was verbatim:

> "Recommendation for the next turn: §6.4 *'Provenienz und Lizenzstatus
> je Datenquelle'* — a metadata surface on ingestion sources that
> formalises the partial provenance tracking already in `core/retrieval`
> (the existing `DataSource` descriptor in `core/retrieval/models.py`
> carries `license`, `pii_risk`, `retention_days`; this would elevate
> it to a reviewable governance report, analogous to what the retention
> scanner does for deletion candidates)."

That is exactly this turn.

### Idempotency check

Before building:

- `grep -rn 'ProvenanceReport\|ProvenanceScanner\|ProvenancePolicy'`
  returned no matches — no existing implementation anywhere;
- `core/retrieval/registry.py` enforces provenance/license/retention
  checks only at `register()` time and only for the hardcoded EXTERNAL
  / UNTRUSTED / PII axes;
- no parallel branch tracks this scope;
- the next-step recommendation from the prior turn was exactly this.

The registry's registration-time checks stay untouched — the scanner
does not re-implement them. It produces a *current-state* report
over all registered sources under an operator-defined policy, which
is the piece that did not exist.

---

## 2. Design

### Scanner is read-only and stateless

`ProvenanceScanner(registry=..., policy=...).scan()` iterates
`registry.list_all()` once, applies the frozen `ProvenancePolicy` per
source, and returns a fully-typed `ProvenanceReport`. Two consecutive
scans on an unchanged registry yield identical analytical payload
(only `generated_at` differs), which the test suite asserts.

### Policy is orthogonal to registry registration rules

The registry rejects EXTERNAL/UNTRUSTED sources without provenance at
`register()` time (hard error) and emits advisory warnings for PII
sources without retention and EXTERNAL/UNTRUSTED sources without
license. Those checks still fire — this turn does not change them.

The scanner adds a second, *operator-tunable* layer on top:

- `require_provenance_for` / `require_license_for`: trust levels where
  missing metadata becomes a finding. Defaults match the registry's
  registration set; an operator can tighten to include TRUSTED or
  INTERNAL.
- `require_retention_for_pii`: flag PII sources without retention.
- `require_retention_for_all`: flag *every* source without retention
  (disabled by default).

This keeps registration strict-by-default but lets the governance
report evolve independently — analogous to how `RetentionPolicy` is
orthogonal to trace/approval creation.

### Typed findings with a closed kind set

`ProvenanceFindingKind` is a `Literal` of four values:
`provenance_missing`, `license_missing`, `retention_missing_for_pii`,
`retention_missing`. Downstream tooling can switch on kind without
parsing the free-text message. The set is small and conservative; new
kinds should be added here rather than extended via free-form strings.

### No double-reporting

When a source triggers `retention_missing_for_pii`, the
`retention_missing` rule is suppressed for that source even if
`require_retention_for_all=True`. A PII-bearing source getting two
findings about the same missing field would be noise, not signal. The
test suite pins this behaviour.

### No audit-log write from the scanner

Same contract as the retention scanner / pruner and the PII detector:
the scanner is a pure primitive. The caller (a governance surface, a
CLI, a scheduled job) owns the operator audit trail. Adding a second
audit writer here would create a parallel audit stack.

### Location: `core/retrieval/`, not `core/audit/`

The scanner is about *source metadata*, not *audit records*, so it
lives next to `registry.py` and `models.py`. `core/audit/` remains the
home of retention / PII / export primitives that operate on trace +
approval stores. Keeping the governance helpers adjacent to the data
they describe avoids creating a "governance kitchen sink" module.

---

## 3. Public API

```python
from core.retrieval import (
    KnowledgeSourceRegistry,
    ProvenancePolicy,
    ProvenanceScanner,
    ProvenanceReport,
    SourceTrust,
)

registry = KnowledgeSourceRegistry()
# ... registry.register(...) calls, same as today ...

# Default policy mirrors registry registration checks.
scanner = ProvenanceScanner(registry=registry)
report: ProvenanceReport = scanner.scan()

for status in report.statuses:
    if not status.compliant:
        for finding in status.findings:
            print(status.source_id, finding.kind, "—", finding.message)

# Tightened policy — require license and provenance for ALL trust levels.
tight = ProvenancePolicy(
    require_provenance_for=list(SourceTrust),
    require_license_for=list(SourceTrust),
    require_retention_for_all=True,
)
tight_report = ProvenanceScanner(registry=registry, policy=tight).scan()
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel retrieval registry | ✅ — `KnowledgeSourceRegistry` remains the single source of truth; scanner reads only |
| No second audit stack | ✅ — scanner writes no audit entries |
| No business logic in CLI / UI / schemas | ✅ — pure evaluation primitive |
| No hidden reactivation of legacy | ✅ — greenfield addition; registry `_validate_governance` / `_advisory_warnings` untouched |
| No second governance source-of-truth | ✅ — registration-time checks still authoritative; scanner produces a report, not a second registry |
| No overlap with `RetentionPolicy` | ✅ — this policy evaluates source-metadata presence, not record age |
| Additive only | ✅ — one new module + re-exports + tests + doc |
| No new dependencies | ✅ — stdlib + pydantic only |

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/retrieval/provenance.py` | `ProvenancePolicy`, `ProvenanceFinding`, `ProvenanceFindingKind`, `ProvenanceSourceStatus`, `ProvenanceTotals`, `ProvenanceReport`, `ProvenanceScanner` |
| `core/retrieval/__init__.py` | re-exports the 7 new symbols |
| `tests/retrieval/test_retrieval_provenance.py` | 19 unit tests |
| `docs/reviews/phase_gov_provenance_scanner_review.md` | this doc |

---

## 6. Test coverage

19 tests, all green:

- **TestPolicy** (3) — default policy matches registry's registration
  set; trust lists are deduped; `extra="forbid"` on `ProvenancePolicy`.
- **TestCleanRegistry** (2) — a registry with fully-declared sources
  reports 0 findings; an empty registry yields an empty report.
- **TestFindingKinds** (5) — each of the four finding kinds fires for
  the right shape of source; `retention_missing` does not double-report
  when the PII rule already fired.
- **TestAggregation** (3) — a single source can accumulate multiple
  findings; report totals aggregate across sources; every registered
  source produces a status entry regardless of compliance.
- **TestReadOnly** (2) — scanning does not mutate the registry; two
  consecutive scans produce identical analytical payloads.
- **TestSchemaHardening** (4) — `extra="forbid"` enforced on
  `ProvenanceFinding`, `ProvenanceSourceStatus`, `ProvenanceTotals`,
  `ProvenanceReport`.

### Suites

- Mandatory + `tests/audit` + `tests/retrieval`: **1475 passed,
  1 skipped** (+19 over the prior scoped baseline).
- Full (`tests/` with `test_*.py`): **1634 passed, 1 skipped** (+19
  over the 1615 baseline from the prior turn).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (policy + read-only scanner over registry) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical registry read-only | ✅ |
| No new shadow source-of-truth | ✅ |
| Registration-time governance untouched | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+19 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

§6.4 Data Governance after this turn:

- [x] Datenschema für Training und Auswertung
- [x] **Provenienz und Lizenzstatus je Datenquelle** — closed this turn
- [x] PII-Strategie
- [x] Retention- und Löschkonzept
- [ ] reproduzierbare Datensplits — deferred to Phase 5 data pipeline

§6.4 is effectively closed apart from the Phase 5 dataset-splits item
which belongs with the dataset builder.

**Recommendation for the next turn:** Phase 5's *"reproduzierbare
Datensplits"* item — a deterministic split surface on top of the
existing Phase 5 dataset pipeline. Composes cleanly with the PII
detector (splits must not re-mix PII-bearing and clean records) and
the provenance scanner (splits must preserve per-source attribution).

Alternative of similar weight: §6.5 *"Energieverbrauch pro Modellpfad
messen"* — energy-estimation surface over `PerformanceHistoryStore`.
Smaller in scope, but depends on credible wattage estimates per model
tier, which may not be available without external data.

Phase 7 stays deferred until a real-traffic `promote` verdict from
`BrainOperationsReporter` is on record.
