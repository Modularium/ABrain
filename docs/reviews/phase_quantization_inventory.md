# Phase 4 – Quantisierungs- und Distillationspfad für lokale Modelle — Inventur

**Branch:** `codex/phase_quantization_inventory`
**Date:** 2026-04-19
**Scope:** Inventory-only pass on the last open Phase-4 checkbox
(`docs/ROADMAP_consolidated.md:263`). No code changes. Establishes the
canonical shape of the gap, what already exists on main, what a minimal
architecture-conformant primitive would look like, and which parts must
stay deferred behind a follow-up turn. Mirrors the "inventory-first
before implementation" rule used for prior research-shaped items.

---

## 1. Roadmap position and prior context

Roadmap §Phase 4 line 263:

> `[ ] Quantisierungs- und Distillationspfad für lokale Modelle
> aufbauen — *deferred zusammen mit §6.5 Green-AI-Items*`

This is the **only remaining unchecked item in Phase 4**. Every other
Phase-4 row (M1 registry, M2 purpose taxonomy, M3 cost/latency/risk
routing, M4 KPI audit, local-model guardrail check, fallback cascades)
is green with a review doc on main. The roadmap itself flags this row
as *deferred zusammen mit §6.5 Green-AI-Items*, which means:

- It is **not blocking** the Phase-4 exit criteria (all three exit
  criteria on lines 268–270 are already green and read:
  "nachvollziehbar und budgetbewusst" / "einfache Aufgaben benötigen
  nicht automatisch teure General-LLMs" / "hybrides Routing bringt
  messbaren Mehrwert").
- It belongs to the same cluster of long-vertagte Green-AI items
  tracked under §6.5 (Quantisierung/Distillation für lokale
  Spezialmodelle evaluieren, Energy-per-Decision metrics — the latter
  closed earlier via the `EnergyEstimator` + `abrain ops energy`
  turn).

Relationship to prior primitives already on main:

| Primitive | File | Purpose | Relevance here |
|---|---|---|---|
| `ModelDescriptor` | `core/routing/models.py` | Declared facts about one model/provider variant | **Host** for quantization/distillation metadata |
| `ModelTier` | `core/routing/models.py` | LOCAL / SMALL / MEDIUM / LARGE cost-tier enum | LOCAL tier is the scope of this item |
| `ModelRegistry` | `core/routing/registry.py` | Single source of truth for available models | Already emits advisory warnings for missing cost/latency metadata |
| `ModelDispatcher` | `core/routing/dispatcher.py` | Prefer-LOCAL routing with fallback cascades | Consumer of any new metadata field |
| `RoutingAuditor` | `core/routing/auditor.py` | Emits cost/latency/tier KPI spans to TraceStore | Natural surface for quant/distill attribution |
| `EnergyEstimator` | `core/ops/energy_estimator.py` | Energy-per-decision KPI | Already surfaces a LOCAL-vs-external KPI |
| `ModelRegistry` (learning) | `core/decision/learning/model_registry.py` | Versioned ABrain policy artefacts | **Different registry**, tracks trained ABrain models, not LLMs |

---

## 2. Canonical reading of the task

"Quantisierungs- und Distillationspfad für lokale Modelle aufbauen"
decomposes into three architectural sub-questions. Separating them is
the point of this inventory — they have very different invariant
profiles and must not be lumped into one turn:

### 2.1 Declaration surface (facts)

*What does ABrain need to know about a local model's quantization or
distillation lineage so routing and audit can reason about it?*

- Quantization method (e.g., `fp16`, `int8`, `int4`, `gguf_q4_k_m`,
  `awq`, `gptq`). This is a declared fact about the artefact the
  operator put on disk / in Ollama, not something ABrain computes.
- Distillation parent (the larger teacher model a local variant was
  distilled from), plus distillation method (`kd`, `fitnet`, `self-
  distill`), so provenance can be audited.
- Quality-vs-baseline delta: an **evaluated** quality score relative
  to the distillation parent or a pre-quantization baseline. This is
  an invariant the operator records once after evaluation; ABrain
  does not re-evaluate at routing time.

This layer is a **pure declaration extension to `ModelDescriptor`** —
additive pydantic fields with `extra="forbid"` and validators. Fits
every Phase-4 / routing-layer invariant:

- declared facts, no business logic;
- no new store, no new runtime;
- no new heavy dependencies (stdlib + pydantic);
- does not change any existing routing/dispatch behaviour.

**Target this turn or next.** See §4 for a concrete shape.

### 2.2 Routing policy surface (decisions)

*Should the dispatcher prefer a quantized/distilled LOCAL variant over
an equivalent non-quantized LOCAL model, or over an external SMALL
variant, based on the declared quality delta and the caller's quality
tolerance?*

This is routing-policy territory — it touches `ModelDispatcher` and
the cost/latency/risk scoring. Any change here must preserve:

- prefer-LOCAL default;
- fallback-cascade ordering;
- the separation between declared facts (descriptor) and routing logic
  (dispatcher).

**Target for a later turn**, after §2.1 lands. A natural split: one
turn adds the fields and advisory warnings; a follow-up turn teaches
the dispatcher to treat `quality_delta_vs_teacher` as an additional
signal in the LOCAL-preference check. Splitting keeps blast radius
small.

### 2.3 Conversion pipeline surface (operations)

*How does an operator actually produce a quantized or distilled local
artefact?*

This is the heavy part of "aufbauen". Realistic tooling is
**llama.cpp quantize**, **GGUF quantization scripts**, or
**Hugging Face optimum** — all of which are non-trivial third-party
runtimes. Pulling any of these into ABrain's `core/` would violate:

- "no new heavy dependencies" (every prior review explicitly listed
  this invariant);
- "no new runtime / no new stores";
- ABrain's provider-abstraction invariant (model conversion is a
  provider/operations concern, not an ABrain-core concern).

**Stays deferred.** The right shape is a sidecar `ops/` runbook or an
external CLI tool the operator invokes outside ABrain; ABrain only
reads the declared result. This inventory explicitly records that
decision so a future turn does not try to absorb the conversion
pipeline into `core/`.

---

## 3. Idempotency check

`grep -ri "quantiz|distill"` over `core/` and `services/` returns
**zero primitive hits** — only references in review docs
(`phase_gov_retention_prune_cli_review.md`,
`phase_learningops_export_cli_review.md`,
`phase_gov_sources_cli_review.md`, `phase_doc_audit_review.md`,
`phase_doc_architecture_diagrams_review.md`,
`phase_green_energy_estimator_review.md`) and the roadmap itself.
There is no existing quantization/distillation primitive to surface,
wrap, or de-duplicate — unlike every prior operator-surface turn.

Consequence: implementation would be genuinely new code, not a
surface exposure. Under the master prompt's "Scope präzise
festlegen / Idempotente Arbeitsweise" rules this elevates the
required caution level — hence the inventory-first split.

---

## 4. Proposed minimal canonical primitive (for a follow-up turn)

All fields optional; default `None`; `extra="forbid"` on every model.

### 4.1 `QuantizationProfile` (new, in `core/routing/models.py`)

```python
class QuantizationMethod(StrEnum):
    FP16 = "fp16"
    INT8 = "int8"
    INT4 = "int4"
    GGUF_Q4_K_M = "gguf_q4_k_m"
    GGUF_Q5_K_M = "gguf_q5_k_m"
    GGUF_Q8_0 = "gguf_q8_0"
    AWQ = "awq"
    GPTQ = "gptq"


class QuantizationProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: QuantizationMethod
    bits: int = Field(ge=2, le=16)
    baseline_model_id: str | None = Field(default=None, min_length=1, max_length=128)
    quality_delta_vs_baseline: float | None = Field(default=None, ge=-1.0, le=1.0)
    evaluated_on: str | None = Field(default=None, max_length=128)  # eval-set slug
    notes: str | None = Field(default=None, max_length=1024)
```

### 4.2 `DistillationLineage` (new, in `core/routing/models.py`)

```python
class DistillationMethod(StrEnum):
    KD = "kd"                 # standard knowledge distillation
    FITNETS = "fitnets"
    SELF_DISTILL = "self_distill"
    CUSTOM = "custom"


class DistillationLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_model_id: str = Field(min_length=1, max_length=128)
    method: DistillationMethod
    quality_delta_vs_teacher: float | None = Field(default=None, ge=-1.0, le=1.0)
    evaluated_on: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=1024)
```

### 4.3 `ModelDescriptor` additive fields

```python
quantization: QuantizationProfile | None = None
distillation: DistillationLineage | None = None
```

### 4.4 `ModelRegistry._advisory_warnings` extension

Add one new advisory (non-fatal, same shape as existing cost/latency
advisories):

> Model '<id>' is LOCAL tier but declares neither `quantization` nor
> `distillation`. Local model provenance will be under-documented in
> the audit trail.

Advisory only — registration succeeds; this keeps existing LOCAL
descriptors on main fully valid without migration.

### 4.5 Non-changes

- `ModelDispatcher` — **unchanged**. Prefer-LOCAL semantics and
  fallback cascades are not touched. A later turn can layer on
  `quality_delta_vs_teacher` awareness once the declaration layer is
  proven.
- `RoutingAuditor` — **unchanged** in the minimal primitive turn.
  A later turn can add `routing.result.quantization.method` and
  `routing.result.distillation.teacher_model_id` span attributes
  without breaking existing KPIs.
- No new service in `services/core.py`. No new CLI command. The
  declaration layer is consumed via the existing `ModelRegistry`
  APIs; operator-surface comes in a later turn once the data exists.
- No new store, no new runtime, no new heavy dependency.

---

## 5. Explicit deferrals

| Concern | Status | Reason |
|---|---|---|
| Quantization conversion pipeline (llama.cpp / optimum / GGUF) | Deferred indefinitely | Violates "no new heavy dependency" invariant; belongs in an operator-side runbook, not `core/` |
| Distillation training pipeline | Deferred indefinitely | Same reason; also duplicates `OfflineTrainer` conceptually at the wrong abstraction level |
| Dispatcher policy using `quality_delta_vs_teacher` | Deferred to a follow-up turn | Depends on §4 declaration landing first; keeps blast radius small |
| Auditor span attributes for quant/distill | Deferred to a follow-up turn | Same — landing the field set first keeps the audit extension mechanical |
| CLI surface (`abrain routing models --lineage`) | Deferred to a follow-up turn | No data exists until §4 lands; premature otherwise |
| Ollama / llama.cpp introspection to auto-fill `QuantizationProfile` | Deferred indefinitely | Couples ABrain to external runtimes; facts must be operator-declared |

---

## 6. Invariants honoured by the proposed minimal primitive

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — additive to the routing declaration layer, no layer boundary crossed |
| `core/routing/` declares facts; `dispatcher` decides; `auditor` observes | ✅ — only the declaration layer extends in the first turn |
| `ModelRegistry` sole truth for available models | ✅ — extension is additive on `ModelDescriptor` |
| `TraceStore` sole audit truth | ✅ — no new audit store |
| `PerformanceHistoryStore` / `ApprovalStore` / `KnowledgeSourceRegistry` untouched | ✅ |
| `services/core.py` central wiring | ✅ — no new service required in the first turn |
| `scripts/abrain` sole CLI | ✅ — no new CLI required in the first turn |
| No new runtime, no new store, no new heavy dependency | ✅ — stdlib + pydantic only |
| Read-only `governance retention` / `governance sources` / etc. untouched | ✅ — orthogonal surface |
| Prefer-LOCAL routing unchanged | ✅ — dispatcher is not touched in the minimal primitive turn |

---

## 7. Decision for this turn

**Inventory only.** No code changes. Reasons:

1. Master-prompt "Scope präzise festlegen" rule: a research-shaped
   roadmap row with no existing primitive should first be mapped and
   split into declaration / policy / operations concerns before any
   code lands. Splitting here lets the follow-up implementation turn
   stay within the "small, focused, canonical extension" envelope
   that every prior merged turn respected.
2. The roadmap row itself says *deferred*. Landing a declaration-only
   primitive without the audit/dispatcher/CLI reach-through would
   create a dangling field set; landing all of it in one turn would
   violate the "small blast radius per turn" rule.
3. The minimal primitive in §4 is **self-consistent and drop-in**:
   additive fields, one new advisory warning, zero behavioural
   changes. It is ready for a follow-up turn to pick up verbatim
   once prioritisation allows.

---

## 8. Artifacts

| File | Change |
|---|---|
| `docs/reviews/phase_quantization_inventory.md` | new — this inventory |
| All other files | unchanged |

---

## 9. Test gates

Because this turn contains no code change, test gates exist solely
to confirm no regression from branch creation / merge mechanics:

- `py_compile` — not applicable (no Python change).
- Mandatory suite: re-run baseline to confirm green.
- Full suite: re-run baseline to confirm green.

---

## 10. Next step

One natural follow-up turn candidate:

**`codex/phase_quantization_descriptor_fields`** — land §4 verbatim:
`QuantizationProfile`, `DistillationLineage`, additive optional
`ModelDescriptor` fields, one new advisory warning in
`ModelRegistry._advisory_warnings`. Tests: pydantic validation,
registry advisory emission, existing descriptor regression (LOCAL
descriptors without lineage still register cleanly with the new
advisory). Estimated scope: one file change in `core/routing/models.py`,
one in `core/routing/registry.py`, one new test file. No dispatcher,
no auditor, no CLI. Unblocks the roadmap row to be re-evaluated for
checkbox flip once the audit span extension (a second small turn)
also lands.

Alternative: continue on other open roadmap items; §6.5 Green-AI
cluster still has the explicit "Quantisierung/Distillation für lokale
Spezialmodelle evaluieren" evaluation row, which is research-shaped
and co-scoped with this Phase-4 row — a single future turn could
close both by referencing this inventory.

No immediate blockers on main; no code change in this turn.
