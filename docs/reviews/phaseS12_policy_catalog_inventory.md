# Phase S12 — Policy Catalog & Approval Transitions Inventory

**Date:** 2026-04-15
**Branch:** `codex/phaseS12-policy-catalog-approval-transitions`
**Purpose:** Baseline inventory before building the S12 test catalog.

---

## 1. What S11 established

S11 (`a4acd16b`) delivered the evaluation layer (`core/evaluation/`) with replay and compliance
baselines.  The full test suite was 381 passed, 1 skipped.

---

## 2. Existing test coverage for policy and approval

### 2.1 Approval tests (pre-S12)

| File | Tests | Coverage |
|------|-------|---------|
| `tests/approval/test_store.py` | 2 | persist/load round-trip, `list_pending` filtering |
| `tests/approval/test_policy.py` | 2 | `ApprovalPolicy` triggers on external side effects; stays unblocked for low-risk analysis |
| `tests/approval/test_models.py` | (existing) | basic model validation |

**Gaps identified:**
- No parametrized test for all 4 terminal transitions from PENDING
- No test for duplicate-ID guard
- No test for ordering of `list_pending`
- No test for comment/rating/metadata preservation
- No explicit test that `ApprovalDecision(decision=PENDING)` is rejected

### 2.2 Policy tests (pre-S12)

No dedicated `tests/governance/` directory existed.  The only policy tests were the 2
`ApprovalPolicy` tests in `tests/approval/test_policy.py`, which exercise the legacy
`ApprovalPolicy` wrapper, not `PolicyEngine`/`PolicyRegistry` directly.

**Gaps identified:**
- No test for all 9 `PolicyRule._matches()` conditions
- No test for all 3 `PolicyEffect` values via `PolicyEngine.evaluate()`
- No test for priority ordering (`get_applicable_policies` sort key)
- No test for effect-weight tiebreak within same priority
- No test for multi-rule resolution (all matched rules listed in decision)
- No test for compound rules (multiple conditions must all be met)
- No test for `PolicyRegistry.load_policies()` from JSON
- No test for `PolicyEngine.build_execution_context()` field mapping

---

## 3. Source code inventory for S12

### 3.1 `core/governance/policy_models.py`

| Symbol | Purpose |
|--------|---------|
| `PolicyEffect` | `Literal["allow", "deny", "require_approval"]` |
| `PolicyRule` | 9 optional matching conditions + effect + priority; `extra="forbid"` |
| `PolicyEvaluationContext` | Flattened context for deterministic matching |
| `PolicyDecision` | Outcome: effect, matched_rules, winning_rule_id, winning_priority, reason |

### 3.2 `core/governance/policy_registry.py`

| Symbol | Purpose |
|--------|---------|
| `PolicyRegistry.__init__` | Accepts `rules` list or `path` to JSON/YAML file |
| `PolicyRegistry.load_policies` | Load from `{policies: [...]}` or bare `[...]` JSON |
| `PolicyRegistry.get_applicable_policies` | Match + sort by `(-priority, -effect_weight, id)` |
| `PolicyRegistry.list_rules` | Return current loaded rules |
| `PolicyRegistry._matches` | 9-condition deterministic matcher |

### 3.3 All 9 `_matches()` conditions

| # | Condition | Fires when |
|---|-----------|-----------|
| 1 | `capability` | required capability IS in context |
| 2 | `agent_id` | agent_id matches exactly |
| 3 | `source_type` | source_type matches exactly |
| 4 | `execution_kind` | execution_kind matches exactly |
| 5 | `risk_level` | risk_level matches exactly |
| 6 | `external_side_effect` | external_side_effect matches exactly |
| 7 | `max_cost` | `estimated_cost > max_cost` (cost EXCEEDED) |
| 8 | `max_latency` | `estimated_latency > max_latency` (latency EXCEEDED) |
| 9 | `requires_local` | `is_local != requires_local` (locality violated) |

**Note on conditions 7–9:** These are threshold/constraint rules that fire when the
limit is violated.  A rule with `max_cost=1.0` fires only when `estimated_cost > 1.0`,
not when it equals or is below the limit.

### 3.4 `core/governance/policy_engine.py`

| Symbol | Purpose |
|--------|---------|
| `PolicyEngine.evaluate` | Returns `PolicyDecision`; default allow when no rules match |
| `PolicyEngine.build_execution_context` | Maps `TaskIntent` + `AgentDescriptor` → `PolicyEvaluationContext`; infers `is_local` from `execution_kind`/`source_type` |

**Locality inference in `_infer_locality`:**
- `CLOUD_AGENT` → `is_local=False`
- `CODEX` source_type → `is_local=False`
- `LOCAL_PROCESS` or `SYSTEM_EXECUTOR` execution kind → `is_local=True`
- `OPENHANDS`, `ADMINBOT`, `N8N`, `FLOWISE` source types → `is_local=True`
- Otherwise → `is_local=None`

### 3.5 `core/approval/models.py`

| Symbol | Purpose |
|--------|---------|
| `ApprovalStatus` | `PENDING APPROVED REJECTED EXPIRED CANCELLED` |
| `ApprovalDecision` | Terminal decision; `validate_decision` rejects `PENDING` |
| `ApprovalRequest` | Serializable request; starts in `PENDING` state |

### 3.6 `core/approval/store.py`

| Method | Behavior |
|--------|---------|
| `create_request` | Creates; raises `ValueError` on duplicate `approval_id` |
| `record_decision` | Overwrites status + stores decision in metadata; raises `KeyError` for unknown IDs; no guard against re-deciding |
| `list_pending` | Returns PENDING requests sorted by `requested_at` |
| `save_json` / `load_json` | JSON persistence; round-trip stable |

---

## 4. S12 canonical architecture decision

**Location:** `tests/governance/` (new) and `tests/approval/test_transitions.py` (new)

Justification:
- Policy engine tests belong in `tests/governance/` — the canonical location parallel to `core/governance/`
- Approval transition tests extend `tests/approval/` — existing location
- No new production code is added — S12 is purely a test-catalog phase
- All tests are read-only with respect to the canonical trace/audit/execution stack
- Tests operate on in-memory stores and isolated `tmp_path` fixtures only

**Not production code, not a second implementation, not a new module.**

---

## 5. What S12 will build

| Component | What it does |
|-----------|-------------|
| `tests/governance/__init__.py` | Makes `tests/governance` a proper test package |
| `tests/governance/test_policy_catalog.py` | 57 tests covering all 9 matching conditions (parametrized), all 3 effects, priority ordering, effect-weight tiebreak, multi-rule resolution, compound rules, JSON loading, `build_execution_context` field mapping, model validation |
| `tests/approval/test_transitions.py` | 24 tests covering all 4 terminal transitions, ordering, duplicate/unknown guards, comment/rating/metadata preservation, persistence round-trip |

---

## 6. Explicit non-goals for S12

- No new production code in `core/`
- No new CLI commands
- No changes to `PolicyEngine`, `PolicyRegistry`, or `ApprovalStore`
- No changes to `ApprovalPolicy` (legacy wrapper — untouched)
- No CI gate configuration (that is S13+)
