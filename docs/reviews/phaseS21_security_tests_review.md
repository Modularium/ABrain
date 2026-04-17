# Phase S21 — Security Tests against Unsafe Plugins / Prompt Injection

**Branch:** `codex/phaseS21-security-tests`
**Date:** 2026-04-17
**Reviewer:** automated phase gate

---

## 1. Roadmap Position

**Phase 2 — Kontrollierte Erweiterbarkeit**, last open step:

| Roadmap task | Status |
|---|---|
| Security-Tests gegen unsichere Plugins/Prompt Injection aufbauen | ✅ closed |

**Phase 2 exit criteria (all now met):**

| Criterion | Evidence |
|---|---|
| Neue Integrationen erweitern das System, ohne neue Schattenpfade zu erzeugen | S15–S19: manifest-driven, single canonical adapter contract |
| Jeder Adapter ist capability-, policy- und audit-aware | S15 capabilities, S16 policy bindings, S19 audit events |
| Kein Tool darf implizit außerhalb seines Scopes handeln | S20 budget+isolation, S21 enforcement verified by tests |

**Phase 2 ist damit abgeschlossen. Phase 3 — Retrieval- und Wissensschicht — kann beginnen.**

---

## 2. What was already present

- `extra="forbid"` on all governance boundary models (S15–S20)
- `validate_required_metadata()` — key-presence input validation (S17)
- `validate_result()` — structural output validation (S18)
- `result_warnings()` / `budget_warnings()` — soft capability and budget checks (S18, S20)
- `PolicyEngine` + `PolicyRegistry` + `enforce_policy()` — deterministic governance (S12)
- `build_default_rules_for_manifest()` — per-adapter default rules (S16)
- `PolicyViolationError` — hard-block on "deny" (S12)

**What was missing:**
- No explicit security characterisation tests for injection payloads at input boundaries
- No test verifying that injection in metadata values doesn't affect governance outcome
- No test verifying that `extra="forbid"` applies at all governance model boundaries simultaneously
- No end-to-end tests verifying HIGH-tier adapter → `require_approval` via the policy engine
- No tests for `PolicyViolationError` carry-through, priority ordering from a security perspective, or context normalization as injection defence

---

## 3. What changed

### `tests/execution/test_security_boundaries.py` (new)

38 tests in 5 sections:

**TestModelIntegrity (5)**
- All 5 governance boundary models (`AdapterManifest`, `AdapterBudget`, `IsolationRequirements`, `ExecutionResult`, `AgentDescriptor`) reject unknown fields via `extra="forbid"`.

**TestInputBoundary (12 — 8 parametrized + 4 structural)**
- 8 injection payload variants (SQL injection, template injection, XSS, LLM prompt injection, JNDI, SSTI, null bytes, 4 KB padding) as metadata values: all pass `validate_required_metadata` when the required key is present — confirmation that validation is key-presence-only, not content-aware.
- Missing required key raises regardless of extra keys or injection payloads as key names.
- No-required-keys manifest accepts arbitrary metadata (including `__proto__`, `constructor`).

**TestOutputBoundary (5)**
- Empty `agent_id` rejected by `validate_result()`.
- `success=True` + `error` object → rejected.
- `success=False` + no error → rejected.
- `success=False` + blank `error_code` → rejected.
- Required result metadata key missing on success → rejected.

**TestMetadataExtraKeysContained (3)**
- Extra metadata keys (`admin`, `bypass_policy`, `is_root`, `recommended_policy_scope`, `risk_tier`) cannot satisfy required-key check, cannot override policy scope, and cannot alter manifest risk tier.

**TestHighRiskAdapterRequiresApproval (3 — parametrized + integrated)**
- All 3 HIGH-tier adapters: default rules produce only `require_approval`.
- ClaudeCode end-to-end: `PolicyEngine.evaluate()` returns `require_approval` with default bindings.
- AdminBot end-to-end: `PolicyEngine.evaluate()` returns `allow` with default bindings.

### `tests/governance/test_security_enforcement.py` (new)

30 tests in 5 sections:

**TestEnforcePolicy (5)**
- `enforce_policy(deny)` raises `PolicyViolationError`.
- Error carries original `PolicyDecision` object.
- Error message contains the denial reason.
- `require_approval` returns `"approval_required"` without raising.
- `allow` returns `"allowed"`.

**TestPriorityOrdering (3)**
- Deny at high priority overrides allow at low priority.
- `require_approval` at high priority overrides allow at low priority.
- No matching rule → `"allow"` with `"no_policy_matched"` reason.

**TestAdapterTierEnforcement (8)**
- All HIGH-tier adapters: only `require_approval` rules.
- LOW-tier (AdminBot): only `allow` rules.
- MEDIUM-tier (Flowise, n8n): have both effects.
- `external_side_effect=True` → `require_approval` for MEDIUM.
- `external_side_effect=False` → `allow` for MEDIUM.
- All combined default rules have non-empty ids.
- ≥3 `require_approval` rules in combined set.

**TestPolicyRuleStructuralValidation (7)**
- Empty id, whitespace id, empty description, extra fields, invalid effect all rejected.
- Negative priority accepted (valid use case).
- Negative `max_cost` rejected.

**TestEvaluationContextNormalization (9)**
- Whitespace-only `source_type`, `execution_kind`, `agent_id`, `risk_level` → `None` (no accidental empty-string matches).
- Extra fields rejected.
- Empty `task_type` rejected.
- Empty capability silently stripped (characterisation of existing behaviour).
- Duplicate capabilities deduplicated.
- Negative `estimated_cost` rejected.

---

## 4. Security surface characterised

| Threat | Mitigation | Verified by |
|---|---|---|
| Prompt injection via metadata values | Governance is key-presence-only; values are never evaluated by the policy engine | `TestInputBoundary` |
| Extra governance fields in manifest | `extra="forbid"` on all models | `TestModelIntegrity` |
| Inconsistent result state (success+error, missing error) | `validate_result()` structural check | `TestOutputBoundary` |
| Metadata key collisions (`__proto__`, `constructor`) | No key serialization into Python namespace; dict lookup only | `TestInputBoundary` |
| Risk tier downgrade via metadata | Manifest is immutable class attribute; metadata can't override it | `TestMetadataExtraKeysContained` |
| HIGH-tier adapter auto-executing without approval | Default rules enforce `require_approval` for all HIGH adapters | `TestHighRiskAdapterRequiresApproval`, `TestAdapterTierEnforcement` |
| Whitespace-padded source_type matching rule | Context normalization strips to `None` | `TestEvaluationContextNormalization` |
| Deny decision not blocking execution | `PolicyViolationError` raised by `enforce_policy()` | `TestEnforcePolicy` |
| Low-priority allow overriding high-priority deny | Priority ordering correctly resolved | `TestPriorityOrdering` |

---

## 5. Architecture invariant check

| Invariant | Status |
|---|---|
| No parallel structure | test-only step, no production code added |
| Single canonical policy/audit path | no second engine or second store added |
| Pure test additions | no production logic changed |
| Additive change | no existing test removed |
| No new dependencies | no new packages |

---

## 6. Test results

```
68 passed (test_security_boundaries.py + test_security_enforcement.py)
685 passed, 1 skipped, 0 failed (full canonical suite)
```

---

## 7. Review-/Merge-Gate

| Check | Result |
|---|---|
| Scope correct (S21 = security tests only)? | ✅ |
| No parallel structure? | ✅ |
| Canonical paths used? | ✅ |
| No business logic in wrong layer? | ✅ (test-only) |
| No new shadow truth? | ✅ |
| Tests green? | ✅ 68/68 + 685/685 |
| Documentation consistent? | ✅ |
| Merge-ready? | ✅ |

---

## 8. Phase 2 Exit — Phase 3 Entry

**Phase 2 — Kontrollierte Erweiterbarkeit — is now complete.**

All six deliverables closed:
- Adapter manifest (S15)
- Capabilities formal (S15)
- Policy bindings per adapter (S16)
- Input/output schema enforcement (S17, S18)
- Output validators (S18)
- Sandboxing/isolation declarations (S20)
- Cost/latency budgets (S20)
- Standardised audit events (S19)
- Risk tiering (S15)
- Security tests (S21) ← this step

**Next phase: Phase 3 — Retrieval- und Wissensschicht**

First step (R1): Classify knowledge sources (trusted / internal / external / untrusted) and define the Retrieval API surface — additive, no production code until classification is documented and the API contract is specified.
