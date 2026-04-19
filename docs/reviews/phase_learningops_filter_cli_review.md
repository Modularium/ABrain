# §6.4 / Phase 5 – LearningOps filter CLI surface review

**Branch:** `codex/phase_learningops_filter_cli`
**Date:** 2026-04-19
**Scope:** `abrain learningops filter` CLI subcommand backed by a new
`services.core.get_dataset_quality_report` wrapper that composes
`core.decision.learning.DatasetBuilder` (over the canonical
`TraceStore` + `ApprovalStore`) with
`core.decision.learning.DataQualityFilter`.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. The previous turn added
`abrain learningops split` under a new `learningops` parent subparser.
`DataQualityFilter` was the next unsurfaced §6.4 / Phase 5 primitive:
it is what an offline training job runs right before `DatasetSplitter`,
so operators had no way to preview which records would be dropped
before starting a training run. This turn closes that gap while
reusing the same `DatasetBuilder` path as `get_dataset_split`.

---

## 2. Idempotency check

| Primitive | On main? | Operator surface? |
|---|---|---|
| `DatasetBuilder` | ☑ | ☑ (composed — no duplication) |
| `DatasetSplitter` | ☑ | ☑ (prior turn — `abrain learningops split`) |
| `DataQualityFilter` | ☑ (long-standing) | ❌ — closed by this turn |
| `ProvenanceScanner` | ☑ | ❌ — still blocked on registry persistence |
| `DatasetExporter` | ☑ | ❌ — writes files, destructive seam deferred |
| `RetentionPruner` | ☑ | ❌ — destructive, out of scope |

`DataQualityFilter`, `QualityViolation`, and `DatasetBuilder` are
consumed verbatim — no validation, aggregation, or record-assembly
logic is duplicated in `services/` or `scripts/`.

---

## 3. Design

### 3.1 `services.core.get_dataset_quality_report`

```python
def get_dataset_quality_report(
    *,
    require_routing_decision: bool = True,
    require_outcome: bool = False,
    require_approval_outcome: bool = False,
    min_quality_score: float = 0.0,
    limit: int = 1000,
    rejected_sample_size: int = 20,
) -> Dict[str, Any]: ...
```

- Reads `TraceStore` + `ApprovalStore` via `_get_trace_state()` /
  `_get_approval_state()`. `trace_store is None` surfaces the
  canonical `trace_store_unavailable` error payload.
- Clamps `min_quality_score` into `[0.0, 1.0]` (the domain of
  `LearningRecord.quality_score()`), clamps `limit` to `>= 1`, and
  clamps `rejected_sample_size` to `>= 0`.
- Builds LearningRecords via `DatasetBuilder(...).build(limit=limit)`,
  then runs `DataQualityFilter(...).filter_with_report(records)`.
- Returns a compact payload:
  - `policy` block (echoed back so operators can confirm the rule
    set),
  - `totals` (total, accepted, rejected, acceptance_rate),
  - `violations_by_field` histogram (field → count),
  - `rejected_sample` (bounded, each entry carries `trace_id`,
    `workflow_name`, `task_type`, `quality_score`, and the full list
    of `QualityViolation`s on that record),
  - `rejected_sample_truncated` flag so operators know when a larger
    `--sample-size` would surface more.

Read-only across both stores by construction: the builder never
mutates and the filter only inspects.

### 3.2 `scripts/abrain_control.py`: `learningops filter` subaction

Added under the `learningops` parent subparser introduced last turn.
Flags:

- `--require-routing-decision` / `--no-require-routing-decision` —
  default on; the `--no-` flip is the escape hatch for operators
  previewing very early stages of trace coverage.
- `--require-outcome` — off by default; flips to require resolved
  `success`.
- `--require-approval-outcome` — off by default; flips to require a
  resolved approval outcome.
- `--min-quality-score FLOAT` — default `0.0`; clamped to `[0.0, 1.0]`
  at handler level.
- `--limit INT` — default `1000`, clamped to `>= 1`.
- `--sample-size INT` — default `20`, clamped to `>= 0`.
- `--json` — machine-readable mode.

Renderer surfaces:

- header + generation timestamp,
- echoed policy block,
- totals block,
- per-field violation histogram (sorted, explicit `(none)` path),
- rejected sample (each record followed by indented violations),
- truncation line when the full rejected set overflows the sample cap.

Error payloads (`trace_store_unavailable`) render as `[WARN] Quality
filter preview unavailable: <error>` with a `detail=` line.

---

## 4. Public surface

```bash
abrain learningops filter [--no-require-routing-decision] \
                          [--require-outcome] \
                          [--require-approval-outcome] \
                          [--min-quality-score 0.0..1.0] \
                          [--limit 1000] \
                          [--sample-size 20] \
                          [--json]
```

Exit code is always `0`; argument errors surface via argparse, store
errors via the renderer.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| TraceStore is the sole trace/audit truth | ✅ — `_get_trace_state` only |
| ApprovalStore is the sole approval truth | ✅ — `_get_approval_state` only |
| PerformanceHistoryStore untouched | ✅ — not read |
| `services/core.py` is the central service wiring | ✅ |
| `scripts/abrain` is the sole CLI | ✅ |
| Read-only — no mutation of stores | ✅ — builder + filter are read-only |
| No new dependencies | ✅ — stdlib only |
| `DataQualityFilter` semantics unchanged | ✅ — wrapper only |
| No parallel record-assembly logic | ✅ — `DatasetBuilder` reused verbatim |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only on Audit tail |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 function `get_dataset_quality_report` |
| `scripts/abrain_control.py` | +1 subaction (`learningops filter`), +1 handler, +1 renderer |
| `tests/core/test_abrain_cli_learningops_filter.py` | new — 10 unit tests |
| `docs/reviews/phase_learningops_filter_cli_review.md` | this doc |

---

## 7. Test coverage

10 tests, all green:

- **TestRenderer** (3) — populated totals+violations+sample with
  truncation line; empty-violations + empty-sample both render
  `(none)` twice; error payload surfaces the
  `trace_store_unavailable` path.
- **TestCliWiring** (4)
  - defaults delegate correctly
    (`require_routing_decision=True`, `require_outcome=False`,
    `min_quality_score=0.0`, `limit=1000`, `rejected_sample_size=20`);
  - `--no-require-routing-decision --require-outcome
    --require-approval-outcome --min-quality-score 0.75` flips all
    flags and forwards the threshold unchanged;
  - `--limit -8 --sample-size -3` clamps to `limit=1` /
    `rejected_sample_size=0`;
  - `--json` mode emits a JSON-loadable payload.
- **TestServiceIntegration** (3) — without mocking the primitive:
  (a) `_get_trace_state` returning `None` surfaces
  `trace_store_unavailable`; (b) an empty store yields zeroed totals
  and the `min_quality_score=5.0` input is clamped to `1.0`; (c) a
  real `TraceStore` with three traces (none carrying an
  explainability record) yields 3 rejected records, a
  `has_routing_decision=3` histogram entry, and the exact `trace_id`
  set in the rejected sample.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_learningops_filter.py` —
  **10 passed**.
- Mandatory canonical suite: **1162 passed, 1 skipped** (+10 new).
- Full suite (`tests/` with `test_*.py`): **1748 passed, 1 skipped**
  (+10 new).
- CLI smoke: `python -m scripts.abrain_control learningops filter
  --help` renders argparse help cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (additive operator surface, no new logic) | ✅ |
| Idempotency rule honoured (no §6.4 primitive rebuilt) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical CLI / services / store paths reinforced | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+10 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

With `learningops split` and `learningops filter` both on main, the
Phase-5 operator sweep is advanced: operators can preview what will
be dropped (`filter`) and how what remains gets partitioned (`split`)
without leaving the CLI. Remaining high-value gap-fill candidates:

1. Bootstrap-Turn für `KnowledgeSourceRegistry`-Persistence
   (`ABRAIN_KNOWLEDGE_SOURCES_PATH` + JSON-Loader in
   `services/core`) — entsperrt anschließend `abrain governance
   provenance` als nächsten §6.4-Surface.
2. `abrain learningops export` — wrap `DatasetExporter` für
   persistierte Splits; bewusst deferred, weil schreibend (Pruner-
   analog) und damit ein eigener, destruktiver Review-Scope.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate.
