# Phase S16 — Policy Bindings per Adapter (Phase 2, Step 2)

**Branch:** `codex/phaseS16-policy-bindings`
**Date:** 2026-04-15
**Reviewer:** automated phase gate

---

## Goal

Close the Phase 2 task *"jedem Tool/Adapter Policy-Regeln zuordnen"* — assign
canonical governance policy rules to each execution adapter.

S15 established that every adapter has a `risk_tier` and a
`recommended_policy_scope`.  S16 makes that governance intent operational by
deriving concrete `PolicyRule` objects that operators can load directly into a
`PolicyRegistry`.

All changes are **additive** — no existing production logic was modified.

---

## What changed

### `core/execution/adapters/policy_bindings.py` — new file

Two public functions:

#### `build_default_rules_for_manifest(manifest) -> list[PolicyRule]`

Pure derivation from `manifest.risk_tier` and `manifest.adapter_name`:

| Risk tier | Rules generated |
|-----------|----------------|
| LOW | One `effect=allow` rule bound to `source_type=adapter_name` |
| MEDIUM | Two rules: `require_approval` when `external_side_effect=True` (priority 10) + baseline `allow` (priority 0) |
| HIGH | One `require_approval` rule for all executions |

#### `get_all_adapter_default_rules() -> list[PolicyRule]`

Aggregates rules for all 6 canonical adapters in stable order.
Total: **8 rules** (1 + 2 + 2 + 1 + 1 + 1).

| Adapter | Tier | Rules | Effects |
|---------|------|-------|---------|
| AdminBot | LOW | 1 | allow |
| OpenHands | HIGH | 1 | require_approval |
| ClaudeCode | HIGH | 1 | require_approval |
| Codex | HIGH | 1 | require_approval |
| Flowise | MEDIUM | 2 | allow + require_approval (side-effect) |
| n8n | MEDIUM | 2 | allow + require_approval (side-effect) |

The result is ready to pass directly to `PolicyRegistry(rules=...)`.

### `core/execution/adapters/__init__.py`

`build_default_rules_for_manifest` and `get_all_adapter_default_rules` added
to imports and `__all__`.

### `.github/workflows/core-ci.yml`

`core/execution/adapters/policy_bindings.py` added to the `py_compile` list.

### `tests/execution/test_adapter_policy_bindings.py` — 38 new tests

| Section | Tests | What's verified |
|---------|-------|-----------------|
| 1a. LOW tier | 5 | 1 rule, allow, source_type, no side-effect constraint, description |
| 1b. MEDIUM tier | 6 | 2 rules, approval on side-effect, allow baseline, priority ordering, source_type, descriptions |
| 1c. HIGH tier | 4 | 1 rule, require_approval, source_type, description |
| 2. Per-adapter | 6 | Each of the 6 concrete adapters generates the correct rules |
| 3. Aggregation | 7 | List type, count=8, unique ids, all source_types covered, instances, descriptions, effects |
| 4. Registry integration | 6 | Rules load into PolicyRegistry; AdminBot→allow; ClaudeCode→require_approval; Flowise without/with side-effect; no match for unknown |
| 5. Invariants | 4 | HIGH=never allow; LOW=only allow; MEDIUM=both effects; all rules have source_type |

---

## Architecture check

### 1. No existing production logic modified

`PolicyEngine`, `PolicyRegistry`, `PolicyRule`, `PolicyEvaluationContext`,
`AdapterManifest` — all unmodified.  `policy_bindings.py` is a pure builder.

### 2. No second registry or parallel governance world

Callers decide whether and how to load the rules.  No singleton, no
auto-registration, no side effects at import time (adapter classes are
imported lazily inside `get_all_adapter_default_rules()`).

### 3. Deriving from manifests, not duplicating

Rule source_types come from `manifest.adapter_name`, which matches
`AgentSourceType.value`.  When manifests change (e.g. a new adapter is added),
the builder produces updated rules automatically.

### 4. `PolicyRule` validation enforced

All generated rules pass through `PolicyRule` Pydantic validation
(`extra="forbid"`, `id` length, description length).  No invalid rules can
be produced.

### 5. Registry integration tested end-to-end

Section 4 tests load the generated rules into a live `PolicyRegistry` and
assert correct `get_applicable_policies()` results for representative
contexts — this is the real integration path operators will use.

---

## Phase 2 progress

| Task | Status |
|------|--------|
| Plugin-/Adapter-Manifest spezifizieren | DONE (S15) |
| Capabilities formal beschreiben | DONE (S15) |
| Risk-Tiering pro Plugin/Adapter | DONE (S15) |
| jedem Tool/Adapter Policy-Regeln zuordnen | **DONE (S16)** |
| Eingabe-/Ausgabe-Schemas erzwingen | open |
| Output-Validatoren für kritische Aktionen | open |
| Sandboxing-/Isolation-Regeln | open |
| Kosten- und Latenzbudgets pro Adapter | open |
| Audit-Events für jeden Tool-Call | open |
| Security-Tests gegen unsichere Plugins | open |

---

## Test counts

| Suite | Before S16 | New in S16 | Total |
|-------|-----------|-----------|-------|
| `tests/execution/test_adapter_policy_bindings.py` | 0 | 38 | 38 |
| `tests/execution/test_adapter_manifests.py` | 50 | 0 | 50 |
| `tests/execution/test_execution_result_contracts.py` | 45 | 0 | 45 |

**Full suite:** 607 passed, 1 skipped, 0 failures

---

## Merge-readiness

| Check | Status |
|-------|--------|
| No existing production logic modified | PASS |
| No parallel governance world | PASS |
| Pure derivation from manifest (no hard-coded duplication) | PASS |
| LOW → allow, MEDIUM → allow + conditional approval, HIGH → require_approval | PASS |
| 8 rules total, unique ids, all 6 source_types covered | PASS |
| PolicyRegistry integration tested end-to-end | PASS |
| policy_bindings.py added to CI py_compile | PASS |
| All 38 new tests green | PASS |
| Full suite green (607 passed, 1 skipped) | PASS |
| Scope matches Phase 2 roadmap | PASS |

**Merge-ready: YES**
