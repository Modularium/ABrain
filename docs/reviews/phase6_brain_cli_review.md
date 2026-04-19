# Phase 6 – Brain v1 Operator CLI surface review

**Branch:** `codex/phase6_brain_cli`
**Date:** 2026-04-19
**Scope:** `abrain brain status` CLI subcommand backed by a new
`services.core.get_brain_operations_snapshot` wrapper around
`BrainOperationsReporter`.

---

## 1. Roadmap position

Phase 6 (B6-S1…B6-S6) and the §6.3 Observability composer
`BrainOperationsReport` are all closed on main (see
`docs/reviews/phase6_B[1-6]_review.md`,
`docs/reviews/phase6_obs_report_review.md`). The §6.4 Data Governance and
§6.5 Efficiency surfaces also landed on main since (PII detector,
provenance scanner, dataset splitter, energy estimator) and §6.2
Architecture diagrams are documented.

### Idempotency finding

The recommended next step in the user prompt was "Phase 6 Brain-v1 B6-S4".
A grep of `core/decision/brain/` confirmed B6-S4
(`BrainShadowRunner` writing `brain_shadow_eval` spans) is already on
main, alongside B6-S5/S6 and the `BrainOperationsReporter` composer.
Per the master prompt's idempotency rule, the existing artefacts were
**not** rebuilt.

The actual gap was operator-facing: **no CLI / service surface wraps
`BrainOperationsReporter`**, so the Phase-6 exit verdict
(`promote` / `observe` / `reject`) is only readable by writing Python.
Phase 7 stays gated on a real-traffic `promote` verdict from this exact
reporter — without an operator surface, that gate is invisible. This
turn closes that surface gap.

---

## 2. Design

Two thin, additive layers — both read-only:

### 2.1 `services.core.get_brain_operations_snapshot`

```python
def get_brain_operations_snapshot(
    *,
    trace_limit: int = 1000,
    workflow_filter: str | None = None,
    version_filter: str | None = None,
    max_feed_entries: int | None = None,
) -> Dict[str, Any]: ...
```

- Reuses the canonical `_get_trace_state()` accessor (same TraceStore
  resolution that every other `services.core` reader uses).
- Returns `{"error": "trace_store_unavailable", "trace_store_path": ...}`
  if no TraceStore is wired — keeps the surface defensive without
  raising into the CLI.
- Otherwise constructs `BrainOperationsReporter(trace_store=...)` with
  default thresholds, calls `.generate(...)` with the operator-supplied
  scan params, and returns `report.model_dump(mode="json")` — same
  serialisation contract as the rest of `services.core`.
- No new TraceStore queries; no new model registry; no writes.

### 2.2 `scripts/abrain_control.py`: `brain status` subcommand

Adds a `brain` parent subparser with one action `status`. Mirrors the
existing CLI conventions exactly:

- `_handle_brain_status(args)` clamps `--trace-limit` to `>= 1`, then
  calls `services.core.get_brain_operations_snapshot(...)`.
- `_render_brain_status(payload)` emits a human-readable lagebericht;
  `--json` returns the raw payload via the shared `_emit()` helper.
- Error payloads (`trace_store_unavailable`) render as
  `[WARN] Brain status unavailable: <error>` so the operator sees the
  cause without an exception trace.

Renderer surface:

```
=== Brain v1 Operations Report ===
Generated:        2026-04-19T00:00:00+00:00
Trace limit:      250
Workflow filter:  planner
Version filter:   <none>

-- Baseline --
Recommendation:   promote
Reason:           agreement 83% >= 70%
Traces scanned:   42
Shadow samples:   30
Overall:          agreement=83.0%, mean_divergence=0.120, mean_top_k_overlap=0.770

-- Suggestion feed --
Gated:            True
Gate passed:      True
Gate reason:      baseline promote
Shadow samples:   30
Disagreements:    5
Entries returned: 0
```

---

## 3. Public surface

```bash
abrain brain status [--trace-limit N] [--workflow W] [--version V] \
                    [--max-feed-entries M] [--json]
```

| Flag | Default | Behaviour |
|---|---|---|
| `--trace-limit` | 1000 | scan window in spans (clamped `>= 1`) |
| `--workflow` | none | restrict to one workflow id |
| `--version` | none | restrict to one Brain version id |
| `--max-feed-entries` | none | cap suggestion-feed entries (baseline unaffected) |
| `--json` | off | machine-readable mode (raw `BrainOperationsReport.model_dump`) |

Exit code is always `0` — error payloads are surfaced via the renderer,
matching the `health` / `runtime` / `state` subcommand convention.

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| TraceStore is the sole trace truth | ✅ — reuses `_get_trace_state()` |
| `services/core.py` is the central service wiring | ✅ — new function added there |
| `scripts/abrain` is the sole CLI | ✅ — subcommand added to existing dispatcher |
| No parallel CLI / service surface | ✅ — additive, mirrors existing patterns |
| No writes / no new dependencies | ✅ |
| `BrainOperationsReporter` semantics unchanged | ✅ — wrapper only |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only on Audit/Decision tail |

---

## 5. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 function `get_brain_operations_snapshot` |
| `scripts/abrain_control.py` | +1 subparser (`brain status`), +1 handler, +1 renderer |
| `tests/core/test_abrain_cli_brain.py` | new — 6 unit tests |
| `docs/reviews/phase6_brain_cli_review.md` | this doc |

---

## 6. Test coverage

6 tests, all green:

- **TestRenderer** (2) — baseline+feed summary contains expected fields;
  error payload renders trace-store path.
- **TestCliWiring** (4)
  - delegates to `services.core.get_brain_operations_snapshot` with
    parsed args and prints the human-readable surface;
  - `--json` mode emits a JSON-loadable payload;
  - `--trace-limit 0` is clamped to `1` before delegation;
  - service error payload is surfaced via the `[WARN] Brain status
    unavailable` render path.

---

## 7. Test gates

- Focused: `tests/core/test_abrain_cli_brain.py` — **6 passed**.
- Mandatory canonical suite (`tests/state tests/mcp tests/approval
  tests/orchestration tests/execution tests/decision tests/adapters
  tests/core tests/governance tests/services
  tests/integration/test_node_export.py`): **1190 passed, 1 skipped**.
- Full suite (`tests/` with `test_*.py`): **1689 passed, 1 skipped**
  (+6 new tests).
- CLI smoke: `bash scripts/abrain --version` → ok.

---

## 8. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (additive operator surface, no new logic) | ✅ |
| Idempotency rule honoured (B6-S1…S6 not rebuilt) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical CLI / services paths reinforced | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+6 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 9. Next step

With the operator surface in place, Phase 7 becomes *visibly* gated on
a `promote` verdict from `abrain brain status`. Natural next moves:

1. Wire `abrain brain status` into routine ops (no code change — purely
   procedural; could ship as a doc note in `docs/operations.md`).
2. Continue §6 Querschnitts-Workstreams that remain open
   (e.g. §6.1 Governance refresh, §6.6 Lifecycle/Sunset).
3. Phase 7 — deferred until real-traffic `promote` is recorded.

Phase 7 remains blocked; this turn changes only the *visibility* of that
gate, not the gate itself.
