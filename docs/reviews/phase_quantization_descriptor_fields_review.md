# Phase 4 — Quantization/Distillation declaration-layer primitive

**Branch:** `codex/phase_quantization_descriptor_fields`
**Date:** 2026-04-19
**Scope:** Land the minimal architecture-conformant primitive specified
verbatim in `phase_quantization_inventory.md §4` — additive pydantic
declaration of quantization and distillation lineage on
`ModelDescriptor`, plus one new advisory warning in `ModelRegistry`.
No dispatcher, auditor, or CLI change. Closes one half of the Phase-4
§263 roadmap row (declaration surface); policy/audit/CLI reach-through
remains explicitly deferred to future turns.

---

## 1. Roadmap position

`docs/ROADMAP_consolidated.md:263`:

> `[ ] Quantisierungs- und Distillationspfad für lokale Modelle
> aufbauen — *deferred zusammen mit §6.5 Green-AI-Items*`

The preceding turn (inventory, merge `e7c5cb90`) split this row into
three sub-concerns:

1. **Declaration surface** (declared facts on `ModelDescriptor`).
2. **Routing policy surface** (dispatcher awareness).
3. **Conversion pipeline surface** (operator-side, not ABrain core).

This turn lands concern 1 verbatim from the inventory §4 spec. Concerns
2 and 3 remain deferred.

---

## 2. Idempotency check

Before starting:

- `grep -ri "QuantizationProfile\|QuantizationMethod\|DistillationLineage\|DistillationMethod"` over the repo returned **one hit**, in `docs/reviews/phase_quantization_inventory.md` (the inventory's prose spec). No primitive on main.
- `grep -ri "quantiz\|distill"` in `core/` + `services/` — zero primitive hits (unchanged from the inventory).
- No parallel branch, no partial implementation, no duplicated scanner/policy shape to reconcile.

Consequence: pure additive landing. No renames, no migrations, no back-compat shims — existing `ModelDescriptor` instances on main continue to validate without change because both new fields default to `None`.

---

## 3. Design

### 3.1 Pydantic enums (new)

Added to `core/routing/models.py`:

```
class QuantizationMethod(StrEnum):
    FP16, INT8, INT4,
    GGUF_Q4_K_M, GGUF_Q5_K_M, GGUF_Q8_0,
    AWQ, GPTQ, CUSTOM

class DistillationMethod(StrEnum):
    KD, FITNETS, SELF_DISTILL, CUSTOM
```

The `CUSTOM` tail on each enum is deliberate — the operator ecosystem
for LOCAL-tier artefacts is too open to enumerate exhaustively, and an
open enum with a `notes` escape hatch is closer to the "declare facts,
not restrict the world" invariant than a closed set would be.

### 3.2 Pydantic models (new)

```
class QuantizationProfile(BaseModel, extra="forbid"):
    method: QuantizationMethod
    bits: int                             # 2..16
    baseline_model_id: str | None         # stripped; empty rejected
    quality_delta_vs_baseline: float | None   # [-1.0, 1.0]
    evaluated_on: str | None              # eval-set slug
    notes: str | None

class DistillationLineage(BaseModel, extra="forbid"):
    teacher_model_id: str                 # required, stripped
    method: DistillationMethod
    quality_delta_vs_teacher: float | None    # [-1.0, 1.0]
    evaluated_on: str | None
    notes: str | None
```

`teacher_model_id` is the only required string beyond `method` — a
distillation lineage without a named teacher carries no provenance
value and is therefore rejected by the validator. `baseline_model_id`
on `QuantizationProfile` is optional because quantization against an
unregistered vendor baseline (e.g., an Ollama tag) is a legitimate
case.

### 3.3 `ModelDescriptor` — additive fields

```
quantization: QuantizationProfile | None = None
distillation: DistillationLineage | None = None
```

Plus one new `@model_validator(mode="after")` stage enforcing:

> quantization / distillation may only be declared on `ModelTier.LOCAL`
> — hosted models are not quantized/distilled by the operator and
> therefore must not carry operator-owned lineage metadata.

This prevents the obvious misuse where an operator attaches a
"quantization" note to a hosted Claude/GPT descriptor. Cost invariant
(`LOCAL` tier must not declare cost) was already enforced; this
validator mirrors that shape.

### 3.4 `ModelRegistry._advisory_warnings` — one new entry

```
if (
    descriptor.tier == ModelTier.LOCAL
    and descriptor.quantization is None
    and descriptor.distillation is None
):
    warnings.append(
        f"Model '{descriptor.model_id}' is LOCAL tier but declares neither "
        f"quantization nor distillation.  Local model provenance will be "
        f"under-documented in the audit trail."
    )
```

Non-fatal — registration succeeds. This is the "nudge operators to
document their local artefact provenance" surface. Existing LOCAL
descriptors on main (and in `DEFAULT_MODELS`) continue to register
cleanly; they just gain one extra advisory line.

### 3.5 `core/routing/__init__.py`

Export surface extended with `QuantizationMethod`, `QuantizationProfile`,
`DistillationMethod`, `DistillationLineage`. No re-export churn.

### 3.6 Non-changes (preserved verbatim from the inventory §4.5)

- `ModelDispatcher` — unchanged. Prefer-LOCAL semantics untouched.
- `RoutingAuditor` — unchanged. Existing KPI span shape intact.
- `services/core.py` — unchanged. No new service.
- `scripts/abrain_control.py` — unchanged. No new CLI.
- `core/routing/catalog.py` — unchanged. Default catalog still registers without lineage (advisory fires for any LOCAL entry; intentional nudge).
- No new store, no new runtime, no new heavy dependency (stdlib + pydantic only).

---

## 4. Public surface (new)

```python
from core.routing import (
    QuantizationMethod,
    QuantizationProfile,
    DistillationMethod,
    DistillationLineage,
)

profile = QuantizationProfile(
    method=QuantizationMethod.GGUF_Q4_K_M,
    bits=4,
    baseline_model_id="llama-3-8b",
    quality_delta_vs_baseline=-0.04,
    evaluated_on="abrain-routing-eval-v3",
)

lineage = DistillationLineage(
    teacher_model_id="claude-opus-4-7",
    method=DistillationMethod.KD,
    quality_delta_vs_teacher=-0.12,
    evaluated_on="abrain-routing-eval-v3",
)

descriptor = ModelDescriptor(
    model_id="llama-3-8b-local-q4",
    display_name="Llama 3 8B (local, Q4_K_M)",
    provider=ModelProvider.LOCAL,
    purposes=[ModelPurpose.LOCAL_ASSIST],
    tier=ModelTier.LOCAL,
    p95_latency_ms=800,
    quantization=profile,
    distillation=lineage,
)
```

No migration required for existing descriptors — both new fields
default to `None`.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — additive on the routing declaration layer, no layer crossing |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — only declaration extended |
| `ModelRegistry` sole truth for available models | ✅ — extension is purely additive |
| Prefer-LOCAL routing unchanged | ✅ — dispatcher not touched |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` / `KnowledgeSourceRegistry` sole truths | ✅ — none touched |
| `services/core.py` central wiring | ✅ — no service added |
| `scripts/abrain` sole CLI | ✅ — no command added |
| Destructive ops default to dry-run | ✅ — no destructive op introduced |
| No new runtime, store, or heavy dependency | ✅ — stdlib + pydantic only |
| `extra="forbid"` on every new pydantic model | ✅ |
| Existing `DEFAULT_MODELS` descriptors continue to register cleanly | ✅ — new fields default to `None`; advisory is non-fatal |

---

## 6. Artifacts

| File | Change |
|---|---|
| `core/routing/models.py` | +`QuantizationMethod`, +`DistillationMethod`, +`QuantizationProfile`, +`DistillationLineage`, +`ModelDescriptor.quantization`, +`ModelDescriptor.distillation`, +`_lineage_restricted_to_local_tier` validator |
| `core/routing/registry.py` | +1 advisory in `_advisory_warnings` (LOCAL without lineage) |
| `core/routing/__init__.py` | +4 symbols on the public surface |
| `tests/routing/test_quantization_lineage.py` | new — 25 tests |
| `docs/reviews/phase_quantization_descriptor_fields_review.md` | this doc |

---

## 7. Test coverage

25 new tests, all green:

- **TestQuantizationProfile** (7): happy path, every method accepted, bits range, quality-delta clamping, baseline stripping/empty rejection, extra-field rejection.
- **TestDistillationLineage** (5): happy path, every method accepted, teacher stripping/empty rejection, quality-delta clamping, extra-field rejection.
- **TestModelDescriptorLineage** (7): LOCAL with quant only / distill only / both / neither, hosted tier rejects quant, hosted tier rejects distill, extra field rejected.
- **TestRegistryLineageAdvisory** (6): LOCAL without lineage emits advisory, LOCAL with quant suppresses it, LOCAL with distill suppresses it, hosted never emits it, advisory is additive to latency advisory, registration still succeeds with the advisory.

---

## 8. Test gates

- Focused: `tests/routing/test_quantization_lineage.py` — **25 passed**.
- Routing suite: `tests/routing/` — **110 passed** (85 existing + 25 new).
- Mandatory canonical suite: **1217 passed, 1 skipped** (unchanged — `tests/routing/` sits outside it, but the code change is covered by upstream consumers in the mandatory list).
- Full suite (`tests/` with `test_*.py`): **1828 passed, 1 skipped** (+25 new).
- `py_compile core/routing/models.py core/routing/registry.py core/routing/__init__.py` — clean.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (declaration-only, inventory §4 verbatim) | ✅ |
| Idempotency rule honoured (no duplicate enums/models) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical routing-layer shape reinforced (same `ModelDescriptor`, same registry) | ✅ |
| Destructive path not touched | ✅ |
| Prefer-LOCAL dispatch invariant not touched | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+25 new) | ✅ |
| Documentation consistent with the inventory | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

The declaration layer is now in place. Two natural follow-up turns,
roughly independent:

1. **`codex/phase_quantization_auditor_attributes`** — extend
   `RoutingAuditor` to emit `routing.result.quantization.method`,
   `routing.result.quantization.bits`,
   `routing.result.distillation.teacher_model_id`,
   `routing.result.distillation.method` span attributes when the
   dispatcher's descriptor carries them. Purely observational; no
   routing-policy change. Small blast radius (one file + tests).
2. **`codex/phase_quantization_routing_policy`** — teach
   `ModelDispatcher` to treat `quality_delta_vs_teacher` /
   `quality_delta_vs_baseline` as an additional tie-breaker in the
   LOCAL-preference check, behind a conservative tolerance. Larger
   scope because prefer-LOCAL semantics are central to Phase 4; needs
   its own inventory sub-pass before landing.

The conversion pipeline (llama.cpp / optimum / GGUF) stays deferred
indefinitely per the inventory §5.

Roadmap §6.4 governance surface remains fully operator-reachable.
Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. No immediate blockers on main.
