# Phase S20 — Adapter Cost/Latency Budgets and Static Isolation Declarations

**Branch:** `codex/phaseS20-adapter-budgets`
**Date:** 2026-04-17
**Reviewer:** automated phase gate

---

## 1. Roadmap Position

**Phase 2 — Kontrollierte Erweiterbarkeit**, steps closed by this step:

| Roadmap task | Status |
|---|---|
| Kosten- und Latenzbudgets pro Adapter einführen | ✅ closed |
| Sandboxing-/Isolation-Regeln definieren | ✅ closed (static declarations) |

**Phase 2 exit criterion addressed:**
> „kein Tool darf implizit außerhalb seines Scopes handeln"

Budget limits make scope violations visible post-execution via `result.warnings`
and the canonical audit span's `warning_count`.  Isolation declarations give
operators a machine-readable description of what each adapter needs from its
deployment environment.

**Remaining Phase 2 task (next step):**
- Security-Tests gegen unsichere Plugins/Prompt Injection aufbauen (S21)

---

## 2. What was already present

- `AdapterManifest` with `risk_tier`, `capabilities`, required/optional metadata
  keys, `required_result_metadata_keys` (S15–S18)
- `result_warnings()` in `validation.py` for capability-based soft warnings (S17)
- `budget_warnings()` call site already prepared in `execution_engine.py` via
  the `result_warnings` call pattern (S18–S19)

**What was missing:**
- No `AdapterBudget` model
- No `IsolationRequirements` model
- No `budget_warnings()` function
- No concrete budget or isolation values on any adapter manifest

---

## 3. What changed

### `core/execution/adapters/budget.py` (new)

```
AdapterBudget (Pydantic BaseModel, extra="forbid")
    max_cost_usd:    float | None   ge=0.0  — USD ceiling per execution
    max_duration_ms: int   | None   ge=1    — wall-clock ceiling in ms
    max_tokens:      int   | None   ge=1    — token count ceiling

IsolationRequirements (Pydantic BaseModel, extra="forbid")
    network_access_required:   bool  — adapter makes outbound network calls
    filesystem_write_required: bool  — adapter writes local filesystem
    process_spawn_required:    bool  — adapter spawns a subprocess
    privileged_operation:      bool  — adapter may perform OS-level changes
```

All fields have `extra="forbid"` to prevent silent addition of unknown
governance fields.  `IsolationRequirements` defaults are all `False` so the
base adapter is safe by default.

### `core/execution/adapters/manifest.py` (modified)

Two new optional fields added to `AdapterManifest`:

```python
budget:    AdapterBudget        = Field(default_factory=AdapterBudget)
isolation: IsolationRequirements = Field(default_factory=IsolationRequirements)
```

Default instances are unconstrained (`AdapterBudget()` — all None) and
minimally privileged (`IsolationRequirements()` — all False).  Additive,
backward-compatible change: all existing manifest constructions without these
fields continue to work.

### `core/execution/adapters/validation.py` (modified)

New pure function `budget_warnings(manifest, result) -> list[str]` added:

- Checks all three budget fields against corresponding result fields
- Emits a human-readable warning string per violation
- Applies to both success and error results (runaway executions remain
  visible in the trace even when the adapter ultimately fails)
- Returns empty list when no limits set or result fields absent (no
  false-positive warnings for adapters that don't report cost/tokens)
- Boundary semantics: `result_value == limit` is not a violation

### `core/execution/execution_engine.py` (modified)

`budget_warnings()` imported and called after `result_warnings()`:

```python
budget_warns = budget_warnings(adapter.manifest, result)
if budget_warns:
    result.warnings.extend(budget_warns)
```

Budget violations flow through `result.warnings` and thus into the canonical
audit span's `warning_count` field (populated by S19's
`canonical_execution_span_attributes`).  No second audit path.

### Concrete adapter manifests — budget and isolation declared

| Adapter | max_cost_usd | max_duration_ms | max_tokens | network | fs_write | spawn | privileged |
|---------|-------------|-----------------|------------|---------|----------|-------|------------|
| adminbot | — | 5 000 ms | — | ✗ | ✗ | ✗ | ✗ |
| flowise | $1.00 | 30 000 ms | 4 000 | ✓ | ✗ | ✗ | ✗ |
| n8n | $1.00 | 30 000 ms | 4 000 | ✓ | ✗ | ✗ | ✗ |
| openhands | $5.00 | 120 000 ms | — | ✓ | ✓ | ✓ | ✗ |
| claude_code | $5.00 | 120 000 ms | — | ✓ | ✓ | ✓ | ✗ |
| codex | $5.00 | 120 000 ms | — | ✓ | ✓ | ✓ | ✗ |

HIGH-tier code-execution adapters: no `max_tokens` limit because they use
CLI protocols whose token counts are not reliably reported in the current
result schema.

### `tests/execution/test_adapter_budgets.py` (new)

31 tests in 5 sections:

1. `TestAdapterBudget` — field defaults, valid values, negative/zero rejection, extra fields (7)
2. `TestIsolationRequirements` — defaults, high-risk profile, extra fields (3)
3. `TestBudgetWarnings` — all violation branches; at-limit no-warning; None fields no-warning; multi-violation; error result checked (12)
4. `TestEngineIntegration` — end-to-end: mock adapter with budget violation → warning in `result.warnings` (1)
5. `TestConcreteAdapterManifests` — every adapter has budget+isolation; tier-specific assertions (8)

---

## 4. Architecture invariant check

| Invariant | Status |
|---|---|
| No parallel implementation | single `budget_warnings()`, single call site in engine |
| Single audit truth (TraceStore) | budget warnings flow through `result.warnings` → `warning_count` in canonical span, no second store |
| No business logic in wrong layer | `budget.py` and `budget_warnings()` are pure, stateless |
| Additive change | no existing field removed, no existing behaviour changed |
| No new heavy dependencies | no new packages |
| Kanonische Kernpfade | `validation.py` → `execution_engine.py` → `result.warnings` → `canonical_execution_span_attributes` |
| extra="forbid" on all new models | drift-resistant |

---

## 5. Enforcement model

Budget enforcement is **advisory (soft)** at the Python layer:

- Cost and token counts are only available post-execution; they cannot be
  prevented before the adapter returns.
- Duration limits: post-execution check surfaces violations; hard pre-execution
  timeouts are an operator-level concern (subprocess `timeout`, asyncio
  `wait_for`, HTTP client `timeout`).

Operators who require hard limits must enforce them at the infrastructure
layer (container resource limits, provider spending caps, network timeouts).
The manifest's `isolation` declarations give them a machine-readable starting
point.

This is the correct scope for a Phase 2 static governance step.  Pre-execution
hard enforcement would require significant changes to the adapter call protocol
and is deferred to a future phase if the need is demonstrated by real incidents.

---

## 6. Test results

```
31 passed (test_adapter_budgets.py)
648 passed, 1 skipped, 0 failed (full canonical suite)
```

---

## 7. Review-/Merge-Gate

| Check | Result |
|---|---|
| Scope correct (S20 tasks only)? | ✅ |
| No parallel structure? | ✅ |
| Canonical paths used? | ✅ |
| No business logic in wrong layer? | ✅ |
| No new shadow truth? | ✅ |
| Tests green? | ✅ 31/31 + 648/648 |
| Documentation consistent? | ✅ |
| Merge-ready? | ✅ |

---

## 8. Next step

**S21 — Security tests against unsafe plugins and prompt injection**

Phase 2 final remaining task:
> Security-Tests gegen unsichere Plugins/Prompt Injection aufbauen

Candidates:
- Test that an adapter with `risk_tier=HIGH` and no policy binding fails the
  policy gate (requires `policy_bindings` + `GovernanceEngine` integration)
- Test that `validate_required_metadata` blocks execution for malformed inputs
- Test that output validation rejects prompt-injected structured outputs
- Test that a manifest with unknown fields is rejected at parse time
- Characterisation tests for boundary values in `budget_warnings`
