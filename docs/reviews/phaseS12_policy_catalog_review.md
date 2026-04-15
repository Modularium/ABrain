# Phase S12 — Policy Catalog & Approval Transition Tests

**Branch:** `codex/phaseS12-policy-catalog-approval-transitions`
**Date:** 2026-04-15
**Reviewer:** automated phase gate

---

## Goal

Close the policy and approval test coverage gaps left after S11:

1. Parametrized policy rule catalog covering all 9 `PolicyRule._matches()` conditions,
   all 3 `PolicyEffect` values, priority ordering, and multi-rule resolution.
2. Full `ApprovalStore` state-transition test suite covering every terminal state,
   all guard conditions, and metadata/rating/comment preservation.

Both are **read-only test additions** — no production code changed.

---

## What changed

### `tests/governance/__init__.py` — new empty package marker

Makes `tests/governance/` a proper pytest-importable package, parallel to
`core/governance/`.

### `tests/governance/test_policy_catalog.py` — 57 new tests

#### Section 1: All 9 matching conditions (33 parametrized cases)

Each condition tested with at least: positive match, negative mismatch, edge cases
(None context value, at-limit for threshold conditions).

| Condition | Cases |
|-----------|-------|
| `capability` | present, absent, empty list, None rule skips |
| `agent_id` | exact match, mismatch, None context |
| `source_type` | match, mismatch, None context |
| `execution_kind` | match, mismatch |
| `risk_level` | match, mismatch, None context |
| `external_side_effect` | True/True, True/False, True/None, False/False |
| `max_cost` | exceeded, at limit, under limit, unknown cost |
| `max_latency` | exceeded, at limit, under limit, unknown latency |
| `requires_local` | local=True fires when is_local=False; no fire when is_local=True or None; local=False fires when is_local=True |

**Critical behavior verified for threshold conditions:**
- `max_cost=1.0` with `estimated_cost=1.0` → **no match** (at limit is not exceeded)
- `max_latency=500` with `estimated_latency=500` → **no match** (at limit is not exceeded)
- `max_cost=1.0` with `estimated_cost=None` → **no match** (unknown cost is not exceeded)

**Critical behavior verified for requires_local:**
- `requires_local=True` fires when agent is non-local (`is_local=False`), not when local
- `requires_local=True` is conservative when `is_local=None` (no match)

#### Section 2–3: All 3 effects + default allow

- `allow`, `require_approval`, `deny` each verified via `PolicyEngine.evaluate()`
- Default `allow` when no rules registered
- Default `allow` when registered rules don't match

#### Section 4–5: Priority ordering + effect tiebreak

- Higher `priority` value wins over lower
- Within same priority: `deny(2) > require_approval(1) > allow(0)` by `_EFFECT_WEIGHT`
- `PolicyEngine.evaluate()` returns the `matched[0]` winner

#### Section 6: Multi-rule resolution

- All matched rules listed in `decision.matched_rules`
- Non-matching rules excluded from `decision.matched_rules`

#### Section 7: Compound rules

- Rule with multiple conditions matches only when ALL conditions are met
- Single-condition mismatch causes entire rule to not fire

#### Section 8: Registry JSON loading

- `{policies: [...]}` wrapper format
- Bare `[...]` list format
- Missing file → empty rule list (no crash)

#### Section 9–10: Engine integration + context mapping

- `reason` includes agent `display_name`
- `reason` uses `"unselected-agent"` fallback for `None` agent
- `build_execution_context` maps `agent_id`, `source_type`, `execution_kind`, `risk_level`
- Locality inference: `LOCAL_PROCESS` → `is_local=True`; `CLOUD_AGENT` → `is_local=False`; no agent → `is_local=None`

#### Section 11: Model validation

- Blank `id` and `description` rejected
- Invalid `effect` rejected
- Whitespace normalized from `id` and `description`

### `tests/approval/test_transitions.py` — 24 new tests

#### Transitions (4 tests)

All 4 legal `PENDING → terminal` transitions tested individually:
`APPROVED`, `REJECTED`, `CANCELLED`, `EXPIRED`

#### Initial state (2 tests)

- New request always starts `PENDING`
- Appears in `list_pending()` immediately after creation

#### `list_pending` filtering (6 tests)

- Parametrized over all 4 terminal states: none appear in `list_pending()`
- Mixed store: only the PENDING request returned
- `requested_at` ordering: ascending sort verified

#### Guard conditions (3 tests)

- Duplicate `approval_id` → `ValueError`
- Unknown `approval_id` → `KeyError`
- `get_request` returns `None` for unknown ID

#### `ApprovalDecision` validation (2 tests)

- `decision=PENDING` → `ValueError` ("terminal states")
- All 4 terminal statuses accepted

#### Metadata preservation (4 tests)

- Comment stored in `metadata["decision"]["comment"]`
- Rating stored in `metadata["decision"]["rating"]`
- Pre-existing request metadata fields preserved after decision
- `decided_by` stored in `metadata["decision"]["decided_by"]`

#### Second decision (1 test)

- `record_decision` has no guard against re-deciding — last write wins.
  Documented behavior, not a bug.

#### Persistence (3 tests)

- Decision + comment persisted and reloaded from JSON
- Multiple requests (some decided, some not) round-trip correctly
- Explicit `save_json(path)` with no auto-save path

---

## Architecture check

### 1. No production code changed

`core/governance/`, `core/approval/`, `core/evaluation/` are all unmodified.
This phase adds test coverage only.

### 2. No parallel implementation

No second policy engine, no second approval store, no shadow governance layer.

### 3. Tests use only public APIs

All tests operate via `PolicyEngine`, `PolicyRegistry`, `PolicyEvaluationContext`,
`PolicyRule`, `PolicyDecision`, `ApprovalStore`, `ApprovalRequest`, `ApprovalDecision`,
`ApprovalStatus` — all public surfaces.

The `_matches()` method is private but accessed via `get_applicable_policies()`,
which is the correct public path.

### 4. No execution side effects

Tests are pure in-memory or `tmp_path` isolated.  No SQLite trace store touched,
no real agent adapters called, no approvals written to the canonical `runtime/` path.

### 5. Scope matches roadmap Phase 1

S12 completes the policy catalog and approval transition test catalog that was
identified as a Phase 1 gap in the roadmap after S11.

---

## Test counts

| Suite | New | Total |
|-------|-----|-------|
| `tests/governance/test_policy_catalog.py` | 57 | 57 |
| `tests/approval/test_transitions.py` | 24 | 24 |
| **S12 new tests** | **81** | |

**Full suite:** 462 passed, 1 skipped (pre-existing `test_generate_flowise_nodes`), 0 failures

---

## Merge-readiness

| Check | Status |
|-------|--------|
| No production code changed | PASS |
| No parallel implementation | PASS |
| All 9 matching conditions covered | PASS |
| All 3 effects covered | PASS |
| Priority + effect ordering covered | PASS |
| All 4 terminal transitions covered | PASS |
| All guard conditions covered | PASS |
| Metadata/rating/comment preservation covered | PASS |
| Persistence round-trip covered | PASS |
| All new tests green | PASS |
| Full suite green (462 passed, 1 skipped) | PASS |
| Scope matches roadmap Phase 1 | PASS |

**Merge-ready: YES**
