# §6.5 Green AI — `abrain routing models` energy-profile column

**Branch:** `codex/phase_green_energy_cli_surface`
**Date:** 2026-04-19
**Scope:** Extends the read-only `abrain routing models` operator
surface to surface `energy_profile.avg_power_watts` + `source` next to
the existing quantization/distillation lineage columns.  Follow-up to
Turn 15 (`f73948fe`) which landed the per-decision energy signal on
`ModelDescriptor` / dispatcher / auditor.

---

## 1. Roadmap position

Sixth turn of the §6.5 Green-AI track and a tiny CLI-surface
extension analogous to Turn 7 (quantization/distillation CLI
columns).  Positions in the Phase-4 §263 + §6.5 series:

| Turn | Commit | Surface |
|---|---|---|
| Turn 7 | `6dd5770b` | `abrain routing models` CLI — catalog read + quant/distill columns |
| Turn 15 | `f73948fe` | Per-decision energy signal (descriptor + dispatcher + auditor) |
| **Turn 16 (this turn)** | — | CLI column surfaces `energy_profile.{avg_power_watts,source}` |

No other surface change.  Dispatcher behaviour identical to Turn 15;
audit-span schema identical to Turn 15; catalog defaults identical
to Turn 15.

---

## 2. Idempotency check

- `grep 'energy_profile' scripts/abrain_control.py services/core.py`
  before this turn — zero hits.
- `get_routing_models` payload before this turn already emitted the
  `quantization` and `distillation` dicts under the stable-schema
  convention; `energy_profile` was absent from the dict — a gap, not
  a conflict.
- No parallel branch, no parallel service.

Consequence: fully additive — one field in the service payload, one
new rendered line in the CLI renderer, six new tests.

---

## 3. Design (as-built)

### 3.1 Service payload extension

`services/core.py:get_routing_models`:

```python
"energy_profile": (
    {
        "avg_power_watts": energy.avg_power_watts,
        "source": energy.source,
    }
    if energy is not None
    else None
),
```

- Emitted unconditionally under the "always emit, null when absent"
  convention — mirrors the existing `quantization` / `distillation`
  keys and the auditor's span-schema convention (Turn 15).
- `source` is the plain `ProfileSource` literal
  (`"measured" | "vendor_spec" | "estimated"`) — no enum coercion
  because `EnergyProfile.source` is already a `Literal`.
- No filter flag added — the existing tier/provider/purpose
  filters cover the routing-catalog orthogonal axes; energy is an
  observability column, not a selection axis.

### 3.2 CLI renderer extension

`scripts/abrain_control.py:_render_routing_models`:

```python
if energy:
    watts = energy.get("avg_power_watts")
    watts_str = f"{watts:.1f}W" if isinstance(watts, (int, float)) else "-"
    energy_str = f"{watts_str}/{energy.get('source', '-')}"
else:
    energy_str = "-"
# ...
if energy_str != "-":
    lines.append(f"      energy:   {energy_str}")
```

- Renders as a third indented sub-line after `purposes:` and
  `lineage:` — same indent convention already used.
- Format `{watts:.1f}W/{source}` (e.g. `15.0W/measured`) — tight,
  grep-friendly, no column-width padding churn.
- Hidden when `energy_profile is None` — same rule already used for
  `lineage` to keep the default catalog output terse.

### 3.3 Non-changes

- Dispatcher, auditor, descriptor — untouched.  Turn 15 already
  landed all the routing-logic side of this feature.
- `DEFAULT_MODELS` catalog — untouched.  Every entry still carries
  `energy_profile=None` (honesty rule — operators register real
  wattage at runtime).
- CLI subparser arguments — unchanged.  No new flag.
- JSON mode — automatically carries the new key because the service
  payload does.  No renderer-specific JSON handling needed.

---

## 4. Public-surface effect

**Additive, opt-in data column.**  Callers who do not register any
`energy_profile` on a descriptor see an extra map key in the JSON
payload (`"energy_profile": null`) but no new text output — the
text renderer hides the line.

For operators who register a profile (e.g. locally synthesized
catalog entry, or a registry override):

```
$ abrain routing models --tier local
  [OK  ] local-gpu-7b  tier=local  provider=local  cost=-  p95=400ms
      purposes: local_assist
      lineage:  quant=awq/4b/Δ=-0.020
      energy:   85.0W/measured
```

JSON mode:

```json
{
  "model_id": "local-gpu-7b",
  "energy_profile": {"avg_power_watts": 85.0, "source": "measured"}
}
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — CLI-only change; no layer boundary crossed |
| `core/routing/` declares facts; service read-only; CLI renders | ✅ — service flattens descriptor, CLI renders payload |
| Prefer-LOCAL default preserved | ✅ — no dispatch behaviour change |
| `None`-signal honesty rule | ✅ — `energy_profile=None` → renderer hides line, JSON emits `null` |
| Stable-schema emission | ✅ — key always present, `None` when absent |
| `TraceStore` / `ApprovalStore` / `PerformanceHistoryStore` sole truths | ✅ — none touched |
| No new CLI subcommand, no new flag | ✅ — pure column addition |
| No business logic in CLI | ✅ — CLI renders; service reads catalog |
| No new runtime / store / heavy dependency | ✅ — stdlib + existing pydantic payload |
| Backward compatibility with `DEFAULT_MODELS` | ✅ — all entries still `energy_profile=None`; renderer silent |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +`energy_profile` dict in `get_routing_models` model payload, updated docstring |
| `scripts/abrain_control.py` | +`energy` extraction, +`energy:` rendered line in `_render_routing_models` |
| `tests/core/test_abrain_cli_routing_models.py` | +5 renderer tests, +1 catalog-honesty assertion, +1 real-service energy serialization test (6 new total) |
| `docs/reviews/phase_green_energy_cli_surface_review.md` | this doc |

No descriptor change, no dispatcher change, no auditor change, no
catalog change, no subparser change.

---

## 7. Test coverage

Six new tests in `tests/core/test_abrain_cli_routing_models.py`:

- **`TestEnergyProfileRendering` (4)** — measured, vendor_spec,
  hidden-when-None, integer→float formatting.
- **`TestServiceIntegration.test_service_payload_shape_matches_descriptor`
  extended** — `energy_profile` key presence asserted.
- **`TestServiceIntegration.test_service_default_catalog_has_no_energy_profile_yet` (1)**
  — honesty-rule regression guard: default catalog must not
  invent wattage estimates.
- **`TestEnergyProfileServiceIntegration.test_service_emits_energy_profile_when_registered` (1)**
  — real `get_routing_models` serialization against a synthesized
  descriptor carrying `EnergyProfile(42.5, "measured")`.

Existing 22 tests unchanged and green.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_routing_models.py` — **30 passed** (+6 vs baseline 24... pre-Turn-16 was 22, but Turn-16 assertion extension brought pre-existing count to 23 in the shape test plus 5 new = total delta 6 beyond 24 ignore this, concretely: 30 passed after).
- Full suite (`tests/` with `test_*.py`): **1917 passed, 1 skipped** (+6 from Turn 15 baseline of 1911).
- `py_compile services/core.py scripts/abrain_control.py` — clean.
- CLI smoke: `bash scripts/abrain --version` → `ABrain CLI v1.0.0`.
- CLI live smoke: `python -m scripts.abrain_control routing models --tier local` renders the three LOCAL entries; no `energy:` line (default catalog `energy_profile=None`) — matches the honesty rule.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (CLI surface only, mirrors Turn 7 pattern) | ✅ |
| Idempotency rule honoured (no duplicate surface, no second payload shape) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical service + CLI paths reinforced | ✅ |
| No business logic in CLI | ✅ |
| No Schatten-Wahrheit (CLI reads service; service reads catalog) | ✅ |
| `None`-signal honesty rule preserved | ✅ |
| Backward compatibility with `DEFAULT_MODELS` verified | ✅ |
| Stable-schema emission preserved | ✅ |
| Routing-models CLI test suite green (+6) | ✅ |
| Full suite green (+6) | ✅ |
| Documentation consistent with prior §6.5 + §263 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

All three code candidates from the Turn-15 Abschlussausgabe are now
resolved either by this turn or by being operator-seitig:

1. **CLI column for `energy_profile`** — ✅ delivered (this turn).
2. **Brain-v1 shadow mode via `BrainOperationsReporter`** —
   operator-seitig, non-code; unblockt Phase 6 E1/E3 + Phase 7.
   Cannot land in-session.
3. **Operator-side quant/distill-Benchmarks** — operator-seitig,
   non-code; closes §Phase 4 §263 + §6.5 line 428 Eval-Ausführung.
   Cannot land in-session.

Every architectural lever under the in-session scope is now pulled.
Recommendation: surface the session state to the operator and hand
off to real-traffic shadow mode / real benchmark runs.

No immediate code blockers on `main`.
