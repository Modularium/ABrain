# §6.4 / Phase 5 – LearningOps split CLI surface review

**Branch:** `codex/phase_learningops_split_cli`
**Date:** 2026-04-19
**Scope:** `abrain learningops split` CLI subcommand backed by a new
`services.core.get_dataset_split` wrapper that composes
`core.decision.learning.DatasetBuilder` (over the canonical `TraceStore`
and `ApprovalStore`) with `core.decision.learning.DatasetSplitter`.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. Prior turns surfaced the
§6.5 axes (`abrain ops cost`, `abrain ops energy`). With those closed at
the primitive level, the next unsurfaced §6.4 LearningOps primitive is
`DatasetSplitter` (commit `a89156e4`). This turn adds its operator
surface, giving operators a deterministic, reproducible train/val/test
split over the canonical trace corpus without leaving the CLI.

---

## 2. Idempotency check

| Primitive | On main? | Operator surface? |
|---|---|---|
| `DatasetBuilder` | ☑ | ☑ (composed here — no primitive duplication) |
| `DatasetSplitter` | ☑ (commit `a89156e4`) | ❌ — closed by this turn |
| `ProvenanceScanner` | ☑ | ❌ — still blocked on registry persistence |
| `DataQualityFilter` | ☑ | ❌ — LearningOps filter seam |
| `RetentionPruner` | ☑ | ❌ — destructive, out of scope |

`DatasetSplitConfig`, `DatasetSplitter`, `SplitManifest`, and
`DatasetBuilder` are consumed verbatim — no split, fingerprint, or
record-assembly logic is duplicated in `services/` or `scripts/`.

---

## 3. Design

### 3.1 `services.core.get_dataset_split`

```python
def get_dataset_split(
    *,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
    group_by: str = "trace_id",
    limit: int = 1000,
    include_sample_trace_ids: bool = False,
) -> Dict[str, Any]: ...
```

- Reads the canonical `TraceStore` + `ApprovalStore` via
  `_get_trace_state()` / `_get_approval_state()` — no second store, no
  alternate path. `trace_store is None` surfaces as an `error` payload
  (`trace_store_unavailable`), mirroring `get_retention_scan`.
- Builds `DatasetSplitConfig` inside a try/except so pydantic
  validation errors (ratios not summing to 1, collapsed splits, illegal
  `group_by`) surface as `split_config_invalid` before any store read —
  the splitter's own `ValueError` (duplicate `trace_id`s) surfaces as
  `split_invalid` after build.
- Runs `DatasetBuilder(...).build(limit=limit)` once, then
  `DatasetSplitter(config=config).split(records)`.
- Returns `manifest.model_dump(mode="json")` plus a compact
  `sizes = {train, val, test}` block (split records themselves stay
  inside the process — operators see *counts and fingerprint*, not
  record payloads, keeping the surface read-only-and-light). With
  `include_sample_trace_ids=True` the payload additionally lists the
  first 20 `trace_id`s per bucket for spot-checking.

The service is read-only by construction: `DatasetBuilder` never mutates
either store, and `DatasetSplitter` returns fresh lists.

### 3.2 `scripts/abrain_control.py`: `learningops split` subaction

New `learningops` parent subparser (parallel in spirit to the `ops`
parent added earlier). Flags:

- `--train FLOAT`, `--val FLOAT`, `--test FLOAT` (required) — ratios.
- `--seed INT` (required) — clamped `>= 0` at handler level.
- `--group-by {trace_id, task_type, workflow_name}` — default
  `trace_id`.
- `--limit INT` — clamped `>= 1`, default `1000`.
- `--show-trace-ids` — sample bucket previews (first 20 per bucket).
- `--json` — machine-readable mode.

Renderer surfaces:

- header + generation timestamp, group_by, seed, and ratio triple,
- totals block (total records, total groups, ungrouped fallbacks,
  dataset fingerprint),
- split sizes per bucket,
- optional sample trace_id list per bucket (when requested).

Error payloads (`trace_store_unavailable`, `split_config_invalid`,
`split_invalid`) render as `[WARN] Dataset split unavailable: <error>`
with a `detail=` line.

---

## 4. Public surface

```bash
abrain learningops split --train 0.7 --val 0.15 --test 0.15 --seed 42 \
                         [--group-by trace_id|task_type|workflow_name] \
                         [--limit 1000] \
                         [--show-trace-ids] \
                         [--json]
```

Exit code is always `0`; argument errors surface via argparse, split
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
| Read-only — no mutation of stores | ✅ — builder + splitter are read-only |
| No new dependencies | ✅ — stdlib only |
| `DatasetSplitter` semantics unchanged | ✅ — wrapper only |
| No parallel record-assembly logic | ✅ — `DatasetBuilder` reused verbatim |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only on Audit tail via DatasetBuilder |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 function `get_dataset_split` |
| `scripts/abrain_control.py` | +1 subaction (`learningops split`), +1 handler, +1 renderer, +1 parent subparser |
| `tests/core/test_abrain_cli_learningops_split.py` | new — 11 unit tests |
| `docs/reviews/phase_learningops_split_cli_review.md` | this doc |

---

## 7. Test coverage

11 tests, all green:

- **TestRenderer** (4) — populated manifest + sizes; sample-trace_ids
  block renders per bucket with `(none)` for empty buckets; error
  payload surfaces `trace_store_unavailable` + path; `split_invalid`
  error payload surfaces the `detail` line.
- **TestCliWiring** (4)
  - defaults delegate correctly (group_by=trace_id, limit=1000,
    include_sample_trace_ids=False);
  - `--group-by workflow_name --limit 250 --show-trace-ids` forwarded
    correctly;
  - `--seed -5 --limit -9` clamps to `seed=0` / `limit=1`;
  - `--json` mode emits a JSON-loadable payload.
- **TestServiceIntegration** (3) — without mocking the primitives:
  (a) `_get_trace_state` returning `None` surfaces
  `trace_store_unavailable`; (b) invalid ratios surface
  `split_config_invalid` without touching the store (sentinel
  `list_recent_traces` raises if called); (c) real `TraceStore` with 20
  synthetic traces yields a split whose `dataset_fingerprint` and bucket
  `sizes` are byte-identical across two consecutive calls — the
  determinism invariant that makes the surface useful.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_learningops_split.py` —
  **11 passed**.
- Mandatory canonical suite: **1152 passed, 1 skipped** (+11 new).
- Full suite (`tests/` with `test_*.py`): **1738 passed, 1 skipped**
  (+11 new).
- CLI smoke: `python -m scripts.abrain_control learningops split --help`
  renders argparse help cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (additive operator surface, no new logic) | ✅ |
| Idempotency rule honoured (no §6.4 primitive rebuilt) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical CLI / services / store paths reinforced | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+11 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

With `abrain ops cost`, `abrain ops energy`, and `abrain learningops
split` on main, the §6.4/§6.5 operator sweep is advanced by a third
primitive surface. Remaining high-value gap-fill candidates:

1. `abrain learningops filter` — wrap `DataQualityFilter` so operators
   can preview which `LearningRecord`s the quality policy would drop
   before exporting.
2. `abrain governance provenance` — still blocked on a persistent
   `KnowledgeSourceRegistry` loader in `services/core`; a separate
   bootstrap turn would land `ABRAIN_KNOWLEDGE_SOURCES_PATH` + JSON
   loader, then the CLI drops on top.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate.
