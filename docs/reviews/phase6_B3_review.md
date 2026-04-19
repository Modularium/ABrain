# Phase 6 – Brain v1 B6-S3: Brain Offline Trainer

**Branch:** `codex/phase6-brain-v1-offline-trainer`  
**Date:** 2026-04-19  
**Roadmap task:** "Shadow-Mode für Brain-v1 einführen" — closes the training pipeline from BrainRecord to a model artefact loadable by ModelRegistry + ShadowEvaluator

---

## 1. Scope

Load a JSONL dataset of `BrainRecord` objects, convert them to `TrainingSample`
instances using a fixed 13-dim Brain feature schema, run a training pass with
the existing `NeuralTrainer`/`NeuralPolicyModel`/`MLPScoringModel` stack, and
save the resulting weights to disk.  The artefact is directly compatible with
`ModelRegistry.register()` and `ShadowEvaluator`.

New file: `core/decision/brain/trainer.py`  
Updated: `core/decision/brain/__init__.py`

---

## 2. Idempotency check

| Component | Status before B6-S3 |
|-----------|-------------------|
| `trainer.py` in `brain/` | **Did not exist** |
| `BrainRecord`, `BrainState`, `BrainTarget` | ✅ on main (B6-S1) — **read-only input** |
| `NeuralPolicyModel`, `NeuralTrainer`, `MLPScoringModel` | ✅ on main — **reused unmodified** |
| `RewardModel` | ✅ on main — **reused unmodified** |
| `ModelRegistry`, `ShadowEvaluator` | ✅ on main (P5-L4/L5) — **downstream consumers** |

---

## 3. Design

### Brain feature schema (13-dim, fixed)

The schema is stable across runs — saved MLP weights are only loadable when
the feature count and order match.

| Index | Feature name | Source | Default when absent |
|-------|-------------|--------|-------------------|
| 0 | `routing_confidence` | `BrainState` | 0.0 |
| 1 | `score_gap` | `BrainState` | 0.0 |
| 2 | `num_candidates_norm` | `num_candidates / 10`, clamped | — |
| 3 | `has_policy_effect` | `BrainState.policy` | 0.0 |
| 4 | `approval_required` | `BrainState.policy` | 0.0 |
| 5 | `cap_match_score` | top-1 candidate | 0.0 |
| 6 | `success_rate` | top-1 candidate | 0.5 |
| 7 | `avg_latency_norm` | top-1 `avg_latency_s / latency_scale_s`, clamped | 1.0 |
| 8 | `avg_cost_norm` | top-1 `avg_cost_usd / cost_scale_usd`, clamped | 0.0 |
| 9 | `recent_failures_norm` | top-1 `recent_failures / 5`, clamped | 0.0 |
| 10 | `load_factor` | top-1 candidate | 0.0 |
| 11 | `trust_level_ord` | top-1 candidate | 0.0 |
| 12 | `availability_ord` | top-1 candidate | 0.5 |

The "top-1 candidate" is `state.candidates[0]` — the selected agent, always
placed first by `BrainRecordBuilder`.  Neutral defaults apply when the
candidate list is empty.

### Reward derivation

`RewardModel.compute_reward(success, latency_s, cost_usd, failure_count=0)`
using `BrainTarget` fields:

| Target field | Neutral default |
|-------------|----------------|
| `outcome_success` | 0.5 (absent = neutral) |
| `outcome_latency_ms / 1000` | `latency_scale_s` (1 scale unit) |
| `outcome_cost_usd` | 0.0 |

### JSONL persistence

`save_brain_records(records, path)` / `load_brain_records(path)` — one
`BrainRecord` JSON object per line, no manifest.  Simple and sufficient for
Brain training files; a richer format can be layered on later.

### Training flow

```
load_brain_records(brain_records_path)
  → [filter: require_outcome]
  → _brain_record_to_sample() × N
  → TrainingDataset
  → NeuralTrainer(batch_size, lr, epochs, min_samples).train(dataset, NeuralPolicyModel())
  → save_model(output_artifact_path)
```

Always starts with a **fresh** `NeuralPolicyModel` — no warm-starting.  The
artefact is directly passable to `ModelRegistry.register(result, config)` via
an `OfflineTrainingResult`-compatible wrapper (the `artifact_path` string field
is sufficient for `ModelRegistry` lookup).

### `require_outcome` guard

When `True`, skips `BrainRecord`s whose `target.outcome_success is None`.
Default `False` — neutral-success records still contribute a weak gradient,
which is acceptable for exploratory runs.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel production router | ✅ — training is fully offline |
| No second TraceStore / PerformanceHistoryStore | ✅ — no runtime store dependency |
| No modification of production NeuralPolicyModel | ✅ — fresh model per run |
| No business logic in wrong layer | ✅ — all in `core/decision/brain/` |
| No new heavy dependencies | ✅ — stdlib + existing canonical components |
| Additive only | ✅ — one new file + `__init__.py` extension |

---

## 5. Tests

**File:** `tests/decision/test_brain_offline_trainer.py`  
**Count:** 34 tests (unit + one end-to-end, `tmp_path` I/O)

| Test class | Tests | Focus |
|-----------|-------|-------|
| `TestBrainRecordsIO` | 7 | save/load roundtrip, empty file, parent dirs, overwrite |
| `TestBrainRecordToSample` | 12 | feature vector schema, routing/policy signals, neutral defaults, reward ordering, latency clamp |
| `TestBrainTrainingJobConfig` | 3 | extra rejection, batch_size ≥ 1, sensible defaults |
| `TestBrainOfflineTrainerRun` | 11 | result type, counts, require_outcome filter, artefact on disk, loadable by NeuralPolicyModel, parent dirs, artifact path |
| `TestEndToEndPipeline` | 1 | LearningRecord → BrainRecord → JSONL → BrainOfflineTrainer → loadable model |

**Full suite:** 1440 passed, 1 skipped — all green.

---

## 6. Gate

| Check | Result |
|-------|--------|
| Scope correct (offline training only, no runtime touch) | ✅ |
| No production path touched | ✅ |
| No second router, store, or registry | ✅ |
| Fixed feature schema documented and stable | ✅ |
| Artefact compatible with ModelRegistry + ShadowEvaluator | ✅ |
| Tests green (34/34 new + 1440/1440 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Next step

**B6-S4 – Brain shadow runner**: wire `BrainOfflineTrainer` output into
`ModelRegistry` and `ShadowEvaluator`, so a Brain-trained model runs in shadow
mode alongside the production heuristic router — closing the full
train → register → shadow-evaluate loop described in the Phase 6 roadmap.
