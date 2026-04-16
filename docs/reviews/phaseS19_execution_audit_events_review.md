# Phase S19 – Standardised Execution Audit Events: Review

## 1. Scope

S19 implements Phase 2 "Audit-Events für jeden Tool-Call standardisieren".

Before S19 the execution span emitted to `TraceStore` carried an ad-hoc, caller-specific attribute set with different keys and coverage across the three call sites (`services/core.py`, `orchestrator.py` primary, `orchestrator.py` fallback). S19 replaces all three with a single canonical function and adds the two fields that were missing from all of them: `risk_tier` and `policy_effect`.

## 2. What was already present

- `TraceStore` with SQLite-backed `SpanRecord` persistence (phaseN/K)
- `start_child_span` / `finish_span` call structure in all three execution paths (phaseS area)
- Execution spans already emitted: `success`, `duration_ms`, `cost`, `warning_count`, `adapter_name`
- `result_warnings()` in `validation.py` (S18) — not yet wired to the engine

**What was missing:**
- `risk_tier` — never included in any span; governance tier of the adapter was invisible in the trace
- `policy_effect` — span emitted after governance, but the policy outcome was not recorded in the execution span's attributes
- `agent_id`, `task_type`, `source_type`, `execution_kind`, `token_count` — some present in some call sites, absent in others
- S18 `result_warnings()` not yet called anywhere — capability warnings were never surfaced

## 3. What was added

### `core/execution/audit.py` (new)

Pure function `canonical_execution_span_attributes(result, *, task_type, policy_effect) -> dict[str, Any]` assembles exactly `CANONICAL_EXECUTION_SPAN_KEYS`:

```
agent_id, adapter_name, task_type, risk_tier, source_type, execution_kind,
success, duration_ms, cost, token_count, warning_count, policy_effect
```

Reads from `result.metadata` (populated by engine) and two caller-supplied values. No side effects.

`CANONICAL_EXECUTION_SPAN_KEYS` is the exported tuple for exhaustiveness checks.

### `core/execution/execution_engine.py` (modified)

Two additions to `ExecutionEngine.execute()`:
1. `result.metadata.setdefault("risk_tier", adapter.manifest.risk_tier.value)` — populates the governance tier before returning
2. `result_warnings(adapter.manifest, result)` — called and appended to `result.warnings`; capability warnings now flow through naturally to the span's `warning_count`

### `core/orchestration/orchestrator.py` (modified)

Both execution `finish_span` calls (primary at line ~685, fallback at line ~1135) replaced with `canonical_execution_span_attributes(...)`. Import added at top of file.

### `services/core.py` (modified)

`run_task` execution `finish_span` call replaced with `canonical_execution_span_attributes(...)`. Import is lazy (inside the try block) for consistency with the existing import pattern in that file.

### `tests/execution/test_execution_audit.py` (new)

18 tests across four sections:
1. `canonical_execution_span_attributes()` shape and field values — 13 cases
2. `CANONICAL_EXECUTION_SPAN_KEYS` exhaustiveness — 3 cases
3. `ExecutionEngine.execute()` — `risk_tier` in metadata and capability warning propagation — 2 cases

## 4. Architecture invariants verified

| Invariant | Status |
|---|---|
| Single canonical audit path | one function for all three execution spans |
| TraceStore remains the single audit truth | no second store, no second span |
| No business logic in wrong layer | `audit.py` is pure, no state |
| Additive change | no existing span removed, only attributes standardised |
| No new dependencies | no new packages |
| Pure function | `canonical_execution_span_attributes` has no side effects |

## 5. Canonical span attribute table

| Field | Source | Note |
|---|---|---|
| `agent_id` | `result.agent_id` | Which agent ran |
| `adapter_name` | `result.metadata["adapter_name"]` | Set by engine |
| `task_type` | Caller (task context) | |
| `risk_tier` | `result.metadata["risk_tier"]` | Set by engine (S19) |
| `source_type` | `result.metadata["source_type"]` | Set by engine |
| `execution_kind` | `result.metadata["execution_kind"]` | Set by engine |
| `success` | `result.success` | |
| `duration_ms` | `result.duration_ms` | None when not reported |
| `cost` | `result.cost` | None when not reported |
| `token_count` | `result.token_count` | None when not reported |
| `warning_count` | `len(result.warnings)` | Includes S18 capability warnings |
| `policy_effect` | Caller (policy decision) | Governance outcome |

## 6. Test results

```
617 passed, 1 skipped, 6 warnings
```

## 7. Files changed

| File | Change |
|---|---|
| `core/execution/audit.py` | new — canonical audit function and key tuple |
| `core/execution/execution_engine.py` | `risk_tier` metadata + capability warnings via S18 `result_warnings()` |
| `core/orchestration/orchestrator.py` | both execution spans use canonical function |
| `services/core.py` | `run_task` execution span uses canonical function |
| `tests/execution/test_execution_audit.py` | new — 18 tests |
| `docs/reviews/phaseS19_execution_audit_events_review.md` | this file |

## 8. Gate result

| Check | Result |
|---|---|
| Scope correct | yes — Phase 2 "Audit-Events für jeden Tool-Call" |
| No parallel structure | yes — one canonical function, three call sites |
| Canonical paths used | yes — TraceStore, SpanRecord, execution_engine |
| No business logic in wrong layer | yes |
| No shadow truth | yes |
| Tests green | yes — 617/617 |
| Documentation consistent | yes |
| **Merge-ready** | **yes** |

## 9. Phase 2 status after S19

| Phase 2 task | Status |
|---|---|
| Manifest spezifizieren | done (S15) |
| Capabilities beschreiben | done (S15) |
| Risk-Tiering | done (S15) |
| Policy-Regeln zuordnen | done (S16) |
| Eingabe-Schemas erzwingen | done (S17) |
| Ausgabe-Schemas erzwingen | done (S18) |
| Audit-Events standardisieren | done (S19) |
| Kosten- und Latenzbudgets pro Adapter | open |
| Sandboxing-/Isolation-Regeln | open |
| Security-Tests gegen Prompt Injection | open |

## 10. Next logical step

**S20 — Kosten- und Latenzbudgets pro Adapter**: add `cost_budget` and `latency_budget_ms` fields to `AdapterManifest`, a budget-check function in `validation.py`, and enforce them either at `validate()` time (static budget) or as a post-execution check. This closes the Phase 2 "Kosten- und Latenzbudgets pro Adapter einführen" task.
