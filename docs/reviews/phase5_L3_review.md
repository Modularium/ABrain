# Phase 5 – LearningOps L3: Offline Training Job Definition

**Branch:** `codex/phase5-learningops-offline-trainer`  
**Date:** 2026-04-18  
**Roadmap steps closed:**
- "Offline-Trainingsjobs definieren" (Phase 5 task 4)
- Completes the end-to-end offline pipeline from TraceStore to model artefact

---

## 1. Scope

Wire the full offline training pipeline by adding:

- `TrainingJobConfig` — declarative Pydantic config (dataset path,
  hyperparameters, quality filter settings, output artifact path)
- `OfflineTrainer` — executes one training run end-to-end
- `OfflineTrainingResult` — structured result with counts, metrics, paths
- `_record_to_sample()` — deterministic `LearningRecord → TrainingSample`
  conversion with a fixed 6-dim feature schema

---

## 2. Idempotency check

| Component | Status before L3 |
|-----------|-----------------|
| `offline_trainer.py` | **Did not exist** |
| `TrainingJobConfig` | **Did not exist** |
| `OfflineTrainer` | **Did not exist** |
| `NeuralTrainer` (trainer.py) | ✅ on main — **reused, not duplicated** |
| `RewardModel` (reward_model.py) | ✅ on main — **reused** |
| `TrainingSample` / `TrainingDataset` | ✅ on main — **reused** |
| `DatasetExporter.load()` | ✅ on main (L2) — **reused** |
| `DataQualityFilter` | ✅ on main (L1) — **reused** |
| `persistence.save_model()` | ✅ on main — **reused** |

No existing component was modified.

---

## 3. Full offline pipeline (closed by L1 + L2 + L3)

```
TraceStore ──┐
             ├──► DatasetBuilder ──► DataQualityFilter ──► DatasetExporter ──► *.jsonl
ApprovalStore─┘
                                                              │
                                           TrainingJobConfig ─┤
                                                              ▼
                                                      OfflineTrainer
                                                       │         │
                                                       ▼         ▼
                                               NeuralTrainer  save_model()
                                                       │         │
                                                       ▼         ▼
                                             TrainingMetrics  model.json (artefact)
```

---

## 4. Design decisions

### Fixed offline feature schema (`_OFFLINE_FEATURE_NAMES`)

The 6-dimensional feature vector is stable across runs:
```
["success", "cost_norm", "latency_norm", "routing_confidence", "score_gap", "capability_match"]
```

This differs from the online `FeatureEncoder` schema intentionally: the
offline pipeline does not have live `AgentDescriptor` objects to compute
per-capability features.  Starting fresh always avoids weight-mismatch errors.

### Always fresh model

`OfflineTrainer.run()` always creates a new `NeuralPolicyModel`.  Continuing
from an existing checkpoint (fine-tuning) is out of scope for L3 and requires
the model versioning work planned for L4.

### Neutral defaults for absent signals

When `success`, `cost_usd`, `latency_ms`, `routing_confidence` or `score_gap`
are `None`, neutral values (0.5/0.0/1.0) are used rather than skipping the
record.  Callers that want high-signal-only training should set
`require_outcome=True` in `TrainingJobConfig`.

---

## 5. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel implementation | ✅ — reuses NeuralTrainer, RewardModel, DatasetExporter |
| No second runtime/orchestrator/policy stack | ✅ |
| No business logic in wrong layer | ✅ — all in `core/decision/learning/` |
| No new shadow truth | ✅ — offline trainer reads exported files, writes to explicit artifact path |
| Only additive changes | ✅ — one new file + `__init__.py` export extension |
| No heavy new dependencies | ✅ — stdlib + existing Pydantic models only |

---

## 6. Tests

**File:** `tests/decision/test_learningops_offline_trainer.py`  
**Count:** 32 tests (unit, tmp_path I/O only)

Coverage:
- `TrainingJobConfig`: defaults, extra-field rejection, batch_size/learning_rate bounds, custom hyperparams
- `_record_to_sample`: feature_names schema, vector length, success mapping (True/False/None), cost/latency normalisation, missing value defaults, agent_id propagation, routing_confidence/score_gap/capability_match, reward bounds, empty task_embedding
- `OfflineTrainer.run()`: result type, record counts, quality filter rejection, artifact creation, parent dir creation, empty dataset, samples_converted == accepted, manifest metadata, training metrics validity, epochs executed, artifact_path matches config

**Full suite:** 760 passed, 1 skipped — all green.

---

## 7. Gate

| Check | Result |
|-------|--------|
| Scope correct (offline training job only) | ✅ |
| No parallel structure | ✅ |
| Canonical store and learning components reused | ✅ |
| No business logic in wrong layer | ✅ |
| Tests green (32/32 new + 760/760 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step after merge

**Phase 5 – L4:** Model artefact versioning — a `ModelRegistry` that tracks
exported model artefacts with version, schema_version, training job config
hash, and training metrics.  Enables rollback by selecting an earlier
versioned entry and reloading via `persistence.load_model()`.
