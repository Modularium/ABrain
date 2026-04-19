# §6.5 – Ops energy CLI surface review

**Branch:** `codex/phase_ops_energy_cli`
**Date:** 2026-04-19
**Scope:** `abrain ops energy` CLI subcommand backed by a new
`services.core.get_energy_report` wrapper around
`core.decision.energy_report.EnergyEstimator`, reading the canonical
`PerformanceHistoryStore` via `_get_learning_state`.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. The previous turn added
`abrain ops cost` (§6.5 cost axis) and introduced the `ops` parent
subparser. This turn adds the orthogonal §6.5 Green-AI axis: per-agent
energy reporting via `EnergyEstimator`. Both §6.5 primitives now have
operator surfaces.

---

## 2. Idempotency check

| Primitive | On main? | Operator surface? |
|---|---|---|
| `AgentPerformanceReporter` | ☑ | ☑ (last turn — `abrain ops cost`) |
| `EnergyEstimator` | ☑ (commit `94fcb2f8`) | ❌ — closed by this turn |
| `ProvenanceScanner` | ☑ | ❌ — blocked on registry persistence |
| `DatasetSplitter` | ☑ | ❌ — LearningOps consumer |
| `RetentionPruner` | ☑ | ❌ — destructive, out of scope |

`EnergyEstimator` + `EnergyEstimatorConfig` + `EnergyProfile` are
consumed verbatim — no estimation, aggregation, or profile-resolution
logic is duplicated.

---

## 3. Design

### 3.1 `services.core.get_energy_report`

```python
def get_energy_report(
    *,
    default_watts: float,
    default_source: str = "estimated",
    profiles: dict[str, dict[str, Any]] | None = None,
    sort_key: str = "total_energy_joules",
    descending: bool = True,
    min_executions: int = 0,
    agent_ids: list[str] | None = None,
) -> Dict[str, Any]: ...
```

- Reuses canonical `_get_learning_state()` — the warm-loaded
  `PerformanceHistoryStore` the routing engine already sees. No second
  history.
- Builds an `EnergyEstimatorConfig` from operator-supplied wattage:
  `default_profile` uses `default_watts` + `default_source`; optional
  per-agent `profiles` dict is coerced to `EnergyProfile` instances.
- Runs `EnergyEstimator.generate(...)` with sort/filter/agent-id knobs.
- Returns `report.model_dump(mode="json")` — fully Pydantic-driven.

Wattage is **operator-supplied**, never measured by the service.
`EnergyProfile.source` (`measured` / `vendor_spec` / `estimated`) makes
fidelity explicit in every report. Agents without an override are
counted in `report.fallback_agents` so operators see where to widen
wattage coverage.

### 3.2 `scripts/abrain_control.py`: `ops energy` subaction

Added under the existing `ops` parent subparser. Flags:

- `--default-watts FLOAT` (required) — default wattage; negative values
  clamped to `0.0` at handler level.
- `--default-source {measured,vendor_spec,estimated}` — fidelity of the
  default wattage (default `estimated`).
- `--profiles PATH` — optional JSON file: `{agent_id: {avg_power_watts,
  source?}}`. Unreadable / wrong-shape files surface a typed error
  payload (`profiles_unreadable` / `profiles_schema_invalid`) via the
  renderer without invoking the service.
- `--sort-key {total_energy_joules,avg_energy_joules,avg_power_watts,
  execution_count,agent_id}` — default `total_energy_joules`.
- `--ascending` — flips the estimator's `descending` default.
- `--min-executions N` — clamped `>= 0`.
- `--agents "id-a, id-b,..."` — comma list; whitespace/empty stripped.
- `--json` — machine-readable mode.

Renderer surfaces:

- header + generation timestamp, sort key, direction,
- totals block (agent count, execution count, total J / Wh,
  weighted avg wattage — 4 decimals),
- **fallback agents list** (capped at 20, explicit `(none)` path) so
  operators see where to widen profile coverage,
- entries list (capped at 20, each row shows watts, avg_J, total_J,
  total_Wh, profile source, and a `(fallback)` marker when the default
  profile was used).

Error payloads (`profiles_*`) render as `[WARN] Energy report
unavailable: <error>` with a `detail=` line.

---

## 4. Public surface

```bash
abrain ops energy --default-watts W \
                  [--default-source measured|vendor_spec|estimated] \
                  [--profiles path/to/profiles.json] \
                  [--sort-key total_energy_joules|avg_energy_joules|...] \
                  [--ascending] \
                  [--min-executions N] \
                  [--agents id-a,id-b,...] \
                  [--json]
```

Exit code is always `0`; argument errors surface via argparse, profile
errors via the renderer.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| PerformanceHistoryStore is the sole per-agent history truth | ✅ — `_get_learning_state` only |
| TraceStore untouched | ✅ — not read |
| `services/core.py` is the central service wiring | ✅ |
| `scripts/abrain` is the sole CLI | ✅ |
| Read-only — no mutation of store | ✅ — estimator is documented read-only |
| No new dependencies | ✅ — stdlib json only |
| `EnergyEstimator` semantics unchanged | ✅ — wrapper only |
| No parallel profile source of truth | ✅ — profiles flow only via CLI arg |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only on Decision tail |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 function `get_energy_report` |
| `scripts/abrain_control.py` | +1 subaction (`ops energy`), +1 handler, +1 renderer |
| `tests/core/test_abrain_cli_ops_energy.py` | new — 12 unit tests |
| `docs/reviews/phase_ops_energy_cli_review.md` | this doc |

---

## 7. Test coverage

12 tests, all green:

- **TestRenderer** (3) — populated totals+entries+fallbacks with
  `(fallback)` marker on default-profile rows; empty-entries and
  empty-fallbacks both render `(none)`; error payload surfaces the
  `error`+`detail` path.
- **TestCliWiring** (7)
  - defaults delegate correctly (sort=total_energy_joules, descending,
    min=0, source=estimated, profiles=None, agent_ids=None);
  - `--default-watts -50` clamps to `0.0`;
  - `--profiles profiles.json` is loaded verbatim and forwarded as a
    dict to the service;
  - missing profiles file surfaces `profiles_unreadable` WITHOUT
    invoking the service;
  - non-object profiles JSON surfaces `profiles_schema_invalid` WITHOUT
    invoking the service;
  - `--sort-key avg_power_watts --ascending --min-executions -5
    --agents " a , ,b"` flips direction, clamps minimum, splits+trims
    agents list;
  - `--json` mode emits a JSON-loadable payload.
- **TestServiceIntegration** (2) — without mocks: real
  `PerformanceHistoryStore` is injected via `_get_learning_state`
  monkeypatch, `record_result()` calls feed the estimator;
  (a) default-only profile path → 300 W × 2.0 s = 600 J entry,
  agent shows up in `fallback_agents`; (b) explicit override
  `{avg_power_watts:400, source:measured}` wins over the default,
  fallback list is empty.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_ops_energy.py` — **12 passed**.
- Mandatory canonical suite: **1141 passed, 1 skipped** (+12 new).
- Full suite (`tests/` with `test_*.py`): **1727 passed, 1 skipped**
  (+12 new).
- CLI smoke: `python -m scripts.abrain_control ops energy --help`
  renders argparse help cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (additive operator surface, no new logic) | ✅ |
| Idempotency rule honoured (no §6.5 primitive rebuilt) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical CLI / services / store paths reinforced | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+12 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

With `abrain ops cost` and `abrain ops energy` both on main, the §6.5
operator sweep is complete at the primitive level. Remaining high-value
gap-fill candidates:

1. `abrain governance provenance` — still blocked on a persistent
   `KnowledgeSourceRegistry` loader in `services/core`. A separate
   bootstrap turn would land `ABRAIN_KNOWLEDGE_SOURCES_PATH` + JSON
   loader, then the CLI drops on top.
2. `abrain learningops split` — wrap `DatasetSplitter` over the
   canonical `TrainingDataset` so operators can audit deterministic
   train/val/test partitioning (§6.4 / §6 LearningOps seam).

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate.
