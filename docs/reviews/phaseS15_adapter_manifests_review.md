# Phase S15 — Adapter Manifests (Phase 2, Step 1)

**Branch:** `codex/phaseS15-adapter-manifests`
**Date:** 2026-04-15
**Reviewer:** automated phase gate

---

## Goal

Open Phase 2 — "Kontrollierte Erweiterbarkeit" — with its first concrete
deliverable: a formal static governance declaration for each execution adapter.

Phase 2 tasks closed by this step:
- **Plugin-/Adapter-Manifest spezifizieren** — `AdapterManifest` is the single
  self-contained declaration of everything statically known about an adapter
  from a governance perspective.
- **Risk-Tiering pro Plugin/Adapter einführen** — `RiskTier` (LOW/MEDIUM/HIGH)
  is now assigned to every adapter class.
- **Capabilities formal beschreiben** — `AdapterManifest.capabilities` embeds
  `ExecutionCapabilities` so consumers have a single reference point.

All changes are **additive** — no existing production logic was modified.

---

## What changed

### `core/execution/adapters/manifest.py` — new file

```
RiskTier (StrEnum)
    LOW    — internal tool dispatch, no network (AdminBot)
    MEDIUM — controlled workflow-engine calls (Flowise, n8n)
    HIGH   — local process / code-execution services (ClaudeCode, Codex, OpenHands)

AdapterManifest (Pydantic BaseModel, extra="forbid")
    adapter_name:             str
    description:              str
    capabilities:             ExecutionCapabilities  (same object as adapter.capabilities)
    risk_tier:                RiskTier
    required_metadata_keys:   list[str]  (default [])
    optional_metadata_keys:   list[str]  (default [])
    recommended_policy_scope: str | None (default None)
```

### `core/execution/adapters/base.py`

Added `manifest: AdapterManifest` class attribute with a safe default (base,
risk_tier=LOW).  Imports `AdapterManifest` and `RiskTier` from the new module.

### Each concrete adapter — `manifest` class attribute added

| Adapter | risk_tier | required_metadata_keys | recommended_policy_scope |
|---------|-----------|------------------------|--------------------------|
| AdminBot | LOW | `[]` | `system_ops` |
| OpenHands | HIGH | `[]` | `code_execution` |
| ClaudeCode | HIGH | `[]` | `code_execution` |
| Codex | HIGH | `[]` | `code_execution` |
| Flowise | MEDIUM | `["base_url", "chatflow_id"]` | `workflow_execution` |
| n8n | MEDIUM | `["webhook_url"]` | `workflow_execution` |

Notes:
- AdminBot has no required keys because tool dispatch is fully internal.
- OpenHands, ClaudeCode, Codex have no required keys because all have safe
  defaults (localhost endpoint / default CLI names).
- Flowise and n8n have required keys encoding the canonical contract already
  verified in S13.

### `core/execution/adapters/registry.py`

Added `get_manifest_for(execution_kind, source_type) -> AdapterManifest | None`
alongside the existing `get_capabilities_for()`.

### `core/execution/adapters/__init__.py`

`AdapterManifest` and `RiskTier` added to imports and `__all__`.

### `.github/workflows/core-ci.yml`

`core/execution/adapters/manifest.py` added to the `py_compile` list.

### `tests/execution/test_adapter_manifests.py` — 50 new tests

| Section | Tests | What's verified |
|---------|-------|-----------------|
| 1. AdapterManifest model | 6 | Required fields, defaults, full population, extra="forbid", missing field raises, JSON round-trip |
| 2. RiskTier enum | 3 | String values, exhaustiveness {low,medium,high}, all tiers present |
| 3. Base adapter manifest | 3 | Has manifest attribute, adapter_name='base', non-empty description |
| 4. Per-adapter name/tier/scope | 6+6+6 | Name, tier, scope per adapter; non-empty descriptions; capabilities consistency |
| 5. Required metadata keys | 8 | Flowise requires base_url+chatflow_id; n8n requires webhook_url; others have no required keys; alternatives are optional |
| 6. Registry get_manifest_for() | 8 | All 6 adapters resolved correctly; unknown pair returns None |
| 7. Risk-tier invariants | 5 | Code-execution=HIGH, workflow=MEDIUM, tool-dispatch=LOW; all scopes non-None; scopes from known set |

---

## Architecture check

### 1. No existing production logic modified

`execute()`, `validate()`, `capabilities`, `ExecutionAdapterRegistry.resolve()`,
`get_capabilities_for()` — all unmodified.  The manifest is purely additive.

### 2. No duplication of business logic

`manifest.capabilities` is the same `ExecutionCapabilities` instance as the
adapter's standalone `capabilities` attribute — no divergence possible.
Tests assert this explicitly.

### 3. Single canonical source of truth

`AdapterManifest` is the single governance declaration.  The registry exposes
it through `get_manifest_for()`.  No second registry or parallel governance
world.

### 4. Backward compatibility

All callers of `adapter.capabilities` and `registry.get_capabilities_for()`
continue to work unchanged.  `get_manifest_for()` is a new, independent method.

### 5. CI gate for new module

`core/execution/adapters/manifest.py` is now syntax-checked on every PR to main.

---

## Phase 2 progress

| Task | Status |
|------|--------|
| Plugin-/Adapter-Manifest spezifizieren | **DONE (S15)** |
| Capabilities formal beschreiben | **DONE (S15)** |
| Risk-Tiering pro Plugin/Adapter | **DONE (S15)** |
| jedem Tool/Adapter Policy-Regeln zuordnen | open (S16) |
| Eingabe-/Ausgabe-Schemas erzwingen | open |
| Output-Validatoren für kritische Aktionen | open |
| Sandboxing-/Isolation-Regeln | open |
| Kosten- und Latenzbudgets pro Adapter | open |
| Audit-Events für jeden Tool-Call | open |
| Security-Tests gegen unsichere Plugins | open |

---

## Test counts

| Suite | Before S15 | New in S15 | Total |
|-------|-----------|-----------|-------|
| `tests/execution/test_adapter_manifests.py` | 0 | 50 | 50 |
| `tests/execution/test_execution_result_contracts.py` | 45 | 0 | 45 |

**Full suite:** 569 passed, 1 skipped, 0 failures

---

## Merge-readiness

| Check | Status |
|-------|--------|
| No existing production logic modified | PASS |
| No parallel governance implementation | PASS |
| `manifest.capabilities == adapter.capabilities` verified in tests | PASS |
| All 6 concrete adapters have manifests | PASS |
| Risk tiers correct (LOW/MEDIUM/HIGH distribution verified) | PASS |
| Required metadata keys match adapter validate() requirements | PASS |
| Registry get_manifest_for() resolves all known pairs | PASS |
| manifest.py added to CI py_compile | PASS |
| All 50 new tests green | PASS |
| Full suite green (569 passed, 1 skipped) | PASS |
| Scope matches Phase 2 roadmap | PASS |

**Merge-ready: YES**
