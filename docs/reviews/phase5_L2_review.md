# Phase 5 – LearningOps L2: DatasetExporter (versioned JSONL)

**Branch:** `codex/phase5-learningops-exporter`  
**Date:** 2026-04-18  
**Roadmap step:** Phase 5, second deliverable — "Datensätze aus Traces, Approvals und Outcomes generieren"

---

## 1. Scope

Persist filtered `LearningRecord` lists to versioned JSONL files for offline
training pipelines.  Provide a round-trip load capability and a directory
listing helper.

- `DatasetExporter` — write JSONL with manifest header, load JSONL back to
  `(ExportManifest, list[LearningRecord])`, list all exports
- `ExportManifest` — typed summary of one exported file (schema_version,
  exported_at, record counts)
- `SCHEMA_VERSION = "1.0"` — hardcoded constant, single source of truth

---

## 2. What already existed (idempotency check)

| Component | Status |
|-----------|--------|
| `core/decision/learning/record.py` | ✅ on main (L1) |
| `core/decision/learning/dataset_builder.py` | ✅ on main (L1) |
| `core/decision/learning/quality.py` | ✅ on main (L1) |
| `core/decision/learning/exporter.py` | **Did not exist** — created here |
| Any JSONL export helper elsewhere | Not found in codebase |

---

## 3. New files

### `core/decision/learning/exporter.py`

**`DatasetExporter(output_dir, schema_version="1.0")`**:

- `export(records, filename=None) -> Path`  
  Writes manifest (line 0) + one record per line.  Auto-generates filename
  `learning_records_{YYYYMMDD_HHMMSS}_v{schema_version}.jsonl`.  Creates
  `output_dir` if missing.

- `load(path) -> (ExportManifest, list[LearningRecord])`  
  Reads JSONL, validates manifest presence on line 0, reconstructs records
  via Pydantic validation.  Raises `ValueError` on empty file or missing
  manifest.

- `list_exports() -> list[Path]`  
  Returns `*.jsonl` files in `output_dir`, newest-first.  Returns `[]` when
  directory does not exist.

**`ExportManifest`**: plain class wrapping the manifest dict with typed
attributes and a useful `__repr__`.

**Manifest format** (line 0 of every JSONL):
```json
{
  "__manifest__": true,
  "schema_version": "1.0",
  "exported_at": "2026-04-18T...",
  "record_count": 42,
  "has_routing_count": 38,
  "has_outcome_count": 30,
  "has_approval_count": 12
}
```

No heavy dependencies — stdlib only (`json`, `pathlib`, `datetime`).

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel implementation | ✅ — no existing JSONL export; purely additive |
| No second store/runtime/orchestrator | ✅ — writes files, does not touch any store |
| No business logic in wrong layer | ✅ — all logic in `core/decision/learning/` |
| No new shadow truth | ✅ — format documents schema_version for traceability |
| Only additive changes | ✅ — one new file, `__init__.py` exports extended |
| No heavy new dependencies | ✅ — stdlib only |
| Offline/online separation maintained | ✅ — exporter is offline-only |

---

## 5. Tests

**File:** `tests/decision/test_learningops_exporter.py`  
**Count:** 20 tests (unit, tmp_path I/O only)

Coverage:
- `export`: dir creation, empty export, path return, line layout, manifest
  counts, schema_version, exported_at ISO format, default filename, custom
  schema version, multi-record line count
- `load`: full round-trip field preservation, manifest return type, empty file
  error, missing manifest error, multi-record round-trip
- `list_exports`: non-existent dir, JSONL discovery, non-JSONL exclusion
- `ExportManifest`: repr, defaults for missing keys

**Full suite:** 728 passed, 1 skipped — all green.

---

## 6. Roadmap task closure

With L1 (DatasetBuilder: generates records from TraceStore + ApprovalStore)
and L2 (DatasetExporter: persists those records to versioned JSONL), the Phase
5 task **"Datensätze aus Traces, Approvals und Outcomes generieren"** is now
fully closed:

```
TraceStore ──┐
             ├──► DatasetBuilder ──► list[LearningRecord] ──► DataQualityFilter ──► DatasetExporter ──► *.jsonl
ApprovalStore─┘
```

---

## 7. Gate

| Check | Result |
|-------|--------|
| Scope correct (L2 exporter only) | ✅ |
| No parallel structure | ✅ |
| Canonical store paths untouched | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green (20/20 new + 728/728 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step after merge

**Phase 5 – L3:** Offline training job definition — a `TrainingJobConfig`
(schema: dataset path, hyperparameters, output artefact path) and a minimal
`OfflineTrainer` that reads a JSONL file produced by L2, converts records to
`TrainingSample` instances via the existing `RewardModel`, and runs a batch
training pass via the existing `NeuralTrainer`.  This wires the full
DatasetBuilder → Exporter → OfflineTrainer pipeline.
