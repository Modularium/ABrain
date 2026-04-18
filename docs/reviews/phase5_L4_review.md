# Phase 5 – LearningOps L4: Model Artefact Versioning (ModelRegistry)

**Branch:** `codex/phase5-learningops-model-registry`  
**Date:** 2026-04-18  
**Roadmap task closed:** "Modellartefakte versionieren" (Phase 5)

---

## 1. Scope

Track every model artefact produced by `OfflineTrainer` as a versioned,
persistent registry entry.  Enable rollback by activating an earlier entry
and reloading the corresponding model weights.

- `ModelVersionEntry` — immutable Pydantic record: version_id, artifact_path,
  dataset_path, schema_version, training_config_hash, record counts, training
  metrics, registered_at, is_active, notes
- `ModelRegistry` — append-only JSON-persisted store with:
  - `register(result, config, activate=True, notes=None) → ModelVersionEntry`
  - `activate(version_id) → ModelVersionEntry` (rollback)
  - `get_active() → ModelVersionEntry | None`
  - `get_active_model() → NeuralPolicyModel | None`
  - `get_version(version_id) → ModelVersionEntry | None`
  - `list_versions() → list[ModelVersionEntry]` (newest-first)
- `_config_hash(config)` — SHA-256 of hyperparameter-only fields (paths
  excluded) for run-identity fingerprinting

---

## 2. Idempotency check

| Component | Status before L4 |
|-----------|-----------------|
| `model_registry.py` | **Did not exist** |
| Any other versioning/registry for model weights | Not found in codebase |
| `persistence.load_model()` | ✅ on main — **reused by `get_active_model()`** |
| `NeuralPolicyModel` | ✅ on main — **reused** |
| `OfflineTrainingResult` / `TrainingJobConfig` | ✅ on main (L3) — **reused** |

---

## 3. Design decisions

### Exactly one active entry
Calling `register(activate=True)` or `activate(version_id)` atomically flips
`is_active` flags: the target becomes `True`, all others become `False`.  This
invariant is maintained in memory and persisted immediately.

### Hyperparameter-only config hash
`_config_hash` excludes `dataset_path` and `output_artifact_path` so that the
same training setup run against different datasets produces the same hash.
This makes it easy to identify "same config, different data" across runs.

### Append-only entries
Entries are never deleted or modified after registration.  `activate()` only
flips the `is_active` flag via `model_copy(update=...)`, keeping all historical
data intact for audit purposes.

### JSON persistence — no DB
The registry file is a JSON array, one object per entry.  Reloaded on
construction when the file exists.  No locking — this is a single-process
offline tool, not a concurrent service.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel versioning system | ✅ — only one registry API |
| No new store/runtime/orchestrator | ✅ — reads from JSON file, delegates model loading to `persistence.load_model()` |
| No business logic in wrong layer | ✅ — all in `core/decision/learning/` |
| No new shadow truth | ✅ — registry tracks artefacts produced by the canonical `OfflineTrainer` |
| Only additive changes | ✅ — one new file + `__init__.py` extensions |
| No heavy new dependencies | ✅ — stdlib `hashlib`, `json`, `pathlib` only |

---

## 5. Tests

**File:** `tests/decision/test_learningops_model_registry.py`  
**Count:** 31 tests (unit, tmp_path I/O only)

Coverage:
- `_short_id`: length, hex format, uniqueness
- `_config_hash`: SHA-256 format, path-independence, hyperparameter sensitivity
- `ModelVersionEntry`: extra-field rejection, `is_active` default
- `ModelRegistry.register`: entry count, return type, activate flag, second-entry
  deactivation, notes, persistence, config hash, schema version, record counts
- `ModelRegistry.activate`: unknown ID error, flag switch, persistence, return value
- Read API: empty registry, `get_active_model()` (None + loaded), `get_version`,
  `list_versions` order, `__len__`
- Persistence: disk round-trip, valid JSON, parent dir creation, multi-entry

**Full suite:** 791 passed, 1 skipped — all green.

---

## 6. Rollback workflow (as documented)

```python
registry = ModelRegistry("models/registry.json")

# Run 1
result1 = OfflineTrainer(config1).run()
v1 = registry.register(result1, config1)

# Run 2 (now active)
result2 = OfflineTrainer(config2).run()
v2 = registry.register(result2, config2)

# Something goes wrong — roll back to v1
registry.activate(v1.version_id)
model = registry.get_active_model()  # loads v1 weights
```

---

## 7. Gate

| Check | Result |
|-------|--------|
| Scope correct (versioning + rollback only) | ✅ |
| No parallel structure | ✅ |
| Canonical `persistence.load_model()` reused | ✅ |
| No business logic in wrong layer | ✅ |
| No new shadow truth | ✅ |
| Tests green (31/31 new + 791/791 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step after merge

**Phase 5 – L5:** Canary / Shadow evaluation — a `ShadowEvaluator` that runs
the active registry model in *shadow mode* alongside the production heuristic
router, compares routing decisions, and emits structured comparison metrics to
TraceStore.  This closes the Phase 5 roadmap task "Canary-/Shadow-Rollout für
neue Decision-Modelle einführen" without putting the learned model on the
critical production path.
