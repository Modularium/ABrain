# §6.1 Sicherheit — standardized AuditExport review

**Branch:** `codex/phase-sec-audit-exports`
**Date:** 2026-04-19
**Scope:** `core/audit/audit_export.py` — single canonical read-only
surface that bundles `TraceStore` and `ApprovalStore` into a versioned
`AuditExport` for forensics / compliance / long-term archive.

---

## 1. Roadmap position

Phases 0–6 are closed on main. §6.3 Observability (`BrainOperationsReport`,
`AgentPerformanceReport`) landed in the previous two turns
(`37fc5c7e`, `bd157ef5`). §6.1 Sicherheit still carried one unchecked
roadmap item:

> §6.1 Sicherheit — **standardisierte Audit-Exports**

This turn closes it with a compositional, read-only exporter — the same
architectural pattern used for the observability surfaces that just landed.

### Idempotency check

Before implementing, I verified:

- `core/audit/exporters/base.py` only defines an abstract
  `BaseTraceExporter` with `NotImplementedError` — no concrete standardized
  export exists;
- `core/audit/__init__.py` has no `AuditExport` / `AuditExporter` symbols;
- no other branch is tracking this scope (`git branch -a` shows only the
  main line through this turn's `codex/phase-sec-audit-exports`);
- `audit_action()` in `core/audit/__init__.py` writes legacy JSONL audit
  entries via `AuditLog` — a different, older surface, not a standardized
  replayable export bundle. Kept untouched; the new exporter does not
  shadow it.

Nothing was double-built.

---

## 2. Design

`AuditExporter` is a thin read-only consumer of the two canonical
audit-bearing stores. It owns no data, no second log, and no write path.

Pipeline:

```
TraceStore.list_recent_traces(trace_limit)
  → per-trace TraceExportEntry (+ optional span_count via get_trace)
  → filter by since / until / workflow_filter
ApprovalStore.snapshot()
  → per-approval ApprovalExportEntry
  → filter by since / until / approval_status_filter
→ AuditExport{ schema_version=1.0.0, generated_at, since, until,
               workflow_filter, approval_status_filter, trace_limit,
               traces[], approvals[] }
```

### Why this shape

- **Frozen `schema_version`.** Consumers (forensics, compliance report
  generators, long-term archive parsers) can pin `"1.0.0"` today and break
  explicitly when the schema rolls. Required by §6.1's "standardisierte"
  — without a versioned schema, "standardized" is just hopeful.
- **Closed `[since, until]` windows.** Both bounds are optional; an open
  side means "no bound on that side." A record whose timestamp equals
  `since` is included (inclusive), mirroring how most compliance windows
  are specified.
- **Span-count opt-out.** `include_span_counts=False` skips per-trace
  `get_trace` calls for bulk archive exports over very large windows —
  keeping the common case (small audit windows) accurate and the bulk
  case cheap.
- **Allow-list / filter behavior.** `workflow_filter` applies only to
  traces (approvals are plan-scoped). `approval_status_filter` applies
  only to approvals (traces have their own status vocabulary). No
  cross-filter coupling, matching how the two stores are actually
  separated.
- **Read-only accessor.** Added `ApprovalStore.snapshot()` (analogous to
  `PerformanceHistoryStore.snapshot()` from the previous turn) so the
  exporter does not touch the store's private `_requests` mapping.

### Why not reuse `core/audit/exporters/base.py`

`BaseTraceExporter.export(TraceSnapshot)` is a per-trace push sink for a
future OTel-like integration — a single-trace streaming contract. An
audit export is a **pull bundle across many traces plus approvals** — a
different shape. Keeping them separate preserves the streaming
contract's purpose without overloading it.

---

## 3. Public API

```python
from core.audit import (
    AUDIT_EXPORT_SCHEMA_VERSION,  # "1.0.0"
    AuditExport,
    AuditExporter,
)
from core.audit.trace_store import TraceStore
from core.approval.store import ApprovalStore
from core.approval.models import ApprovalStatus

exporter = AuditExporter(
    trace_store=trace_store,
    approval_store=approval_store,
)
export = exporter.export(
    since=datetime(2026, 1, 1, tzinfo=UTC),
    until=datetime(2026, 4, 1, tzinfo=UTC),
    workflow_filter="compliance_review_flow",
    approval_status_filter=ApprovalStatus.APPROVED,
    trace_limit=10_000,
)

# export.schema_version == "1.0.0"
# export.traces    -> list[TraceExportEntry]
# export.approvals -> list[ApprovalExportEntry]
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel trace / approval stack | ✅ — both stores are single source of truth |
| No second audit log | ✅ — reads only; does not touch legacy `audit_action()` JSONL |
| No writes to either store | ✅ |
| No business logic outside core | ✅ — pure core module |
| Additive only | ✅ — one new module + one new accessor on `ApprovalStore` + exports + tests + doc |
| No new dependencies | ✅ |

The only change to an existing module beyond exports is the new
`ApprovalStore.snapshot()` accessor — a read-only shallow sort of the
tracked mapping. No existing caller is affected.

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/audit/audit_export.py` | `AuditExport` + `AuditExporter` + entry models + `AUDIT_EXPORT_SCHEMA_VERSION` |
| `core/approval/store.py` | added `snapshot()` accessor |
| `core/audit/__init__.py` | re-exports the 5 new audit-export symbols |
| `tests/audit/__init__.py` | new test package marker |
| `tests/audit/test_audit_export.py` | 15 unit tests |
| `docs/reviews/phase_sec_audit_exports_review.md` | this doc |

---

## 6. Test coverage

15 tests, all green:

- **TestApprovalStoreSnapshot** (1) — snapshot ordering by
  `requested_at`.
- **TestEmptyExport** (2) — empty bundle and schema-version stability.
- **TestTraceExport** (5) — trace surfacing, workflow filter, time
  window, `include_span_counts=False` opt-out, ascending `started_at`
  ordering.
- **TestApprovalExport** (4) — all approvals by default, status filter,
  time window, full field round-trip.
- **TestSchemaHardening** (3) — `extra="forbid"` on all three Pydantic
  models.

### Suites

- Mandatory + `tests/audit`: **1150 passed, 1 skipped**.
- Full (`tests/` with `test_*.py`): **1563 passed, 1 skipped**
  (+15 over the 1548 baseline).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (read-only exporter, one accessor, frozen schema) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical paths reinforced | ✅ |
| No new shadow source-of-truth | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+15 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

§6 Querschnitts-Workstreams status after this turn:

| Item | Status |
|---|---|
| §6.1 Sicherheit – standardisierte Audit-Exports | ✅ this turn |
| §6.3 Observability – Modellvergleiche / Routing / per-agent | ✅ prior turns |
| §6.5 Effizienz – Kosten pro Modellpfad | ✅ prior turn |
| §6.2 Dokumentation – historisch/aktuell/experimentell | ⏳ open |
| §6.4 Daten und Governance (PII / Retention / Provenienz) | ⏳ open, largest remaining stream |

**Recommendation for the next turn:** §6.4 first workstream item —
"Retention- und Löschkonzept." It fits the same read-only /
canonical-store pattern (add a retention window enforcer over
`TraceStore` / `ApprovalStore` / exported JSONL runtime state) and has
the highest data-governance leverage without requiring PII detection
infrastructure.

Phase 7 stays deferred until a real-traffic `promote` verdict from
`BrainOperationsReporter` on actual shadow traces is on record.
