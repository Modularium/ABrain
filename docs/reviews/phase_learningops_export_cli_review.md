# Phase 5 / §6.4 – `abrain learningops export` CLI surface review

**Branch:** `codex/phase_learningops_export_cli`
**Date:** 2026-04-19
**Scope:** Expose `core.decision.learning.DatasetExporter` as the
operator CLI surface `abrain learningops export` — the first
**destructive-write** LearningOps CLI. Composes
`DatasetBuilder` + `DataQualityFilter` + `DatasetExporter` behind
a single service entry with a dry-run-default / `--apply`-to-persist
flag pattern.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. Roadmap §6.4 already has
`splitter` and `filter` surfaced; the L2 exporter primitive has been
on main since `phase5_L2_review` but was never wired into the CLI.
This turn closes the remaining LearningOps gap so operators can move
from *inspecting* datasets (split/filter) to *persisting* a
reproducible JSONL artefact for offline training. Logical successor
of the `governance sources` turn, called out in its §10 as candidate.

Destructive scope — handled explicitly: default is dry-run,
`--apply` is required to write.

---

## 2. Idempotency check

| Primitive | On main? | Surfaced? |
|---|---|---|
| `DatasetBuilder` | ☑ | ☑ (via `learningops split`, `learningops filter`) |
| `DataQualityFilter` | ☑ | ☑ (via `learningops filter`) |
| `DatasetExporter` | ☑ (L2 review `phase5_L2_review.md`) | ❌ before this turn |
| `services.core.export_learning_dataset` | ❌ | added this turn |
| `abrain learningops export` subcommand | ❌ | added this turn |
| `ABRAIN_LEARNING_EXPORTS_DIR` env var | ❌ | added this turn |

Idempotent checks before implementation:

- `grep` for `learningops export` / `export_learning_dataset` over
  `scripts/` + `services/` — no pre-existing surface.
- No parallel exporter implemented: the service delegates to the
  existing `DatasetExporter.export()` verbatim.
- No parallel builder or filter: both are the canonical
  `DatasetBuilder` + `DataQualityFilter` already used by
  `get_dataset_quality_report`.
- No parallel env-var convention invented: `ABRAIN_LEARNING_EXPORTS_DIR`
  follows the existing `ABRAIN_<DOMAIN>_<KIND>` pattern
  (`ABRAIN_TRACE_DB_PATH`, `ABRAIN_APPROVAL_STORE_PATH`,
  `ABRAIN_KNOWLEDGE_SOURCES_PATH`, …).

---

## 3. Design

### 3.1 `services.core.export_learning_dataset`

Single entry that composes builder + filter + exporter, mirroring the
sibling `get_dataset_quality_report`:

- Inputs: the same four filter flags (`require_routing_decision`,
  `require_outcome`, `require_approval_outcome`, `min_quality_score`),
  `limit`, and three write-side inputs: `output_dir`, `filename`,
  `apply`.
- Flow:
  1. `_get_trace_state()` — if the TraceStore is absent, short-circuit
     with `error="trace_store_unavailable"` (same shape as the filter
     service).
  2. `DatasetBuilder(...).build(limit=limit)` — canonical builder over
     `TraceStore` + `ApprovalStore`.
  3. `DataQualityFilter(...).filter_with_report(records)` —
     canonical filter; rejected items feed a `violations_by_field`
     histogram but are **never persisted**.
  4. Resolve `output_dir` via explicit arg → env var
     `ABRAIN_LEARNING_EXPORTS_DIR` → default `runtime/learning_exports`.
  5. If `apply=False` (default): return a dry-run payload describing
     what *would* be written. **No directory is created, no file is
     touched.**
  6. If `apply=True`: `DatasetExporter(output_dir).export(accepted,
     filename=filename)` writes the versioned JSONL file and the
     service returns the written path + record count.

### 3.2 Dry-run vs apply contract

| Behaviour | dry-run (default) | `--apply` |
|---|---|---|
| TraceStore / ApprovalStore read | ✅ | ✅ |
| DatasetBuilder / DataQualityFilter | ✅ | ✅ |
| Output directory created | ❌ | ✅ (via `DatasetExporter.export`) |
| JSONL file written | ❌ | ✅ |
| Existing files modified | ❌ (never) | ❌ (never — exporter always writes a new filename) |
| Return payload includes `written=True` | ❌ | ✅ |
| Return payload includes `written_path` | ❌ | ✅ |
| Return payload includes `planned_filename` | ✅ | — |

Rejected records are **never** included in the exported JSONL — only
`accepted` records are passed to `DatasetExporter.export(...)`. The
filter policy is therefore a hard gate, not a label.

### 3.3 CLI shape

```
abrain learningops export
    [--require-routing-decision | --no-require-routing-decision]
    [--require-outcome] [--require-approval-outcome]
    [--min-quality-score FLOAT]
    [--limit N]
    [--output-dir PATH] [--filename NAME]
    [--apply]
    [--json]
```

Sits next to `split` and `filter` on the existing `learningops`
parent.

Handler clamps `--limit` via `max(1, args.limit)` (same convention as
`filter`/`split`). Filter flags mirror `learningops filter` verbatim
so operators can preview with `filter`, then `export --apply` with the
same policy.

### 3.4 Renderer

Two modes driven by the `apply` + `written` flags in the payload:

- `=== LearningOps Dataset Export (DRY-RUN) ===` with
  `Planned filename: <auto>` and a trailing `dry-run (no file written;
  re-run with --apply to persist)` notice.
- `=== LearningOps Dataset Export (APPLIED) ===` with
  `Written path`, `Written filename`, and `Record count written`.

Error payload: `[WARN] Dataset export unavailable: <error>` +
`detail=<trace_store_path>`.

---

## 4. Public surface

```bash
# Dry-run: see what would be written (default, safe)
abrain learningops export --min-quality-score 0.5

# Persist to the default directory
abrain learningops export --min-quality-score 0.5 --apply

# Persist to a pinned directory + filename (e.g. for CI artefacts)
abrain learningops export \
    --output-dir artefacts/train/$(date -u +%F) \
    --filename pinned_$(date -u +%FT%H%M%SZ).jsonl \
    --apply --json

# Override the env default without the --output-dir flag
ABRAIN_LEARNING_EXPORTS_DIR=/data/abrain/exports abrain learningops export --apply
```

Dry-run text output (abridged):

```
=== LearningOps Dataset Export (DRY-RUN) ===
...
Totals:
  Total records:         10
  Accepted:              7
  Rejected:              3

Violations by field (1):
  - has_routing_decision: 3

Output:
  Directory:             runtime/learning_exports
  Planned filename:      <auto>
  Status:                dry-run (no file written; re-run with --apply to persist)
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| TraceStore sole trace/audit truth | ✅ — reads only |
| ApprovalStore sole approval truth | ✅ — reads only |
| `DatasetBuilder` / `DataQualityFilter` / `DatasetExporter` unchanged | ✅ — no new fields, no new governance/filter checks |
| `services/core.py` central service wiring | ✅ |
| `scripts/abrain` sole CLI | ✅ — surface added on existing `learningops` parent |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — CLI sits on the LearningOps seam over Audit |
| No business logic in CLI | ✅ — handler is pass-through, renderer is pure formatting |
| Destructive ops default to read-only / dry-run | ✅ — `--apply` is required to write |
| Existing files never modified | ✅ — `DatasetExporter` always writes a new filename |
| No new heavy dependencies | ✅ — stdlib only (json/pathlib/datetime already in exporter) |
| No new runtime / no new stores | ✅ |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 service `export_learning_dataset` |
| `scripts/abrain_control.py` | +1 handler, +1 renderer, +1 subparser (`learningops export`) |
| `tests/core/test_abrain_cli_learningops_export.py` | new — 12 unit + integration tests |
| `docs/reviews/phase_learningops_export_cli_review.md` | this doc |

---

## 7. Test coverage

12 tests, all green:

- **TestRenderer** (3)
  - dry-run summary: totals, policy, violations, output block with
    `Planned filename`, dry-run notice;
  - applied summary: `APPLIED` header, written path/filename/count,
    `(none)` for empty violations;
  - error payload: `[WARN] Dataset export unavailable: ...` with
    trace-store path.
- **TestCliWiring** (4)
  - defaults delegation: `apply=False`, all policy defaults forwarded;
  - `--apply`, `--output-dir`, `--filename`, policy-flag flips and
    clamps all forwarded correctly;
  - negative `--limit` clamped to 1;
  - `--json` emits a JSON-dumpable payload.
- **TestServiceIntegration** (5)
  - missing TraceStore → `trace_store_unavailable`;
  - dry-run over a real TraceStore creates neither the output
    directory nor any file;
  - `apply=True` writes a JSONL with a valid manifest line and the
    expected record count;
  - `ABRAIN_LEARNING_EXPORTS_DIR` env var is the default output dir
    when `--output-dir` is not passed, and dry-run does not create it;
  - filter policy rejecting every record still writes a manifest-only
    JSONL (record_count=0) — rejected records are not leaked into the
    artefact.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_learningops_export.py` —
  **12 passed** (1.38s).
- Mandatory canonical suite: **1204 passed, 1 skipped** (+12 new).
- Full suite (`tests/` with `test_*.py`): **1790 passed, 1 skipped**
  (+12 new).
- `py_compile services/core.py scripts/abrain_control.py` — clean.
- CLI smoke: `python -m scripts.abrain_control learningops export --help`
  renders cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (destructive op behind dry-run default + `--apply`) | ✅ |
| Idempotency rule honoured (no duplicate exporter/builder/filter) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical service path reinforced (same `_get_trace_state()` + builder + filter chain) | ✅ |
| Canonical CLI path reinforced (same `learningops <verb>` shape) | ✅ |
| Destructive write guarded | ✅ — `--apply` required, existing files never modified |
| Mandatory suite green | ✅ |
| Full suite green (+12 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

LearningOps §6.4 CLI gap is now fully closed: `split`, `filter`,
`export`. Natural next turns:

1. `abrain governance retention --apply` — surface the destructive
   `RetentionPruner` behind the same dry-run / `--apply` pattern as
   this turn. All prior governance reviews explicitly punted the
   pruner as "destructive, out of scope"; this turn establishes the
   destructive-CLI pattern (dry-run + `--apply`), so a Pruner-apply
   turn can cleanly follow.
2. Roadmap §6.5 residual — *Quantisierung/Distillation für lokale
   Spezialmodelle evaluieren* (research-shaped, not a small
   operator-surface win; would need its own inventory).
3. Phase 7 remains blocked on a real-traffic `promote` verdict via
   `abrain brain status`. No change in this turn.
