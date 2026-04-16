# Phase S17 – Manifest-Driven Input Validation: Review

## 1. Scope

Phase S17 implements "Eingabe- und Ausgabe-Schemas erzwingen" (Phase 2 of the consolidated roadmap).

The change adds a pure validation layer that enforces the `required_metadata_keys` contract declared in each adapter's `AdapterManifest` against the `AgentDescriptor` supplied at execution time.

## 2. What was already present

- `AdapterManifest` with `required_metadata_keys` field (S15)
- Per-adapter manifest declarations with concrete key lists, e.g. Flowise: `["base_url", "chatflow_id"]`, N8N: `["webhook_url"]` (S15)
- `BaseExecutionAdapter.validate()` entry point existed but had no metadata enforcement (S15/prior)
- `__init__.py` exports already structured (S14–S16)

## 3. What was added

### `core/execution/adapters/validation.py` (new)

Two pure functions:

- `missing_metadata_keys(manifest, descriptor) -> list[str]`  
  Returns absent required keys. No side effects, no registry access.

- `validate_required_metadata(manifest, descriptor) -> None`  
  Raises `ValueError` naming adapter, agent, and absent keys. Uniform error surface matching existing adapter-specific `ValueError` raises.

### `core/execution/adapters/base.py` (modified)

`BaseExecutionAdapter.validate()` now calls `validate_required_metadata(self.manifest, agent_descriptor)`. Every subclass gains the manifest enforcement automatically; subclasses that override `validate()` and call `super()` retain it.

### `core/execution/adapters/__init__.py` (modified)

`missing_metadata_keys` and `validate_required_metadata` added to `__all__`.

### `tests/execution/test_adapter_input_validation.py` (new)

19 tests across four sections:
1. `missing_metadata_keys()` pure function — 6 cases
2. `validate_required_metadata()` — 4 cases, error message content
3. `BaseExecutionAdapter.validate()` delegation — 4 cases
4. Integration: concrete adapters Flowise / N8N / AdminBot — 5 cases

### `tests/execution/test_flowise_adapter.py` (fixed)

Two existing tests (`test_flowise_adapter_maps_prediction_request`, `test_flowise_adapter_handles_transport_errors`) used the legacy `prediction_url` descriptor key. After S15 the Flowise manifest declares `base_url` and `chatflow_id` as required keys; the test descriptors now use those canonical keys. URL resolution is unchanged (`_resolve_prediction_url` builds the same URL from both paths).

## 4. Architecture invariants verified

| Invariant | Status |
|---|---|
| No parallel implementation | No second validation path exists |
| Single canonical truth | validation.py is the only metadata-validation module |
| No business logic in wrong layer | pure functions in execution/adapters, not in CLI/UI/API |
| No new dependencies | no new packages |
| Additive change | no existing logic removed |
| Uniform error surface | raises `ValueError` matching existing adapter raises |

## 5. Test results

```
570 passed, 1 skipped, 6 warnings
```

All execution, adapters, core, approval, orchestration, state, decision, services, and integration tests green.

## 6. Files changed

| File | Change |
|---|---|
| `core/execution/adapters/validation.py` | new — pure validation functions |
| `core/execution/adapters/base.py` | validation hook wired into `BaseExecutionAdapter.validate()` |
| `core/execution/adapters/__init__.py` | exports updated |
| `tests/execution/test_adapter_input_validation.py` | new — 19 tests |
| `tests/execution/test_flowise_adapter.py` | fixed — descriptors migrated to canonical `base_url + chatflow_id` keys |

## 7. Gate result

| Check | Result |
|---|---|
| Scope correct | yes — exactly Phase 2 "Eingabe-/Ausgabe-Schemas erzwingen" |
| No parallel structure | yes |
| Canonical paths used | yes |
| No business logic in wrong layer | yes |
| No shadow truth | yes |
| Tests green | yes — 570/570 |
| Documentation consistent | yes |
| **Merge-ready** | **yes** |

## 8. Next logical step

S17 completes the Phase 2 enforcement loop:

- S15: manifest declarations (what is required)
- S16: policy bindings per adapter (what policies apply)
- S17: input validation (enforce required metadata at validate() time)

The next step is **output validation** — enforcing that `ExecutionResult` fields satisfy adapter-specific contracts (output shape, mandatory fields, disallowed patterns) before a result is passed upstream. This would close the Phase 2 "Ausgabe-Schemas erzwingen" half.
