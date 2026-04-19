# §6.4 Data Governance — RetentionScanner review

**Branch:** `codex/phase-gov-retention-scanner`
**Date:** 2026-04-19
**Scope:** `core/audit/retention.py` — single canonical read-only surface
that reports overdue deletion candidates in `TraceStore` and
`ApprovalStore` based on a frozen `RetentionPolicy`. No deletion happens
in this turn.

---

## 1. Roadmap position

Phase 0–6 closed on main. §6.1, §6.3, §6.5 all landed in prior turns
(`319c42a8`, `37fc5c7e`, `bd157ef5`). §6.4 Data Governance is the
largest remaining Querschnitts-Workstream and explicitly lists:

> §6.4 Daten und Governance — **Retention- und Löschkonzept**

`docs/architecture/PERSISTENT_STATE_AND_DURABLE_RUNTIME.md` already
flagged this in the Phase N review:

> *"Phase N does not introduce TTL or archival. The SQLite file grows
> until manual pruning. Phase O scope."*

This turn delivers the **read-only half** of that deferred work — a
policy surface + candidate scanner — without any destructive step. The
pruner that consumes this report is a separate future turn.

### Idempotency check

Before building:

- `grep -i retention` across `core/`, `services/`, `tests/` returned no
  implementation, only doc mentions;
- no `RetentionPolicy`, `RetentionScanner`, or equivalent symbol exists
  anywhere on main;
- no parallel branch is tracking this scope;
- the roadmap item is still unchecked in `docs/ROADMAP_consolidated.md`
  line 417.

Nothing was double-built.

---

## 2. Design

### Two-step pattern: policy + scanner, no destructive action yet

Retention has two natural halves:

1. **What counts as overdue?** → `RetentionPolicy` (frozen Pydantic model)
   + `RetentionScanner.scan()` → `RetentionReport`
2. **What to do with candidates?** → a future `RetentionPruner` that
   consumes the report and calls destructive ops on the stores.

This turn delivers **only** the first half. That separation is
deliberate:

- the policy surface becomes reviewable on its own, independent of any
  destructive action — operators can dry-run a window, see what would
  be deleted, and adjust before anything is wired to act on it;
- the `TraceStore` / `ApprovalStore` destructive APIs don't exist yet;
  implementing them in the same turn would bundle a policy decision
  with an irreversible state change;
- the canonical downstream consumer is well-defined — a pruner reads
  this exact `RetentionReport` shape and calls `DELETE` paths. Keeping
  the report as the single interface prevents future divergence.

### Scanner shape

```
TraceStore.list_recent_traces(trace_limit)
  → for each trace:
      skip if keep_open_traces and ended_at is None
      age = now - (ended_at or started_at)
      if age > trace_retention_days → RetentionCandidate(kind="trace", …)

ApprovalStore.snapshot()
  → for each approval:
      skip if keep_pending_approvals and status == PENDING
      age = now - requested_at
      if age > approval_retention_days → RetentionCandidate(kind="approval", …)

→ RetentionReport { policy, evaluation_time, candidates[], totals }
```

### Boundary rule

`age > window_days` (strict) — a record exactly at the boundary is
**not** a candidate. This matches operator intent ("keep for 30 days"
means "day 30 is still in window") and avoids rounding-induced
flapping.

### Protections (default-on)

- `keep_open_traces=True` — traces without `ended_at` (running /
  paused) are never flagged. Running work is not overdue just because
  its span is long.
- `keep_pending_approvals=True` — `ApprovalStatus.PENDING` approvals
  are never flagged. Dropping a pending approval would lose the
  audit trail of a never-decided action.

Both are opt-out via policy flags — operators with explicit archival
rules can override.

### Deterministic tests via injected `evaluation_time`

`scan(evaluation_time=...)` accepts an injected "now" so tests don't
race against wall-clock. Also enables what-if evaluation ("how many
records would be candidates in 30 days?" without waiting).

---

## 3. Public API

```python
from core.audit import (
    RetentionPolicy,
    RetentionReport,
    RetentionScanner,
)

policy = RetentionPolicy(
    trace_retention_days=90,
    approval_retention_days=365,
    # keep_open_traces=True,            # default
    # keep_pending_approvals=True,      # default
)
scanner = RetentionScanner(
    trace_store=trace_store,
    approval_store=approval_store,
    policy=policy,
)
report: RetentionReport = scanner.scan()

# report.candidates  -> list[RetentionCandidate]
# report.totals      -> RetentionTotals (traces_scanned, approvals_scanned,
#                                        trace_candidates, approval_candidates)
# report.policy      -> the input policy (round-tripped for archive)
# report.evaluation_time -> the reference "now" that was applied
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel trace / approval stack | ✅ — both stores are single source of truth |
| No destructive action | ✅ — scanner is strictly read-only |
| No writes to either store | ✅ |
| No business logic outside core | ✅ — pure core module |
| No hidden reactivation of legacy | ✅ — greenfield addition |
| Additive only | ✅ — one new module + exports + tests + doc |
| No new dependencies | ✅ |

The `evaluation_time` injection is not a write — it is a parameter to a
pure function.

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/audit/retention.py` | `RetentionPolicy`, `Candidate`, `Totals`, `Report`, `Scanner` |
| `core/audit/__init__.py` | re-exports the 5 new retention symbols |
| `tests/audit/test_retention.py` | 18 unit tests |
| `docs/reviews/phase_gov_retention_scanner_review.md` | this doc |

---

## 6. Test coverage

18 tests, all green:

- **TestRetentionPolicy** (3) — `>= 1 day` window validation, default
  `keep_open_traces` / `keep_pending_approvals`, `extra="forbid"`.
- **TestEmptyScan** (1) — empty stores yield a well-formed empty report
  with the policy echoed.
- **TestTraceRetention** (5) — fresh trace skipped; expired flagged
  with age / retention / reason populated; boundary (age ==
  retention_days) is not a candidate; open trace protected by default;
  open trace surfaced when policy disables the protection.
- **TestApprovalRetention** (4) — fresh skipped; expired flagged;
  pending protected by default; pending surfaced when flag disabled.
- **TestCombined** (1) — both kinds reported in the same pass with
  correct totals split.
- **TestSchemaHardening** (2) — `extra="forbid"` on `RetentionCandidate`
  and `RetentionReport`.
- **TestEvaluationTime** (1) — injecting a future `evaluation_time`
  promotes a borderline record to candidate, proving determinism.
- **TestDecisionRecordedApproval** (1) — approval that was `PENDING`
  and then decided (via `record_decision`) ages out correctly — covers
  the realistic lifecycle path.

### Suites

- Mandatory + `tests/audit`: **1168 passed, 1 skipped**.
- Full (`tests/` with `test_*.py`): **1581 passed, 1 skipped**
  (+18 over the 1563 baseline).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (read-only scanner, frozen policy) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical paths reinforced | ✅ |
| No new shadow source-of-truth | ✅ |
| No destructive action wired | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+18 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

§6.4 Data Governance items still open after this turn:

- [ ] Datenschema für Training und Auswertung
- [ ] Provenienz und Lizenzstatus je Datenquelle
- [ ] PII-Strategie
- [ ] reproduzierbare Datensplits
- [x] Retention- und Löschkonzept — *read-only half this turn; pruner is a future turn*

§6.2 Dokumentation is also still largely open:

- [ ] klare Trennung: historisch / aktuell / experimentell
- [ ] Architekturdiagramme
- [ ] Dokumentation pro kanonischem Pfad
- [ ] Experimente explizit markieren
- [ ] veraltete Implementierungsbehauptungen entfernen

**Recommendation for the next turn:** §6.2 *"klare Trennung: historisch
/ aktuell / experimentell"* — a docs-only audit that inventories every
non-frozen Markdown file under `docs/` and tags each as historical,
current, or experimental with a pointer to the canonical replacement
when applicable. Low risk, high signal, complements this turn's
retention policy (both are §6-level governance hygiene).

Phase 7 stays deferred until a real-traffic `promote` verdict from
`BrainOperationsReporter` is on record.
