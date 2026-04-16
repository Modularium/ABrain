# Phase S18 – Manifest-Driven Output Validation: Review

## 1. Scope

S18 implements the output half of Phase 2 "Eingabe-/Ausgabe-Schemas erzwingen".

S17 enforced that adapters receive correct inputs (required metadata keys on the `AgentDescriptor`). S18 enforces that adapters return structurally correct outputs (`ExecutionResult`) before the result is propagated upstream.

## 2. What was already present

- `ExecutionResult` Pydantic model with `extra="forbid"` (basic schema via Pydantic — S14 area)
- `AdapterManifest` with `required_metadata_keys` and `optional_metadata_keys` (S15)
- `validate_required_metadata()` and `missing_metadata_keys()` in `validation.py` (S17)
- Flowise adapter always setting `runtime_contract` in `result.metadata` — but undeclared and unchecked (S15)

## 3. What was added

### `core/execution/adapters/manifest.py` (modified)

New field `required_result_metadata_keys: list[str]` — keys that must appear in `result.metadata` on a successful `ExecutionResult`. Error results are exempt (error paths may short-circuit before populating metadata).

### `core/execution/adapters/validation.py` (extended)

Three new pure functions:

- `missing_result_metadata_keys(manifest, result) -> list[str]`  
  Returns keys from `required_result_metadata_keys` absent in `result.metadata`. Returns empty list for error results.

- `validate_result(manifest, result) -> None`  
  Raises `ValueError` on structural violations in order:
  1. empty `agent_id`
  2. `success=True` with `error` set
  3. `success=False` without `error`, or with empty `error_code`
  4. missing `required_result_metadata_keys` on success

- `result_warnings(manifest, result) -> list[str]`  
  Soft capability-based warnings: adapters that declare `supports_cost_reporting` or `supports_token_reporting` but return `None` for those fields get a non-fatal warning. Error results are exempt.

### `core/execution/adapters/base.py` (modified)

`BaseExecutionAdapter.validate_result(result)` — delegates to `_validate_result(self.manifest, result)`. Adapter `execute()` implementations can call this before returning to surface contract violations early. Does not mutate the result.

### `core/execution/adapters/flowise_adapter.py` (modified)

Manifest gains `required_result_metadata_keys=["runtime_contract"]`. This codifies what was already a de-facto invariant (Flowise always sets `runtime_contract: "prediction_v1"`) into a verifiable contract.

### `core/execution/adapters/__init__.py` (modified)

`missing_result_metadata_keys`, `result_warnings`, `validate_result` added to imports and `__all__`.

### `tests/execution/test_adapter_output_validation.py` (new)

29 tests across five sections:
1. `missing_result_metadata_keys()` — 5 cases
2. `validate_result()` structural invariants — 9 cases, all error messages checked
3. `result_warnings()` capability-based — 8 cases including zero-cost edge case
4. `BaseExecutionAdapter.validate_result()` delegation — 4 cases
5. Integration: Flowise contract — 3 cases

## 4. Architecture invariants verified

| Invariant | Status |
|---|---|
| No parallel implementation | single `validate_result` function, no second path |
| No mutation of ExecutionResult | `validate_result` raises or returns, never mutates |
| Pure functions | no side effects, no registry access, no singletons |
| Uniform error surface | raises `ValueError` matching existing adapter raises |
| Additive change only | no existing logic removed or changed |
| No new dependencies | no new packages |
| Capabilities source of truth | `manifest.capabilities` drives warnings, not duplicated logic |

## 5. Design notes

**Why error results are exempt from `required_result_metadata_keys`:**  
Error paths short-circuit execution before metadata is populated. Requiring metadata keys on error results would force every adapter's error path to populate extra fields, adding noise with no governance value.

**Why `result_warnings` is separate from `validate_result`:**  
Capability violations (cost/token not reported) are informational, not structural errors. A cost of `None` from a cost-capable adapter may be a minor observability gap, not a broken contract. Keeping them as warnings allows the engine or adapter to attach them to the result without blocking execution.

**Why Flowise is the only adapter with `required_result_metadata_keys`:**  
`runtime_contract` is the only metadata key that Flowise commits to always setting on success. Other adapters set variable metadata (e.g., AdminBot's `tool_name` varies by execution, N8N's `workflow_id` may be None). Requiring variable keys would produce false positives.

## 6. Test results

```
599 passed, 1 skipped, 6 warnings
```

All execution, adapters, core, approval, orchestration, state, decision, services, and integration tests green.

## 7. Files changed

| File | Change |
|---|---|
| `core/execution/adapters/manifest.py` | `required_result_metadata_keys` field added |
| `core/execution/adapters/validation.py` | `missing_result_metadata_keys`, `validate_result`, `result_warnings` added |
| `core/execution/adapters/base.py` | `BaseExecutionAdapter.validate_result()` method added |
| `core/execution/adapters/flowise_adapter.py` | manifest gains `required_result_metadata_keys=["runtime_contract"]` |
| `core/execution/adapters/__init__.py` | new functions exported |
| `tests/execution/test_adapter_output_validation.py` | new — 29 tests |

## 8. Gate result

| Check | Result |
|---|---|
| Scope correct | yes — Phase 2 "Ausgabe-Schemas erzwingen" |
| No parallel structure | yes |
| Canonical paths used | yes |
| No business logic in wrong layer | yes |
| No shadow truth | yes |
| Tests green | yes — 599/599 |
| Documentation consistent | yes |
| **Merge-ready** | **yes** |

## 9. Phase 2 status after S18

| Phase 2 task | Status |
|---|---|
| Plugin-/Adapter-Manifest spezifizieren | done (S15) |
| Capabilities formal beschreiben | done (S15) |
| Risk-Tiering pro Plugin/Adapter einführen | done (S15) |
| jedem Tool/Adapter Policy-Regeln zuordnen | done (S16) |
| Eingabe-Schemas erzwingen | done (S17) |
| Ausgabe-Schemas erzwingen | done (S18) |
| Output-Validatoren für kritische Aktionen | done (S18) |
| Kosten- und Latenzbudgets pro Adapter | open |
| Sandboxing-/Isolation-Regeln definieren | open |
| Audit-Events für jeden Tool-Call standardisieren | open |
| Security-Tests gegen Prompt Injection | open |

## 10. Next logical step

**S19 — Audit-Events für Tool-Calls standardisieren**: ensure every adapter execution emits a structured audit event to `TraceStore` with canonical fields (adapter, agent_id, task_type, success, cost, duration, risk_tier). This closes the "Audit-Events für jeden Tool-Call standardisieren" Phase 2 task.
