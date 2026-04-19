# §6.4 Data Governance — RetentionPruner review

**Branch:** `codex/phase-gov-retention-pruner`
**Date:** 2026-04-19
**Scope:** destructive half of the retention concept —
`RetentionPruner` consumes a `RetentionReport` produced by
`RetentionScanner` and deletes the listed candidate records from
`TraceStore` / `ApprovalStore`. Dry-run is the default.

Closes `§6.4 Retention- und Löschkonzept` end-to-end: the previous
turn (`phase_gov_retention_scanner_review.md`, commit `31f315fb`)
shipped the read-only half; this turn ships the pruner that operates
on the resulting report.

---

## 1. Roadmap position

§6.4 "Retention- und Löschkonzept" was split intentionally last turn:
scanner first, pruner second. Quoting that review:

> "the pruner that consumes this report is a separate future turn."

That turn is this one. With the pruner merged, the §6.4 retention task
is fully covered and the roadmap entry moves from "partial" to closed.

### Idempotency check

Before building:

- `grep -r RetentionPruner|retention_pruner|prune_retention|delete_trace|delete_approval` returned only the prior scanner review and the §6.2 docs audit — no existing implementation;
- `TraceStore` / `ApprovalStore` had no `delete_*` methods yet;
- no parallel branch is tracking this scope;
- the next-step recommendation from the prior two reviews was exactly this pruner.

Nothing was double-built.

---

## 2. Design

### Pruner consumes `RetentionReport` — no policy re-evaluation

The scanner is the single source of truth for "what counts as overdue."
The pruner never looks at `RetentionPolicy` — it iterates
`report.candidates` and calls the store's delete path. This keeps the
two halves composable:

- operators can hold a report, diff it against a previous one, and
  decide when to commit — the pruner does not second-guess them;
- future callers (a CLI, a scheduled job, an API endpoint) all share
  the same `RetentionReport` schema;
- no second retention policy surface can drift apart from the
  scanner's.

### Dry-run is the default

`prune(report)` returns a `RetentionPruneResult` with `dry_run=True`
and an accurate per-candidate outcome list **without touching any
store**. To actually delete, callers must pass `commit=True`. This
matches the operator workflow from the scanner turn: inspect, then
flip the switch.

In dry-run, `deleted=True` on an outcome means "the record is present
and would be deleted." That gives the operator a realistic preview
even if a concurrent process has already cleaned some rows.

### One pass, no retries, no partial-failure recovery

`TraceStore.delete_trace` and `ApprovalStore.delete_request` both
return `bool` (`True` if removed, `False` if already absent). The
pruner does not retry, does not raise on concurrent deletion, and
does not roll back on first failure. Two reasons:

- retention deletions are idempotent in the store layer — `delete_*`
  of an absent record is a no-op;
- partial-success is information: the result's `outcomes` list tells
  the caller exactly which IDs did and did not delete, so operator
  tooling can reconcile.

### No audit-log write inside the pruner

The pruner is a destructive primitive. The caller owns the operator
audit trail (`audit_action` for a CLI, a governance surface for an
API). Adding a second audit writer here would create a parallel audit
stack — which explicitly violates invariant B.5 (no second trace /
approval / audit stack).

### Store delete methods — minimal, destructive, honest

- `TraceStore.delete_trace(trace_id)` removes the trace row plus all
  `spans` and `explainability` rows tied to it. The schema has FKs
  declared but SQLite does not enforce them by default, so the
  deletes are explicit. Returns `True` if the trace row was removed.
- `ApprovalStore.delete_request(approval_id)` pops from the in-memory
  dict and triggers `_auto_save` if persistence is configured.
  Returns `True` if the request was present.

Both return `bool` so the pruner can count concurrent-deletion cases
without raising.

---

## 3. Public API

```python
from core.audit import (
    RetentionPolicy,
    RetentionScanner,
    RetentionPruner,
    RetentionPruneResult,
)

policy = RetentionPolicy(trace_retention_days=90, approval_retention_days=365)
scanner = RetentionScanner(
    trace_store=trace_store,
    approval_store=approval_store,
    policy=policy,
)
report = scanner.scan()

pruner = RetentionPruner(
    trace_store=trace_store,
    approval_store=approval_store,
)

# Step 1 — dry-run (default). Inspect what would happen.
preview: RetentionPruneResult = pruner.prune(report)
assert preview.dry_run is True
for outcome in preview.outcomes:
    print(outcome.kind, outcome.record_id, "->", outcome.deleted)

# Step 2 — commit. Destroys the listed records.
result = pruner.prune(report, commit=True)
assert result.dry_run is False
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel trace / approval stack | ✅ — both stores are single source of truth; destructive API lives there, not in a sidecar |
| No second audit stack | ✅ — pruner writes no audit entries of its own |
| No business logic in CLI / UI / schemas | ✅ — destructive primitive only |
| No hidden reactivation of legacy | ✅ — greenfield addition |
| No second retention surface | ✅ — scanner is the only source for "what counts as overdue" |
| Additive only | ✅ — one new module + two store methods + exports + tests + doc |
| No new dependencies | ✅ |
| Dry-run default | ✅ — destructive mode requires explicit `commit=True` |

The two `delete_*` methods are additive. Existing stores still behave
identically for all non-destructive call sites.

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/audit/retention_pruner.py` | `RetentionPruner`, `RetentionPruneResult`, `RetentionPruneOutcome` |
| `core/audit/trace_store.py` | new `delete_trace` method |
| `core/approval/store.py` | new `delete_request` method |
| `core/audit/__init__.py` | re-exports the 3 new pruner symbols |
| `tests/audit/test_retention_pruner.py` | 11 unit tests |
| `docs/reviews/phase_gov_retention_pruner_review.md` | this doc |

---

## 6. Test coverage

11 tests, all green:

- **TestDryRunDefault** (2) — `prune(report)` is dry-run by default and
  touches nothing; every outcome has `dry_run=True`.
- **TestCommitPath** (3) — `commit=True` deletes trace candidates,
  approval candidates, and cascades spans + explainability rows for
  deleted traces; non-candidate records remain untouched.
- **TestIdempotency** (2) — second commit of the same report is a
  no-op (deleted=False per outcome), and a post-commit re-scan returns
  an empty candidate list.
- **TestEmptyAndCombined** (2) — empty report is a no-op; a combined
  report with multiple traces + an approval commits all deletions
  with correct counts.
- **TestSchemaHardening** (2) — `extra="forbid"` on
  `RetentionPruneResult` and `RetentionPruneOutcome`.

### Suites

- Mandatory + `tests/audit`: **1179 passed, 1 skipped** (+11 over the
  1168 baseline from the prior turn).
- Full (`tests/` with `test_*.py`): **1592 passed, 1 skipped** (+11
  over the 1581 baseline from the prior turn).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (destructive pruner + minimal store deletes) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical stores own destructive path | ✅ |
| No new shadow source-of-truth | ✅ |
| Dry-run is the default | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+11 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

§6.4 Data Governance after this turn:

- [ ] Datenschema für Training und Auswertung — *landed Phase 5 / Phase 6 B1; marked done in ROADMAP_consolidated.md*
- [ ] Provenienz und Lizenzstatus je Datenquelle
- [ ] PII-Strategie
- [x] reproduzierbare Datensplits — *future: Phase 5 data pipeline*
- [x] Retention- und Löschkonzept — **closed this turn** (scanner + pruner)

**Recommendation for the next turn:** §6.4 *"PII-Strategie"* — a policy
+ detection surface that tags retention candidates (and future
training-data records) with PII classifications. Low risk because the
detection is additive, high signal because it composes cleanly with
both the retention scanner and the Phase 5 dataset builder.

Alternative of similar weight: §6.4 *"Provenienz und Lizenzstatus je
Datenquelle"* — a metadata surface on ingestion sources. Slightly
narrower scope than PII since the existing Phase 3 retrieval work
already tracks some provenance; this would formalize it.

Phase 7 stays deferred until a real-traffic `promote` verdict from
`BrainOperationsReporter` is on record.
