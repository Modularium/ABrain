# Phase 6 – Brain v1 B6-S4: Brain Shadow Runner

**Branch:** `codex/phase6-brain-v1-shadow-runner`
**Date:** 2026-04-19
**Roadmap task:** "Wire BrainOfflineTrainer output into ModelRegistry + ShadowEvaluator so a Brain-trained model runs in shadow mode alongside the production heuristic router — closing the full train → register → shadow-evaluate loop from the Phase 6 roadmap."

---

## 1. Scope

Close the Phase 6 train → register → shadow-evaluate loop:

1. Extend `ModelRegistry` with a `model_kind` axis so Brain v1 artefacts and the
   existing production neural-policy artefacts coexist with independent active
   slots.
2. Add `BrainShadowRunner` — a Brain-aware analogue of `ShadowEvaluator` that
   loads the active `brain_v1` artefact, scores the production candidate set
   with the 13-dim Brain feature schema, and writes a structured comparison
   span to `TraceStore`.

New file: `core/decision/brain/shadow_runner.py`
Updated: `core/decision/learning/model_registry.py`,
`core/decision/brain/trainer.py`, `core/decision/brain/__init__.py`

---

## 2. Idempotency check

| Component | Status before B6-S4 |
|-----------|-------------------|
| `shadow_runner.py` in `brain/` | **Did not exist** |
| `ModelRegistry.register_brain` | **Did not exist** |
| `model_kind` field on `ModelVersionEntry` | **Did not exist** |
| `BRAIN_FEATURE_NAMES` / `encode_brain_features` exports | **Did not exist** (logic was inline in trainer) |
| `BrainOfflineTrainer`, `BrainTrainingResult` | ✅ on main (B6-S3) — **read-only input** |
| `ModelRegistry`, `ShadowEvaluator`, `TraceStore` | ✅ on main — **extended additively** / **untouched** |

---

## 3. Design

### Why a separate runner instead of reusing `ShadowEvaluator`?

`ShadowEvaluator` runs its loaded model through an ephemeral `RoutingEngine`
which internally calls `NeuralPolicyModel.score_candidates` → `FeatureEncoder`
→ a 14-dim production schema. The Brain artefact uses a fixed 13-dim schema
(`BRAIN_FEATURE_NAMES`) and a different feature semantics. Loading a Brain
artefact through `RoutingEngine` would trip
`NeuralPolicyModel._ensure_model`'s schema check
(`"loaded neural policy weights do not match encoded feature set"`).

`BrainShadowRunner` therefore feeds the loaded `MLPScoringModel`
pre-encoded Brain feature vectors directly, using `BrainStateEncoder` for
state construction and `encode_brain_features` (extracted from the
trainer in this step) for per-candidate vectors. **No production router
involvement, no second runtime loop.**

### `model_kind` axis on `ModelRegistry`

| Aspect | Behaviour |
|--------|-----------|
| New field | `model_kind: str = "neural_policy"` (default keeps old entries compatible on JSON reload) |
| Constants | `MODEL_KIND_NEURAL_POLICY`, `MODEL_KIND_BRAIN_V1` |
| Activation scope | `_set_active` only deactivates entries of the **same** `model_kind` — exactly one active per kind |
| Read API | `get_active(*, model_kind=...)` and `get_active_model(*, model_kind=...)` default to neural-policy → existing callers unchanged |
| Brain-specific reader | `get_active_brain_mlp() -> MLPScoringModel \| None` returns the raw scorer (not a `NeuralPolicyModel`) so the Brain runner can call `forward()` directly |
| Brain registration | `register_brain(BrainTrainingResult, BrainTrainingJobConfig, *, notes=None, activate=True)` — sets `model_kind="brain_v1"`, `schema_version="brain-v1:13"`, hashes Brain hyperparameters |

Backwards compatibility:
- Existing JSON registries with no `model_kind` field still load (default applied).
- `get_active()` (no kwargs) keeps returning the neural-policy entry as before.
- Cross-kind activation is impossible; rolling back one kind does not affect the other.

### Brain feature extraction is now a public helper

`core/decision/brain/trainer.py` exports:

- `BRAIN_FEATURE_NAMES: tuple[str, ...]` — canonical schema (13 features in fixed order)
- `encode_brain_features(state, candidate, *, latency_scale_s, cost_scale_usd) -> list[float]`

The trainer's `_brain_record_to_sample` and the new `BrainShadowRunner` both
call `encode_brain_features` — single source of truth for the schema,
guaranteeing train-time/inference-time parity.

### `BrainShadowRunner` flow

```
runner.evaluate(intent, descriptors, production_decision, *, trace_id, performance_history=None, policy=None)
  ├─ registry.get_active(model_kind="brain_v1")        → entry or None      ── exit None
  ├─ registry.get_active_brain_mlp()                    → MLPScoringModel    ── exit None
  ├─ verify scorer.weights.feature_names == BRAIN_FEATURE_NAMES ─ schema drift exit None
  ├─ BrainStateEncoder.encode(intent, descriptors, perf_history,
  │                            routing_decision=production_decision,
  │                            policy=policy)           → BrainState
  ├─ for each candidate in state.candidates:
  │     vec = encode_brain_features(state, candidate, ...)
  │     score = scorer.forward(vec)
  ├─ rank by score → brain top-1
  ├─ compute (agreement, score_divergence, top_k_overlap, num_candidates)
  ├─ write span_type="brain_shadow_eval", name="brain.shadow_evaluation"
  └─ return BrainShadowComparison
```

Like `ShadowEvaluator`:
- best-effort: any exception in `_run` returns `None` without re-raising;
- silent on missing model: returns `None` when no active Brain entry, the
  artefact is missing, or the on-disk feature schema does not match
  `BRAIN_FEATURE_NAMES`;
- never modifies `production_decision`.

### Comparison span schema

```
span_type   = "brain_shadow_eval"
name        = "brain.shadow_evaluation"
attributes  = {
    "brain_shadow.version_id":       str,
    "brain_shadow.production_agent": str | None,
    "brain_shadow.brain_agent":      str | None,
    "brain_shadow.agreement":        bool,
    "brain_shadow.score_divergence": float in [0, 1],
    "brain_shadow.top_k_overlap":    float in [0, 1],
    "brain_shadow.k":                int,
    "brain_shadow.num_candidates":   int,
}
event       = "brain_shadow_comparison" with full BrainShadowComparison payload
```

Distinct from `shadow_eval` so dashboards can plot the two shadow tracks
independently.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel production router | ✅ — runner scores via `MLPScoringModel.forward` directly; no second `RoutingEngine` |
| No second TraceStore / ModelRegistry | ✅ — both are constructor-injected, single canonical instances |
| No modification of production decision path | ✅ — `production_decision` is read-only input; production neural-policy active slot is independent |
| Additive only | ✅ — one new file, three additive edits |
| No new heavy dependencies | ✅ — stdlib + existing canonical components |
| Best-effort observability | ✅ — exceptions swallowed; missing model returns `None` |
| Backwards compat on persisted state | ✅ — `model_kind` default applies to old registry JSON |

---

## 5. Tests

**File:** `tests/decision/test_brain_shadow_runner.py`
**Count:** 32 tests (unit + end-to-end, `tmp_path` I/O)

| Test class | Tests | Focus |
|-----------|-------|-------|
| `TestRegistryBrainSupport` | 12 | `register_brain`, model_kind isolation across kinds, dataset/schema fields, hash determinism, persistence reload |
| `TestBrainShadowComparison` | 3 | schema validation: extra rejection, divergence range |
| `TestBrainShadowRunnerNoModel` | 4 | empty registry, no Brain entry, neural-policy-only registry, schema-drift artefact |
| `TestBrainShadowRunnerWithModel` | 11 | comparison return, production-decision immutability, span written, span attrs/events, agreement on single candidate, divergence/overlap ranges, custom `k`, `num_candidates`, exception swallowing |
| `TestEndToEndPipeline` | 2 | train → register → evaluate; coexistence of neural-policy and Brain shadow tracks |

**Full suite:** 1472 passed, 1 skipped — all green (76s).

---

## 6. Gate

| Check | Result |
|-------|--------|
| Scope correct (registry extension + shadow runner only) | ✅ |
| Production decision path untouched | ✅ |
| Production registry behaviour preserved (`get_active()` defaults) | ✅ |
| No second router, store, or registry | ✅ |
| Brain feature schema is single source of truth | ✅ |
| Best-effort failure handling | ✅ |
| Tests green (32/32 new + 1472/1472 suite) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Next step

**B6-S5 – Brain vs heuristic baseline evaluation**: aggregate
`brain_shadow_eval` spans across a representative trace window and compute
agreement / divergence / overlap statistics versus the heuristic router, so a
go/no-go decision on Brain v1 promotion can be made.
