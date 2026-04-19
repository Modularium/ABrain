# §6.5 Efficiency / §6.3 Observability — AgentPerformanceReport review

**Branch:** `codex/phase-obs-agent-performance-report`
**Date:** 2026-04-19
**Scope:** `core/decision/performance_report.py` — read-only per-agent
cost / latency / success-rate reporter over the canonical
`PerformanceHistoryStore`.

---

## 1. Roadmap position

Phases 0–6 are closed on main. §6.3 Observability just landed its Brain
surface (`BrainOperationsReport`, commit `37fc5c7e`). Roadmap §6.5 still
carries an unchecked item:

> §6.5 Effizienz und Green AI — **Kosten pro Task und pro Modellpfad reporten**

and §6.3 asks for per-agent success/cost/latency metrics. This turn closes
the "per-Modellpfad kosten/latency reporten" part of §6.5 with the same
compositional read-only pattern used for the Brain report — no new
production path, no second truth.

---

## 2. Design

`AgentPerformanceReporter` is a thin read-only consumer of
`PerformanceHistoryStore` (the canonical per-agent metric truth on this
repo). It owns no write path, no history of its own, and no trace access.

Pipeline:

```
PerformanceHistoryStore.snapshot()
  → per-agent AgentPerformanceEntry
  → optional min_executions / agent_ids filters
  → sort by (avg_cost | avg_latency | success_rate | execution_count | agent_id)
  → execution_count-weighted AgentPerformanceTotals
  → AgentPerformanceReport
```

### Why this shape

- **Read-only.** Uses a new `PerformanceHistoryStore.snapshot()` accessor
  instead of touching `_history` directly — the store keeps ownership of
  its mapping. This is the only change to the existing store.
- **No second truth.** The report is a projection; every number in it
  comes from one `AgentPerformanceHistory` field.
- **Execution-weighted aggregates.** A raw mean across agents is
  misleading when execution counts differ by 5×. Weighting by
  `execution_count` makes `totals.weighted_avg_cost` mean "what ABrain
  currently pays per execution" instead of "what an imaginary
  round-robin would pay."
- **Sort defaults operator-relevant.** `avg_cost` descending — the
  most-likely first question an operator asks under a cost spike.

### Allow-list semantics

When a caller passes `agent_ids=[...]`, missing agents are surfaced with
the store's default values (via `store.get(...)`, `execution_count=0`).
This is deliberate: it lets operators ask "report on these specific
deployed agents" and see gaps in the history explicitly, instead of them
silently dropping out.

---

## 3. Public API

```python
from core.decision import (
    AgentPerformanceReport,
    AgentPerformanceReporter,
    PerformanceHistoryStore,
)

reporter = AgentPerformanceReporter(store=store)
report = reporter.generate(
    sort_key="avg_cost",   # default
    descending=True,       # default
    min_executions=10,     # optional filter
    agent_ids=None,        # optional allow-list
)

# report.entries    -> list[AgentPerformanceEntry]
# report.totals     -> AgentPerformanceTotals (weighted by execution_count)
# report.sort_key / descending / min_executions / generated_at
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel Policy/Router/Orchestrator/History stack | ✅ |
| No second performance store | ✅ — reporter reads only |
| No business logic in CLI/UI/OpenAPI | ✅ — pure core module |
| No writes to existing stores | ✅ |
| Additive only | ✅ — one new module + one new store method (`snapshot`) + exports + tests + doc |
| No new dependencies | ✅ |

The added `PerformanceHistoryStore.snapshot()` is strictly a read-only
accessor that returns a shallow copy of the internal mapping; no existing
caller is affected.

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/decision/performance_report.py` | `AgentPerformanceReport` + `Reporter` + entry/totals models |
| `core/decision/performance_history.py` | added `snapshot()` public accessor |
| `core/decision/__init__.py` | exports the 4 new symbols |
| `tests/decision/test_performance_report.py` | 14 unit tests |
| `docs/reviews/phase_obs_agent_performance_report_review.md` | this doc |

---

## 6. Test coverage

14 tests, all green:

- **TestStoreSnapshot** (1) — `snapshot()` returns an independent copy
  (mutating it does not leak back into the store).
- **TestReportBasics** (3) — empty store; all-agents-by-default;
  entry-field round-trip.
- **TestSorting** (4) — default `avg_cost desc`, latency asc,
  success_rate desc, agent_id asc.
- **TestFilters** (2) — `min_executions`; `agent_ids` allow-list with
  defaulted missing agent.
- **TestTotals** (2) — execution-weighted aggregates match hand
  calculation; zero-execution totals are zero, not NaN.
- **TestSchema** (2) — `extra="forbid"` on both entry and report models.

### Suites

- Mandatory: **1135 passed, 1 skipped**.
- Full (`tests/` with `test_*.py`): **1548 passed, 1 skipped**
  (+14 over the 1534 baseline).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (read-only reporter, one new store accessor) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical paths reinforced | ✅ |
| No new shadow source-of-truth | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+14 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

With §6.5 "Kosten pro Modellpfad reporten" closed, remaining §6
Querschnitts items:

- **§6.4 Data Governance** — Provenienz/Lizenz, PII-Strategie, Retention
  and reproduzierbare Datensplits are all still unchecked and
  substantial.
- **§6.2 Dokumentation** — historisch-vs-aktuell-Trennung and
  Experimentkennzeichnung could close with a docs audit.
- **§6.1 Sicherheit** — items largely closed by Phase S21, but
  "standardisierte Audit-Exports" remains.

Phase 7 stays deferred until real-traffic `promote` verdict from
`BrainOperationsReporter` is on record.

**Recommendation:** §6.1 "standardisierte Audit-Exports" next — a small,
additive surface over `TraceStore`/`ApprovalStore` with clear canonical
path, analogous to this report. Then §6.4 in a larger stream.
