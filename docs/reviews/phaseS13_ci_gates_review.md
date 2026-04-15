# Phase S13 — CI-Gates + Adapter Output Schema Contracts

**Branch:** `codex/phaseS13-ci-gates-adapter-output-contracts`
**Date:** 2026-04-15
**Reviewer:** automated phase gate

---

## Goal

Close two Phase 1 gaps in one minimal step:

1. **CI-Gates aktivieren** — The `core-ci.yml` workflow did not include `tests/state/`,
   `tests/governance/` (added in S12), or `core/evaluation/` (added in S11) in its test
   suite or py_compile list.  Any regression in these modules was invisible to GitHub CI.

2. **Adapter-Output-Snapshots definieren** — No tests formally defined the canonical shape
   and invariants of `ExecutionResult` across all adapter types.  If the output model or
   fallback-eligibility logic changed, there was no snapshot-level check to catch it.

Both changes are **additive** — no production code was modified.

---

## What changed

### `.github/workflows/core-ci.yml` — two additions

#### Test suite additions

```diff
 python -m pytest -o python_files='test_*.py' \
+  tests/state \
   tests/mcp \
   tests/approval \
   ...
   tests/core \
+  tests/governance \
   tests/services \
```

`tests/state/` (27 tests — plan/approval/trace persistence) and `tests/governance/`
(57 tests — policy catalog, S12) are now gated on every PR to `main`.

#### py_compile additions

```diff
 core/audit/trace_store.py \
 core/audit/context.py \
+core/evaluation/__init__.py \
+core/evaluation/models.py \
+core/evaluation/harness.py \
 core/execution/__init__.py \
```

The canonical evaluation layer from S11 is now syntax-checked in CI.

### `tests/execution/test_execution_result_contracts.py` — 45 new tests

#### Section 1: `ExecutionResult` model field constraints (6 tests)

- Required fields (`agent_id`, `success`) present
- `extra="forbid"` rejects unknown fields
- Success defaults: `output=None`, `error=None`, `cost=None`, `duration_ms=None`, `warnings=[]`, `metadata={}`
- Full optional field population
- Error result shape: `success=False`, `error` set, `output=None`
- JSON serialization round-trip

#### Section 2: `is_fallback_eligible()` contract (10 tests, parametrized)

**Fallback-eligible codes** (infrastructure failures only):
- `adapter_unavailable` — CLI not installed / provider absent
- `adapter_timeout` — provider unresponsive
- `adapter_transport_error` — network/connection failure

**Non-fallback codes verified** (9 cases): `execution_error`, `validation_error`,
`unknown_tool`, `policy_denied`, `approval_required`, `process_error`, `domain_error`,
empty string, unknown string.

Success results and no-error results are never fallback-eligible.

#### Section 3: `StructuredError` field contracts (5 tests)

- `error_code` + `message` required
- `code` property is a backward-compatible alias for `error_code`
- String codes accepted (open extension point)
- Optional fields default to `None`/`{}`/`[]`
- `extra="forbid"` enforced

#### Section 4: Per-adapter success/error output shape (4 tests, monkeypatched)

| Adapter | Test scenario |
|---------|--------------|
| `OpenHandsExecutionAdapter` | Success: mocked HTTP response → `success=True`, `cost≥0`, `output` set |
| `OpenHandsExecutionAdapter` | Error: `httpx.ConnectError` → `success=False`, `error` set with string code |
| `AdminBotExecutionAdapter` | Success: mocked `execute_tool` → `success=True`, `output` set |
| `AdminBotExecutionAdapter` | Error: `CoreExecutionError` → `success=False`, `error` set |
| `FlowiseExecutionAdapter` | Success: mocked HTTP → `success=True`, `output` set (requires `execution_kind=WORKFLOW_ENGINE`, `base_url+chatflow_id`) |
| `N8NExecutionAdapter` | Success: mocked HTTP → `success=True` (requires `webhook_url` in metadata) |

#### Section 5: Fallback code exhaustiveness and immutability (3 tests)

- `_FALLBACK_ELIGIBLE_ERROR_CODES` contains exactly `{"adapter_unavailable", "adapter_timeout", "adapter_transport_error"}` — no more, no less
- It is a `frozenset` (not mutable at runtime)
- Every code in the set triggers `is_fallback_eligible()`

#### Section 6: Per-adapter canonical snapshot fixtures (11 parametrized tests)

Success snapshots for all 5 source types (AdminBot, OpenHands, Flowise, N8N, Codex)
verify: `success=True`, `error=None`, `warnings=[]`, `is_fallback_eligible=False`,
and full JSON serialization round-trip.

Error snapshots (6 parametrized cases) verify: `success=False`, `output=None`,
correct `error_code`, and `is_fallback_eligible()` result — per the eligibility contract.

---

## Architecture check

### 1. No production code changed

`core/execution/adapters/`, `core/models/`, `core/evaluation/` — all unmodified.
Only CI config and a new test file.

### 2. CI gates now cover all canonical modules introduced in S11–S13

| Module | CI before S13 | CI after S13 |
|--------|--------------|-------------|
| `core/evaluation/` (S11) | NOT compiled | compiled |
| `tests/state/` | NOT tested | tested |
| `tests/governance/` (S12) | NOT tested | tested |
| `tests/execution/` | tested | tested + contracts |

### 3. No second execution contract

`tests/execution/test_execution_result_contracts.py` tests the **canonical**
`ExecutionResult` model from `core/execution/adapters/base.py`.  No shadow
model is introduced.

### 4. Adapter metadata contract documented in tests

The per-adapter tests now encode the correct metadata key names:
- Flowise: `base_url` + `chatflow_id` (not `flowise_base_url` / `flowise_chatflow_id`)
- N8N: `webhook_url` (not `n8n_base_url`)

These were previously only documented in the adapter source code.  The tests
make the contract checkable.

### 5. Scope matches Phase 1 roadmap

Both items — "CI-Gates für Replay und Compliance aktivieren" and "Adapter-Output-Snapshots
für Regressionstests definieren" — are Phase 1 deliverables.  This closes both.

---

## Test counts

| Suite | New | Notes |
|-------|-----|-------|
| `tests/execution/test_execution_result_contracts.py` | 45 | |
| `tests/state/` | 0 | already existed, now in CI |
| `tests/governance/` | 0 | added in S12, now in CI |

**Full suite:** 507 passed, 1 skipped (pre-existing), 0 failures

---

## Merge-readiness

| Check | Status |
|-------|--------|
| No production code changed | PASS |
| No parallel implementation | PASS |
| `tests/state/` and `tests/governance/` added to CI | PASS |
| `core/evaluation/` added to py_compile | PASS |
| All 3 fallback-eligible codes verified exhaustively | PASS |
| All 5 adapter source types snapshot-tested | PASS |
| Metadata key contracts encoded in tests | PASS |
| All new tests green | PASS |
| Full suite green (507 passed, 1 skipped) | PASS |
| Scope matches roadmap Phase 1 | PASS |

**Merge-ready: YES**

---

## What follows from S13

Remaining Phase 1 open items:
- **Safety-Metriken definieren**: policy compliance rate, unauthorized side effects,
  bad tool calls, approval bypass attempts — needs a `SafetyMetricsReport` type and
  computation logic in `BatchEvaluationReport` or alongside it
- **Routing-Baseline-Metriken**: `BatchEvaluationReport` already has routing_match_rate
  and avg_routing_confidence; remaining KPIs (P95 latency, cost per task, fallback rate)
  need computation from trace metadata
