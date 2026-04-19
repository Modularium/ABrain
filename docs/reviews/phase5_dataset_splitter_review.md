# Phase 5 / §6.4 — DatasetSplitter review

**Branch:** `codex/phase5-dataset-splitter`
**Date:** 2026-04-19
**Scope:** deterministic, reproducible train/val/test splitter on top
of the existing Phase 5 `LearningRecord` / `DatasetBuilder` surface.
Read-only, stdlib + pydantic, no new dependencies.

Closes the §6.4 *"reproduzierbare Datensplits"* line item — the last
non-Phase-7 §6 Data-Governance task. With this merged, §6.4 is fully
covered apart from the deferred Phase 7 items.

---

## 1. Roadmap position

`docs/ROADMAP_consolidated.md` §6.4 before this turn:

- [x] Datenschema für Training und Auswertung
- [x] Provenienz und Lizenzstatus je Datenquelle
- [x] PII-Strategie
- [x] Retention- und Löschkonzept
- [ ] **reproduzierbare Datensplits** ← this turn

The prior turn's recommendation was verbatim:

> "Phase 5's *'reproduzierbare Datensplits'* item — a deterministic
> split surface on top of the existing Phase 5 dataset pipeline.
> Composes cleanly with the PII detector (splits must not re-mix
> PII-bearing and clean records) and the provenance scanner (splits
> must preserve per-source attribution)."

That is exactly this turn.

### Idempotency check

Before building:

- `grep -rln 'reproducible_split\|deterministic_split\|DatasetSplit\|SplitManifest\|DatasetSplitter'`
  returned no matches — no existing implementation;
- `core/decision/learning/` already ships `DatasetBuilder`,
  `LearningRecord`, `DataQualityFilter`, `DatasetExporter`,
  `OfflineTrainer`, `ModelRegistry`, `ShadowEvaluator` — the splitter
  is the missing link between builder output and training;
- no parallel branch tracks this scope;
- the Phase 5 `TrainingDataset.get_batch` method returns deterministic
  tail batches but does not produce reproducible train/val/test
  partitions — orthogonal concern, untouched.

---

## 2. Design

### Hash-bucketing, not tail-slicing

Assignment is a pure function of `(seed, group_key)`:

```
h = blake2b(f"{seed}:{group_key}") / 2**64
if h < train_ratio:       → train
elif h < train+val:       → val
else:                     → test
```

This gives three properties that index-based splitting does not:

1. **Growth-stable.** A record's bucket label depends only on its
   group key and the seed. Adding or removing records never
   reshuffles existing assignments — the test suite asserts this
   both ways (base → base+new and full → full::2).
2. **Order-independent.** Two callers with the same records in
   different orders produce set-equal buckets.
3. **Cross-run / cross-process deterministic.** BLAKE2b sidesteps
   Python's per-process `hash()` randomisation, so splits are
   reproducible regardless of `PYTHONHASHSEED`.

### Grouping prevents key leakage

`group_by` accepts `trace_id` (default — each record is its own
group), `task_type`, or `workflow_name`. All records sharing a group
key land in the same bucket. This is the property that composes with
the PII detector and provenance scanner:

- **PII composition.** If the caller filters PII-bearing records out
  of the input list before splitting (the expected contract — the
  splitter is not the filter), identical records across buckets is
  impossible because each trace_id appears once. If the caller opts
  for `group_by="workflow_name"`, an entire workflow stays together,
  so a PII-flagged workflow can be excluded wholesale.
- **Per-source attribution.** Grouping by `workflow_name` keeps a
  source's samples together, preserving attribution — train/test
  contamination across a workflow is structurally prevented.

Records with a `None` group-by field fall back to `trace_id` and are
counted in `manifest.ungrouped_records`. Visible, not silent.

### Manifest carries a fingerprint, not the records

`SplitManifest` persists the exact config plus sizes and a
`dataset_fingerprint` — a BLAKE2b digest over the sorted
`trace_id` set. Two manifests with matching config and fingerprint
came from the same dataset, regardless of input ordering. This is the
minimal-sufficient information to reconstruct a split: the record
list lives in the existing `DatasetExporter` / `DatasetBuilder`
surfaces; the manifest just anchors identity.

### Duplicate trace_ids are rejected

`split()` raises `ValueError` if `trace_id`s are not unique. The
fingerprint's identity guarantee and the group_by semantics both rely
on trace_id uniqueness; silently deduping would hide an upstream bug
in `DatasetBuilder` callers.

### Read-only

The splitter never mutates input records. Test
`test_records_are_not_mutated` pins this: `model_dump()` before and
after are byte-equal.

### No new dependencies

`hashlib.blake2b` and pydantic only — same dependency footprint as
the rest of `core/decision/learning/`.

---

## 3. Public API

```python
from core.decision.learning import (
    DatasetBuilder,
    DatasetSplitConfig,
    DatasetSplitter,
    DatasetSplit,
    SplitManifest,
)

records = DatasetBuilder(
    trace_store=trace_store,
    approval_store=approval_store,
).build(limit=5000)

config = DatasetSplitConfig(
    train_ratio=0.7,
    val_ratio=0.15,
    test_ratio=0.15,
    seed=42,
    group_by="workflow_name",  # prevent workflow leakage
)

splitter = DatasetSplitter(config=config)
split, manifest = splitter.split(records)

assert manifest.total_records == len(records)
# Persist the manifest alongside exports for reproducibility.
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel dataset pipeline | ✅ — consumes `LearningRecord` from the existing `DatasetBuilder` |
| No second audit stack | ✅ — splitter writes no audit entries |
| No business logic in CLI / UI / schemas | ✅ — pure data-layer primitive |
| No hidden reactivation of legacy | ✅ — greenfield addition; `TrainingDataset.get_batch` untouched |
| No second source-of-truth for training data | ✅ — splitter is an operator over records, not a store |
| Read-only input | ✅ — records never mutated |
| Deterministic + growth-stable | ✅ — BLAKE2b hash-bucketing on (seed, group_key) |
| Additive only | ✅ — one new module + re-exports + tests + doc |
| No new dependencies | ✅ — stdlib `hashlib` + pydantic |

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/decision/learning/splitter.py` | `DatasetSplitConfig`, `DatasetSplit`, `SplitManifest`, `DatasetSplitter`, `GroupBy` |
| `core/decision/learning/__init__.py` | lazy re-exports for the 4 new public symbols |
| `tests/decision/test_learningops_splitter.py` | 24 unit tests |
| `docs/reviews/phase5_dataset_splitter_review.md` | this doc |

---

## 6. Test coverage

24 tests, all green:

- **TestConfig** (6) — ratios must sum to 1.0; all-train / all-val-test-zero
  rejected; train/val-only and train/test-only splits allowed; `extra="forbid"`;
  seed must be non-negative.
- **TestDeterminism** (3) — same seed + same records → byte-identical
  bucket order; different seed → different split; input order does not
  affect set-membership.
- **TestGrowthStability** (2) — base+new does not reassign existing
  records; full→subset survivors keep their bucket.
- **TestGrouping** (3) — `workflow_name` grouping keeps every workflow
  in a single bucket; `task_type=None` falls back to trace_id and is
  counted in `manifest.ungrouped_records`; default group_by is
  `trace_id`.
- **TestRatioApproximation** (1) — 10 000-record split lands within
  ±1 % of the configured ratios.
- **TestManifest** (4) — counts match the split; fingerprint is
  order-independent; fingerprint changes when the dataset changes;
  `total_groups` reflects the chosen grouping.
- **TestEdgeCases** (3) — empty input yields empty split and a zero-count
  manifest; duplicate `trace_id`s raise; input records are not mutated.
- **TestSchemaHardening** (2) — `extra="forbid"` on `DatasetSplit`
  and `SplitManifest`.

### Suites

- Mandatory + `tests/audit` + `tests/retrieval`: **1499 passed,
  1 skipped** (+24 over the prior scoped baseline of 1475).
- Full (`tests/` with `test_*.py`): **1658 passed, 1 skipped** (+24
  over the 1634 baseline from the prior turn).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (deterministic splitter + manifest) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical Phase 5 surface used (LearningRecord) | ✅ |
| No new shadow source-of-truth | ✅ |
| Reproducibility properties asserted in tests | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+24 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

§6.4 Data Governance is closed apart from Phase 7 items.

**Recommendation for the next turn:** §6.5 *"Energieverbrauch pro
Modellpfad messen"* — an energy-estimation surface over
`PerformanceHistoryStore`. Composition: per-model wattage constants
multiplied by observed latency/token volumes from history. Smaller
scope than this turn but bridges Phase 6 observability with §6.5
Green-AI which is the last open §6 bucket with any actionable items.

Alternative of comparable weight: §7 *"Architekturdiagramme für
Kernpfad, Plugin-Pfad, LearningOps"* under §6.2 — a doc-only turn
that uses the same inventory pattern as the prior `phase_doc_audit_*`
turn. Pure documentation; very low risk.

Phase 7 stays deferred until a real-traffic `promote` verdict from
`BrainOperationsReporter` is on record.
