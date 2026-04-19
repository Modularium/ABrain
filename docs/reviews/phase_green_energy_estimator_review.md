# §6.5 Green AI — EnergyEstimator review

**Branch:** `codex/phase_green_energy_estimator`
**Date:** 2026-04-19
**Scope:** read-only per-model energy-consumption estimator on top of the
canonical `PerformanceHistoryStore`. Operator-supplied wattage profiles
multiplied by observed latency and execution counts. Stdlib + pydantic
only; no new dependencies.

Closes the §6.5 *"Energieverbrauch pro Modellpfad messen"* line item —
the last remaining §6.5 Green-AI bucket apart from the Phase-7 /
evaluation-only items (quantisation/distillation).

---

## 1. Roadmap position

`docs/ROADMAP_consolidated.md` §6.5 before this turn:

- [ ] **Energieverbrauch pro Modellpfad messen** ← this turn
- [x] Kosten pro Task und pro Modellpfad reporten
- [ ] Quantisierung/Distillation für lokale Spezialmodelle evaluieren
- [x] unnötig große Modelle durch Routing und Retrieval vermeiden

The prior turn's recommendation was verbatim:

> "§6.5 *'Energieverbrauch pro Modellpfad messen'* — an energy-estimation
> surface over `PerformanceHistoryStore`. Composition: per-model wattage
> constants multiplied by observed latency/token volumes from history."

That is exactly this turn. Wattage × latency is the path taken; token
volumes stay available on the store for future extensions but are not
part of the v1 formula (see §2 for the rationale).

### Idempotency check

Before building:

- `grep -iln 'energy|watt|joule|kwh|kilowatt|EnergyEstimator|green_ai|power_draw'`
  returned only documentation hits (ROADMAP + prior reviews) — no
  existing implementation;
- `core/decision/` already ships `AgentPerformanceReporter` (§6.5 cost
  reporting) and `PerformanceHistoryStore` — the energy estimator is
  the orthogonal per-agent axis (energy vs. cost) on the same store;
- no parallel branch tracks this scope;
- no second per-agent history is introduced — `EnergyEstimator` is a
  pure operator over the canonical store.

---

## 2. Design

### Formula

For each agent in the store:

```
avg_energy_joules   = profile.avg_power_watts × history.avg_latency
total_energy_joules = avg_energy_joules × history.execution_count
total_energy_wh     = total_energy_joules / 3600
```

Wattage × active time is the textbook energy model and the only honest
one given the signals we already have on disk: `avg_latency` is the
observed active time per invocation, `execution_count` is the number of
invocations. Tokens/sec could be a secondary axis but would require
either a second wattage constant (J/token) or an assumed tokens→seconds
conversion — both of which push more operator guesswork into the config
without buying accuracy the store's latency signal already provides.

### Honest fidelity tagging

`EnergyProfile.source` is a tri-state `Literal["measured", "vendor_spec",
"estimated"]`. Default is `"estimated"`, because that is the honest
label for any number an operator pastes in without instrumentation. The
field travels through to each `AgentEnergyEstimate.profile_source`, so a
report consumer can filter to `measured` entries only if they need
audit-grade numbers.

### Fallback visibility

Agents without an explicit profile fall back to
`config.default_profile`. The estimator records their ids in
`report.fallback_agents` (sorted for determinism) — a non-empty list is
a direct operator signal that wattage coverage is incomplete and the
totals should be treated cautiously. Silent fallback would turn an
unmeasured estimate into an apparent measurement.

### Single source of truth

All per-agent metrics come from `PerformanceHistoryStore` via
`store.snapshot()` (default) or `store.get(aid)` (when an allow-list is
passed). No second history, no trace re-derivation. This matches the
sibling `AgentPerformanceReporter` pattern exactly — both surfaces are
read-only consumers that never widen the source-of-truth surface.

### Read-only + deterministic

`TestReadOnly.test_store_is_not_mutated_by_generate` pins read-only
behaviour: two back-to-back `generate()` calls leave the store
byte-equal to its pre-call snapshot.
`test_report_is_deterministic_for_stable_store` pins determinism of the
analytical payload (entries, totals, fallback_agents) — only
`generated_at` varies run-to-run.

### No new dependencies

Stdlib + pydantic, same dependency footprint as the rest of
`core/decision/`.

---

## 3. Public API

```python
from core.decision import (
    EnergyEstimator,
    EnergyEstimatorConfig,
    EnergyProfile,
    PerformanceHistoryStore,
)

store: PerformanceHistoryStore = services.performance_history_store
config = EnergyEstimatorConfig(
    default_profile=EnergyProfile(avg_power_watts=50.0),
    profiles={
        "gpt-4o":       EnergyProfile(avg_power_watts=700.0, source="vendor_spec"),
        "local-llama":  EnergyProfile(avg_power_watts=150.0, source="measured"),
    },
)

estimator = EnergyEstimator(store=store, config=config)
report = estimator.generate(
    sort_key="total_energy_joules",
    descending=True,
    min_executions=10,
)

for entry in report.entries:
    print(entry.agent_id, entry.total_energy_wh, entry.profile_source)

if report.fallback_agents:
    print("Agents without a measured profile:", report.fallback_agents)
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel performance store | ✅ — consumes canonical `PerformanceHistoryStore` |
| No second audit/history stack | ✅ — pure read-only estimator |
| No business logic in CLI / UI / schemas | ✅ — data-layer primitive under `core/decision/` |
| No hidden reactivation of legacy | ✅ — greenfield module; no legacy touched |
| No second source-of-truth for per-agent metrics | ✅ — estimator is an operator over the store |
| Read-only input | ✅ — store never mutated |
| Operator honesty about wattage fidelity | ✅ — `EnergyProfile.source` + `report.fallback_agents` |
| Additive only | ✅ — one new module + re-exports + tests + doc |
| No new dependencies | ✅ — stdlib + pydantic |

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/decision/energy_report.py` | `EnergyProfile`, `EnergyEstimatorConfig`, `AgentEnergyEstimate`, `EnergyTotals`, `EnergyReport`, `EnergyEstimator` |
| `core/decision/__init__.py` | re-exports the 6 new public symbols |
| `tests/decision/test_energy_report.py` | 25 unit tests |
| `docs/reviews/phase_green_energy_estimator_review.md` | this doc |
| `docs/ROADMAP_consolidated.md` | §6.5 energy line ☑ |

---

## 6. Test coverage

25 tests, all green:

- **TestEnergyProfile** (5) — default source = `"estimated"`; accepted
  sources; negative wattage rejected; `extra="forbid"` on profile and
  config.
- **TestEmptyStore** (1) — empty store → empty report with zeroed
  totals.
- **TestSingleAgent** (3) — formula W × s × n; zero latency → zero
  energy; zero executions → zero total but non-zero avg.
- **TestProfileResolution** (3) — override precedence; fallback list
  populated for agents using the default; fallback list is sorted.
- **TestTotals** (3) — joules sum; Wh = J / 3600; weighted power is
  execution-count-weighted; zero-exec path yields zero weighted power.
- **TestSortAndFilter** (5) — default sort is `total_energy_joules`
  desc; sort by agent_id asc; `min_executions` filter; `agent_ids`
  allow-list; unknown ids in allow-list surface with zero energy
  (coverage-gap signal).
- **TestReadOnly** (2) — store unchanged across two `generate()` calls;
  analytical payload deterministic.
- **TestSchemaHardening** (3) — `extra="forbid"` on
  `AgentEnergyEstimate`, `EnergyTotals`, `EnergyReport`.

### Suites

- Mandatory canonical (`tests/state tests/mcp tests/approval
  tests/orchestration tests/execution tests/decision tests/adapters
  tests/core tests/governance tests/services
  tests/integration/test_node_export.py`): **1184 passed / 1 skipped**.
- Full (`tests/` with `test_*.py`): **1683 passed / 1 skipped** (+25
  over the 1658 baseline from the prior §6.4 splitter turn).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (energy estimator over PerformanceHistoryStore) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical store used (read-only) | ✅ |
| No new shadow source-of-truth | ✅ |
| Fidelity signal visible to operators | ✅ (`profile_source`, `fallback_agents`) |
| Mandatory suite green | ✅ |
| Full suite green (+25 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

§6.5 Green AI is now closed apart from *"Quantisierung/Distillation für
lokale Spezialmodelle evaluieren"*, which is an evaluation task — it
produces a decision document, not new canonical code, and is better
deferred until Phase 6 Brain v1 has a real-traffic energy/cost footprint
to evaluate against.

**Recommendation for the next turn:** §6.2 *"Architekturdiagramme für
Kernpfad, Plugin-Pfad, LearningOps"* — a pure doc turn using the same
inventory pattern as the `phase_doc_audit_*` series. Low risk, high
onboarding value, and it consolidates the three flows that §6.3 / §6.4
surfaces already exist for.

Alternatives of comparable weight:

- §6.1 / §6.6 open governance items that need a pass;
- Phase 6 Brain-v1 *B6-S4* — the next canonical LearningOps step once
  offline-trainer + registry + shadow-evaluator + splitter are in.

Phase 7 stays deferred until a real-traffic `promote` verdict from
`BrainOperationsReporter` is on record.
