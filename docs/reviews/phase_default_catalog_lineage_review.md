# Phase 4 — Default catalog lineage annotation

**Branch:** `codex/phase_default_catalog_lineage`
**Date:** 2026-04-19
**Scope:** Annotate the three LOCAL entries in
`core/routing/catalog.py` with their real-world default quantization
profile (`GGUF_Q4_K_M` / 4 bits, baseline = FP16 variant) so that the
registry's under-documented-lineage advisory is silenced out of the
box and `abrain routing models` carries meaningful provenance for
default deployments.  No dispatcher, auditor, or CLI change.

---

## 1. Roadmap position

Fourth Phase-4 §263 turn, smallest of the remaining candidates per
`phase_routing_models_cli_review.md:§10`:

| Turn | Commit | Surface |
|---|---|---|
| §4 declaration layer | `037b161e` | `ModelDescriptor.quantization` / `.distillation` + registry advisory |
| §4 audit layer | `a92b76e3` | `RoutingAuditor` span attributes |
| §4 operator-surface | `6dd5770b` | `abrain routing models` read-only CLI |
| **§4 default catalog (this turn)** | — | LOCAL entries declare real quant profiles |

Together the four turns close the Phase-4 §263 operator-reachability
story: declaration ⇒ audit ⇒ inspection ⇒ meaningful default data.
Dispatcher-policy awareness (quality-delta as routing signal) and the
conversion pipeline stay deferred per
`phase_quantization_inventory.md:§2.2`.

---

## 2. Idempotency check

- `grep -n "quantization=\|distillation=" core/routing/catalog.py` before this turn — zero hits.  Only prose in the module docstring.
- `grep -n "QuantizationProfile\|QuantizationMethod" core/routing/` — only primitive declarations in `core/routing/models.py` and re-exports in `__init__.py`.  No existing catalog use.
- No parallel branch.  The declaration layer primitives are already live on `main`, so this is a pure consumer.
- Registry advisory (`_advisory_warnings`, added in `037b161e`) already
  flags LOCAL descriptors with no lineage — annotating the catalog is
  the intended follow-through, not a duplicate mechanism.

Consequence: fully additive landing.  No renames, no migrations, no
shimming.

---

## 3. Design

### 3.1 What gets declared

Each of the three LOCAL entries gets a `QuantizationProfile`:

| model_id                  | method         | bits | baseline_model_id            |
|---------------------------|----------------|------|------------------------------|
| `llama-3.2-1b-local`      | `gguf_q4_k_m`  | 4    | `llama-3.2-1b`               |
| `llama-3.2-3b-local`      | `gguf_q4_k_m`  | 4    | `llama-3.2-3b`               |
| `phi-3-mini-local`        | `gguf_q4_k_m`  | 4    | `phi-3-mini-4k-instruct`     |

Rationale for `GGUF_Q4_K_M` / 4 bits:

- The three LOCAL entries all target llama.cpp / Ollama / vLLM-GGUF
  backends (per existing docstring).  `Q4_K_M` is the de facto default
  build distributed by those ecosystems and what an operator running
  `ollama pull llama3.2:1b` or `llama3.2:3b` gets without extra flags.
  `phi-3-mini-4k-instruct:q4_K_M` is likewise the Ollama default.
- Declaring any specific build is more honest than leaving the field
  empty — operators running an FP16 or Q8 variant should re-register
  with their real profile, which was always the intended workflow.

### 3.2 Why `quality_delta_vs_baseline` stays `None`

`QuantizationProfile.quality_delta_vs_baseline` is an **observed**
delta against a named baseline on a named eval suite.  ABrain has no
such eval running in CI today, and shipping an invented number would:

- Create a second (non-code) source of truth about model quality that
  decays silently when the real eval does eventually run.
- Mislead the dispatcher once `codex/phase_quantization_routing_policy`
  starts consuming the field as a routing signal.

Leaving it as `None` with a `notes` field that tells the operator "run
an eval and re-register with a measured value" preserves declaration
honesty and defers the quality-delta story to the dedicated policy
turn.  The existing `QuantizationProfile` schema validates this shape
(`quality_delta_vs_baseline: float | None`), so the catalog test
asserts the field *is* `None` out of the box — a deliberate guard
against future drift.

### 3.3 What does *not* change

- `ModelDescriptor` / `QuantizationProfile` / `DistillationLineage` —
  schema unchanged.
- `ModelRegistry` — unchanged.  The advisory code from `037b161e`
  stays in place; the new annotations just happen to satisfy it.
- `ModelDispatcher` — unchanged.  Prefer-LOCAL semantics untouched.
- `RoutingAuditor` — unchanged.  Spans now emit the populated lineage
  values automatically because the auditor already reads from the
  descriptor (landed in `a92b76e3`).
- `services/core.py` / `scripts/abrain_control.py` — unchanged.  The
  CLI inventory picks up the new lineage automatically because
  `get_routing_models` iterates `DEFAULT_MODELS` directly.
- `is_available=False` on all three LOCAL entries — unchanged; lineage
  is declaration metadata, not an availability toggle.

### 3.4 Distillation stays `None`

All three entries are quantized-from-open-weights artefacts, not
distilled student models.  Declaring a fake distillation lineage
would violate the same honesty rule as inventing a quality delta.  An
operator who has actually distilled a local model from a hosted
teacher is expected to re-register the descriptor with a populated
`DistillationLineage`.

---

## 4. Public surface change

End-to-end effect of this turn, visible via the existing CLI:

```
$ abrain routing models --tier local
=== Routing Models Catalog ===
Total (filtered):     3
Catalog size:         10
Active filters:       tier=local

Tiers:                local=3
Providers:            local=3
Purposes:             classification=3, ranking=1, local_assist=3

Models (3):
  [OFF ] llama-3.2-1b-local  tier=local  provider=local  cost=-  p95=60ms
      purposes: classification, local_assist
      lineage:  quant=gguf_q4_k_m/4b/Δ=-
  [OFF ] llama-3.2-3b-local  tier=local  provider=local  cost=-  p95=180ms
      purposes: classification, ranking, local_assist
      lineage:  quant=gguf_q4_k_m/4b/Δ=-
  [OFF ] phi-3-mini-local  tier=local  provider=local  cost=-  p95=80ms
      purposes: classification, local_assist
      lineage:  quant=gguf_q4_k_m/4b/Δ=-
```

Before this turn the `lineage` line was absent entirely for all three
LOCAL entries.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — annotation lives on the Decision/declaration side |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — only the declaration layer is touched |
| `services/core.py` central service wiring | ✅ — not touched; downstream CLI picks up the new data automatically |
| `scripts/abrain` sole CLI | ✅ — unchanged |
| No business logic in declaration layer | ✅ — pure `QuantizationProfile` literals, no computed values |
| Read-only operator surfaces behave identically | ✅ — `abrain routing models` renders the new lineage with the existing renderer |
| No invented eval numbers | ✅ — `quality_delta_vs_baseline` stays `None` with a notes line pointing operators at a real eval |
| Registry advisory remains active | ✅ — the warning code stays in place; this turn just satisfies its precondition on the defaults |
| No new heavy dependency | ✅ — stdlib / existing `core.routing.models` only |
| LOCAL-tier cost-free invariant preserved | ✅ — `cost_per_1k_tokens` stays `None` |

---

## 6. Artifacts

| File | Change |
|---|---|
| `core/routing/catalog.py` | +2 imports (`QuantizationProfile`, `QuantizationMethod`), +3 `quantization=...` blocks on LOCAL descriptors, +governance-note paragraph in module docstring |
| `tests/routing/test_routing_catalog.py` | +5 new tests: all-LOCAL-declare-quantization, bits-range, baseline-id-present-and-not-self, quality-delta-unset-by-default, registry-advisory-silenced |
| `docs/reviews/phase_default_catalog_lineage_review.md` | this doc |

No new module, no new test file, no new CLI command, no service
change.

---

## 7. Test coverage

5 new tests in the existing `TestDefaultModelsList` / `TestBuildDefaultRegistry`
classes:

- **`test_all_local_entries_declare_quantization`** — every LOCAL entry
  carries a non-`None` `QuantizationProfile`.
- **`test_local_quantization_bits_in_valid_range`** — bits ∈ [2, 16]
  (enforced by Pydantic, asserted here for regression).
- **`test_local_quantization_declares_baseline_model_id`** —
  `baseline_model_id` is present and not equal to the artefact's own
  `model_id` (catches accidental self-reference).
- **`test_local_quantization_quality_delta_unset_by_default`** —
  explicit guard against future drift where someone invents an eval
  number and commits it to the default catalog.
- **`test_local_registration_does_not_trigger_lineage_advisory`** —
  calls `ModelRegistry.register` on each LOCAL descriptor and asserts
  the missing-lineage advisory is absent from the returned warning
  list.  End-to-end verification of the intended effect.

---

## 8. Test gates

- Focused: `tests/routing/test_routing_catalog.py` — **35 passed** (+5).
- Routing suite: `tests/routing/` — **199 passed** (+5; unchanged areas untouched).
- CLI inventory: `tests/core/test_abrain_cli_routing_models.py` — **24 passed** (unchanged; consumes the new lineage transparently).
- Mandatory canonical suite: **1241 passed, 1 skipped** (+0 in the mandatory scope; the +5 lives in `tests/routing/` which is not in the mandatory list).
- Full suite (`tests/` with `test_*.py`): **1868 passed, 1 skipped** (+5).
- `py_compile core/routing/catalog.py` — clean.
- CLI smoke: `abrain routing models --tier local` renders the new
  `lineage:  quant=gguf_q4_k_m/4b/Δ=-` line for all three LOCAL
  entries.  `--json` emits the full `quantization` block.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (default catalog annotation, smallest §263 follow-up) | ✅ |
| Idempotency rule honoured (no duplicate profile, no parallel catalog) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical declaration path reinforced (`core/routing/catalog.py`) | ✅ |
| No dispatcher/auditor/service/CLI change | ✅ |
| No invented eval numbers committed | ✅ |
| Registry advisory silenced for defaults; advisory code unchanged | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+5) | ✅ |
| CLI smoke green | ✅ |
| Documentation consistent with prior three §4 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Phase-4 §263 operator-reachability is now fully closed on `main`:
declaration + audit + inspection + meaningful defaults.  Remaining
candidates, roughly by size:

1. **`codex/phase_quantization_routing_policy`** — larger — teach
   `ModelDispatcher` to consume `quality_delta_vs_teacher` /
   `quality_delta_vs_baseline` as an additional signal in the
   prefer-LOCAL / fallback cascade.  Requires its own sub-inventory
   (`phase_quantization_routing_policy_inventory.md`) on tolerance
   semantics, fallback interaction, and how to treat `None` deltas
   (the shape this catalog just shipped).  Not trivially safe without
   a real eval in CI — the inventory should define whether the policy
   gates on a measured delta or falls through to the prior
   prefer-LOCAL behaviour when the delta is absent.
2. **Alternative §6 surfaces** — none of the green-AI residuals in
   `ROADMAP_consolidated.md:§6.5` has a cheap operator-surface win
   left.  Next §6 step would be research-shaped (EnergyEstimator
   per-decision metric integration).
3. **Phase 7** — still blocked on a real-traffic `promote` verdict
   via `abrain brain status`.  No change.

No immediate blockers on `main`.
