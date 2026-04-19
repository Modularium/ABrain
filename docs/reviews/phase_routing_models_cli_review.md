# Phase 4 — `abrain routing models` operator surface

**Branch:** `codex/phase_routing_models_cli`
**Date:** 2026-04-19
**Scope:** Read-only operator surface exposing the canonical
`core.routing.catalog.DEFAULT_MODELS` catalog with the additive
quantization/distillation lineage fields landed in the prior two
turns.  New `services.core.get_routing_models` + a new `routing`
parent on the canonical CLI with one `models` subcommand.  No routing
policy change, no dispatcher or auditor touch.

---

## 1. Roadmap position

Follows the two prior Phase-4 turns:

| Turn | Commit | Surface |
|---|---|---|
| §4 declaration layer | `037b161e` | `ModelDescriptor.quantization` / `.distillation` fields + registry advisory |
| §4 audit layer | `a92b76e3` | `RoutingAuditor` span attributes |
| **§4 operator-surface (this turn)** | — | `abrain routing models` read-only CLI |

The three turns together close the operator-reachability side of
`docs/ROADMAP_consolidated.md:263` — an operator can now **declare**
a quantized/distilled LOCAL artefact, **inspect** the declared
catalog via CLI, and **audit** dispatch attribution for those
artefacts via TraceStore.  Dispatcher policy-awareness
(`quality_delta_vs_teacher` as routing signal) and the conversion
pipeline stay deferred per the inventory.

The new surface also rounds out the §6 operator-reach story — every
existing read-only inventory command (`governance retention`,
`governance pii`, `governance provenance`, `governance sources`,
`ops cost`, `ops energy`, `learningops split`, `learningops filter`)
now has a Phase-4 sibling for the routing layer.

---

## 2. Idempotency check

- `grep -n "get_routing_models\|_handle_routing\|_render_routing"` over `services/` + `scripts/` before this turn — zero primitive hits; only prose references in `phase_quantization_inventory.md` and `phase_quantization_auditor_attributes_review.md`.
- `grep -n '"routing"' scripts/abrain_control.py` — only returned the historical `step.get("routing")` attribute lookup at line 533 (unrelated).  No pre-existing `routing` top-level parser.
- No parallel branch, no partial CLI surface.
- Declaration and audit layers from the prior turns supply all required data shapes — this turn is pure read-through.

Consequence: fully additive landing.  No renames, no migrations, no
shimming.

---

## 3. Design

### 3.1 `services.core.get_routing_models(...)`

Pure read of `core.routing.catalog.DEFAULT_MODELS`, not of a live
registry.  Rationale: the CLI answers *"what models does ABrain know
about and what provenance do they declare?"* — a declaration question,
not a runtime-availability question.  Going through
`build_default_registry()` would hide LOCAL entries by default (the
registry-bootstrap gates them on `enable_local=True`), which is wrong
for inspection.

```python
def get_routing_models(
    *,
    tier: str | None = None,
    provider: str | None = None,
    purpose: str | None = None,
    available_only: bool = False,
) -> dict:
    ...
```

Behaviour:

- All filters are case-insensitive; normalised to lowercase before matching.
- Unknown filter values short-circuit with `{"error": "invalid_tier|invalid_provider|invalid_purpose", "detail": ...}` — same error-payload shape as other read-only services (`provenance`, `sources`, etc.) and ensures CLI typos surface cleanly rather than returning a misleading empty result.
- Payload shape:

  ```
  {
    "total":         <filtered count>,
    "catalog_size":  <full DEFAULT_MODELS size>,
    "filters":       {"tier": ..., "provider": ..., "purpose": ..., "available_only": bool},
    "tiers":         {"local": N, "small": N, "medium": N, "large": N},
    "providers":     {"anthropic": N, "openai": N, "google": N, "local": N, "custom": N},
    "purposes":      {"planning": N, "classification": N, ...},
    "models":        [<flat dict per descriptor>]
  }
  ```

- Per-model flat dict mirrors the descriptor surface **plus both
  lineage blocks** (keys always present; values `None` when absent) —
  same stable-schema convention used by the auditor in the prior turn.

### 3.2 CLI surface

New top-level `routing` parent (sibling to `governance`, `ops`,
`learningops`, etc.) with one `models` subcommand:

```
abrain routing models
    [--tier {local|small|medium|large}]
    [--provider {anthropic|openai|google|local|custom}]
    [--purpose {planning|classification|ranking|retrieval_assist|local_assist|specialist}]
    [--available-only]
    [--json]
```

Argparse `choices=` enforces valid enum values at parse time; the
service-level validators (§3.1) catch programmatic callers with
invalid lowercase strings.  Both layers end at the same error payload
shape so the CLI and the Python API behave identically.

### 3.3 Renderer

- Error branch first (`[WARN] Routing models unavailable: <error>` + optional detail).
- Header: `Total (filtered)`, `Catalog size`, active filters (or `(none)`), tier/provider/purpose summary lines showing only non-zero counts.
- Per-model line: `[OK  ]` / `[OFF ]` availability marker, `model_id`, `tier`, `provider`, cost (`$X.XXXX/1k` or `-`), p95 latency (`Nms` or `-`).  Continuation lines for `purposes` and `lineage` when present.
- Outcomes capped at 40 with `... (N more)` tail — same convention as every other governance/ops renderer.

Lineage display format: `quant=<method>/<bits>b/Δ=±0.000  distill=<method><=<teacher>/Δ=±0.000` — chosen to be grep-friendly while still readable.  `Δ` is the declared `quality_delta_vs_baseline` / `quality_delta_vs_teacher`; renders as `-` when absent.

### 3.4 Non-changes

- `ModelDispatcher` — unchanged.  Prefer-LOCAL semantics not touched.
- `RoutingAuditor` — unchanged.  Span schema identical.
- `ModelDescriptor` / `ModelRegistry` — only read, never mutated.
- `core/routing/catalog.py` — unchanged.  `DEFAULT_MODELS` identical.
- No new store, no new runtime, no new heavy dependency.
- No change to any existing CLI command.

---

## 4. Public surface

```bash
# Full catalog, including LOCAL entries and their lineage
abrain routing models

# Only LOCAL models (inspect quantization/distillation declarations)
abrain routing models --tier local

# Only Anthropic models that support planning
abrain routing models --provider anthropic --purpose planning

# CI / tooling: machine-readable JSON
abrain routing models --tier local --json
```

Sample text output (truncated):

```
=== Routing Models Catalog ===
Total (filtered):     10
Catalog size:         10
Active filters:       (none)

Tiers:                local=3, small=3, medium=2, large=2
Providers:            anthropic=4, openai=3, google=1, local=3, custom=0
Purposes:             planning=4, classification=5, ranking=3, ...

Models (10):
  [OK  ] llama-3-8b-local  tier=local  provider=local  cost=-  p95=800ms
      purposes: local_assist, classification
  [OK  ] claude-haiku-4-5  tier=small  provider=anthropic  cost=$0.0010/1k  p95=500ms
      purposes: local_assist, ranking, retrieval_assist
  ...
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — new surface sits on the Decision/routing side; observation-only |
| `core/routing/` declares facts; dispatcher decides; auditor observes | ✅ — only the declaration layer is read; no policy code added |
| `services/core.py` central service wiring | ✅ — new service lives there |
| `scripts/abrain` sole CLI | ✅ — new command added on the canonical CLI |
| No business logic in CLI | ✅ — handler is pass-through, renderer is pure formatting, validation lives in the service |
| Read-only surfaces default to inspection, never mutation | ✅ — no write path introduced |
| Registry bootstrap behaviour unchanged | ✅ — service reads `DEFAULT_MODELS` directly, not via `build_default_registry` |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` / `KnowledgeSourceRegistry` sole truths | ✅ — none touched |
| No new heavy dependency | ✅ — stdlib only |
| Stable schema for lineage fields in payload | ✅ — keys always present (None when absent), same convention as auditor |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +`_VALID_ROUTING_TIERS/PROVIDERS/PURPOSES` constants, +`get_routing_models(...)` |
| `scripts/abrain_control.py` | +`_render_routing_models`, +`_handle_routing_models`, +`routing` top-level parser with `models` subcommand |
| `tests/core/test_abrain_cli_routing_models.py` | new — 24 tests |
| `docs/reviews/phase_routing_models_cli_review.md` | this doc |

---

## 7. Test coverage

24 new tests:

- **TestRenderer** (11) — header, tier/provider/purpose summaries, cost/latency formatting, quantization lineage line, distillation lineage line, "(none)" filter marker, active-filter rendering, empty models placeholder, `[OFF ]` availability marker, error payload rendering, 40-row cap with tail marker.
- **TestCliWiring** (3) — default delegation (all filters `None`, `available_only=False`), all flags forwarded, JSON mode emits a dumpable payload.
- **TestServiceIntegration** (10) — full catalog by default, tier/provider/purpose filter correctness, case-insensitive tier filter, invalid filter error payloads (tier/provider/purpose), `available_only` filter correctness, per-model payload shape asserts (both lineage keys always present).

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_routing_models.py` — **24 passed**.
- Routing suite: `tests/routing/` — **194 passed** (unchanged; not touched by this turn).
- Mandatory canonical suite: **1241 passed, 1 skipped** (+24).
- Full suite (`tests/` with `test_*.py`): **1863 passed, 1 skipped** (+24).
- `py_compile services/core.py scripts/abrain_control.py` — clean.
- CLI smoke: `python -m scripts.abrain_control routing models --help` renders cleanly; `python -m scripts.abrain_control routing models --json` returns `{"total": 10, "catalog_size": 10, ...}` against the real `DEFAULT_MODELS` catalog.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (read-only inventory, inventory §4 follow-through) | ✅ |
| Idempotency rule honoured (no duplicate service/CLI/renderer) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical service path reinforced (same `services/core.py`) | ✅ |
| Canonical CLI path reinforced (same `scripts/abrain_control.py`) | ✅ |
| No routing-policy change | ✅ |
| No business logic in CLI or renderer | ✅ |
| Stable schema for lineage fields | ✅ |
| Mandatory suite green (+24) | ✅ |
| Full suite green (+24) | ✅ |
| CLI smoke green | ✅ |
| Documentation consistent with prior two turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Declaration + Audit + Operator-surface for Phase-4 §263 are now all
green on main.  Remaining candidates, roughly by size:

1. **`codex/phase_default_catalog_lineage`** — smallest — annotate the
   LOCAL entries in `core/routing/catalog.py` with their real quant/
   distill profiles (e.g., Llama-3-8B as `gguf_q4_k_m` / 4 bits).
   Exercises the advisory end-to-end and populates the new CLI
   inventory for default deployments.  One file change + updated
   catalog test.
2. **`codex/phase_quantization_routing_policy`** — larger — teach
   `ModelDispatcher` to treat `quality_delta_vs_teacher` /
   `quality_delta_vs_baseline` as an additional signal in the
   prefer-LOCAL check.  Needs its own sub-inventory on tolerance
   semantics and fallback-cascade interaction before implementation.
3. **Alternative §6 surfaces** — none of the green-AI residuals in
   §6.5 currently has a cheap operator-surface win left after this
   turn.  The next §6 step would be research-shaped (cf. the
   `EnergyEstimator` per-decision metric integrations).

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`.  No immediate blockers on main.
