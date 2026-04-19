# §6.5 – Ops cost CLI surface review

**Branch:** `codex/phase_ops_cost_cli`
**Date:** 2026-04-19
**Scope:** `abrain ops cost` CLI subcommand backed by a new
`services.core.get_agent_performance_report` wrapper around
`core.decision.performance_report.AgentPerformanceReporter` reading the
canonical `PerformanceHistoryStore` via `_get_learning_state`.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. The §6.5 Efficiency primitives
`AgentPerformanceReporter` (cost/latency/success) and `EnergyEstimator`
(Green AI) are both on main at the primitive level, but neither had an
operator-facing CLI surface. This turn closes the first of those gaps —
`abrain ops cost` — and introduces the `ops` parent subparser so the
upcoming `ops energy` follow-up drops in additively.

### Why not `abrain governance provenance`

The previous turn's "next step" recommended `governance provenance` to
close the §6.4 operator-surface sweep. On inspection that is blocked at
the moment:

- `ProvenanceScanner` scans a `KnowledgeSourceRegistry`, which on main is
  a pure in-process store — no file-backed persistence, no bootstrap
  loader in `services/core`, no `ABRAIN_*` env-var path.
- Surfacing a `governance provenance` CLI now would always scan an empty
  registry (no sources), producing a misleading "0 findings" view that
  does not reflect real governance posture.
- Introducing a registry persistence layer to power the CLI would add a
  new source of truth and is outside a gap-fill operator-surface scope.

That surface is therefore deferred until a persistent registry loader
exists (separate, scoped roadmap step). `ops cost` is the next highest-
leverage gap that composes **only** canonical already-wired state.

---

## 2. Idempotency check

| Primitive | On main? | Operator surface? |
|---|---|---|
| `RetentionScanner` | ☑ | ☑ — `abrain governance retention` |
| `PiiDetector` + `annotate_retention_candidates` | ☑ | ☑ — `abrain governance pii` |
| `RetentionPruner` | ☑ | ❌ — destructive, out of scope |
| `ProvenanceScanner` | ☑ | ❌ — blocked on registry persistence |
| `AgentPerformanceReporter` | ☑ (commit `94fcb2f8` era) | ❌ — closed by this turn |
| `EnergyEstimator` | ☑ (commit `94fcb2f8`) | ❌ — next turn (`ops energy`) |
| `DatasetSplitter` | ☑ | ❌ — LearningOps consumer |

`AgentPerformanceReporter` is consumed verbatim — no reporting or
aggregation logic is duplicated in either the service wrapper or the
renderer.

---

## 3. Design

### 3.1 `services.core.get_agent_performance_report`

```python
def get_agent_performance_report(
    *,
    sort_key: str = "avg_cost",
    descending: bool = True,
    min_executions: int = 0,
    agent_ids: list[str] | None = None,
) -> Dict[str, Any]: ...
```

- Reuses canonical `_get_learning_state()` — the same warm-loaded
  `PerformanceHistoryStore` the routing engine sees. No second history.
- Wraps the store in `AgentPerformanceReporter` and calls `generate(...)`
  with the supplied filter/sort knobs.
- Returns `report.model_dump(mode="json")` — fully Pydantic-driven, no
  custom dict shaping.

No error-payload path: `PerformanceHistoryStore` is always constructed
(empty or persisted) inside `_get_learning_state`, so the service cannot
hit an "unavailable store" condition. An empty history renders as
`Entries (0):  (none)` at the CLI layer.

### 3.2 `scripts/abrain_control.py`: `ops cost` subcommand

Introduces a new `ops` parent subparser (first §6.5 operator surface).
Flags on the `cost` subaction:

- `--sort-key {avg_cost,avg_latency,success_rate,execution_count,agent_id}`
  — default `avg_cost` (same default as the primitive).
- `--ascending` — flips the reporter's `descending` default.
- `--min-executions N` — clamped `>= 0` (negative values round up to 0).
- `--agents "id-a, id-b,  ,id-c"` — comma list; whitespace and empty
  entries are stripped; default `None` (all agents in the store).
- `--json` — machine-readable mode.

Renderer surfaces:

- header + `generated_at`, sort key, direction,
- totals block (agent count, total executions, recent failures,
  weighted success / latency / cost — 4 decimals),
- entries list (capped at first 20, with overflow tail).

---

## 4. Public surface

```bash
abrain ops cost [--sort-key avg_cost|avg_latency|success_rate|execution_count|agent_id] \
                [--ascending] \
                [--min-executions N] \
                [--agents id-a,id-b,...] \
                [--json]
```

Exit code is always `0`.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| PerformanceHistoryStore is the sole per-agent history truth | ✅ — `_get_learning_state` only |
| TraceStore untouched | ✅ — not read |
| `services/core.py` is the central service wiring | ✅ |
| `scripts/abrain` is the sole CLI | ✅ |
| Read-only — no mutation of store | ✅ — reporter is documented read-only |
| No new dependencies | ✅ |
| `AgentPerformanceReporter` semantics unchanged | ✅ — wrapper only |
| No second policy surface | ✅ — no policy, just filter/sort args |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only on Decision tail (history is a Decision-layer concept) |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 function `get_agent_performance_report` |
| `scripts/abrain_control.py` | +1 subparser (`ops`), +1 subaction (`cost`), +1 handler, +1 renderer |
| `tests/core/test_abrain_cli_ops_cost.py` | new — 9 unit tests |
| `docs/reviews/phase_ops_cost_cli_review.md` | this doc |

---

## 7. Test coverage

9 tests, all green:

- **TestRenderer** (3) — populated totals+entries; empty-entries path
  renders `(none)`; overflow tail shows `... (N more)` for >20 entries.
- **TestCliWiring** (5)
  - delegates to `services.core.get_agent_performance_report` with
    defaults (`sort_key=avg_cost`, `descending=True`,
    `min_executions=0`, `agent_ids=None`);
  - `--sort-key avg_latency --ascending` flips direction and key;
  - `--agents " a , b , ,c"` splits + trims to `["a","b","c"]`;
  - `--min-executions -7` clamps to `0`;
  - `--json` mode emits a JSON-loadable payload.
- **TestServiceIntegration** (1) — without mocks: real
  `PerformanceHistoryStore` is injected via `_get_learning_state`
  monkeypatch, two `record_result()` calls, then
  `get_agent_performance_report` returns a real dumped
  `AgentPerformanceReport` with the expected aggregates.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_ops_cost.py` — **9 passed**.
- Mandatory canonical suite: **1129 passed, 1 skipped** (+9 new).
- Full suite (`tests/` with `test_*.py`): **1715 passed, 1 skipped**
  (+9 new).
- CLI smoke: `python -m scripts.abrain_control ops cost --help`
  renders argparse help cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (additive operator surface, no new logic) | ✅ |
| Idempotency rule honoured (no §6.5 primitive rebuilt) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical CLI / services / store paths reinforced | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+9 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

1. `abrain ops energy` — wrap `EnergyEstimator` over the same
   `PerformanceHistoryStore`. Requires an `EnergyEstimatorConfig`
   input shape; probably expose a minimal `--default-watts` and
   optional `--profiles path/to/json` to keep the surface honest.
2. `abrain governance provenance` — unblocked only once a persistent
   `KnowledgeSourceRegistry` loader exists in `services/core`.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate.
