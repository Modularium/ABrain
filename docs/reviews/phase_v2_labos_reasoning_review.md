# Phase V2 — ABrain Domain Reasoning for LabOS (V1)

**Branch:** `codex/phase_v2_labos_reasoning`
**Date:** 2026-04-20
**Scope:** Adds a deterministic, input-driven **domain-reasoning
layer** at `core/reasoning/labos/` that interprets a LabOS context
snapshot and emits structured **Response Shape V2** recommendations.
ABrain plans; it never executes.  Five explicit use cases, three
invariants enforced at a single chokepoint, all surfaced through
`services/core.py` entry points in the existing control plane —
no parallel architecture.

---

## 1. Roadmap position

ABrain V2 opens the *domain-reasoning* boundary required by the
canonical flow:

```
Smolit-AI-Assistant → ABrain (Domain Reasoning) → LabOS MCP → LabOS API/DB
```

Prior ABrain layers covered Decision → Governance → Approval →
Execution → Audit → Orchestration on ABrain's own action universe.
This turn adds the **first external-system reasoner**: ABrain
receives a LabOS context snapshot from the caller and returns a
structured recommendation surface.  It does **not** call LabOS, does
**not** invent tool names, and **respects** the supplied LabOS
action catalogue, approval flags and safety context.

---

## 2. Idempotency check

- `grep -r "labos" core/ services/ interfaces/` before this turn —
  zero hits.
- No pre-existing domain-reasoning module; no parallel
  `services/domain_reasoning/` tree.
- `services/core.py` already owned `get_routing_models` with an
  `{"error": ..., "detail": ...}` envelope — we reuse that pattern
  verbatim for the new `get_labos_*` entry points.
- No existing pydantic models under `core/reasoning/`.

Consequence: fully additive.  One new `core/reasoning/labos/`
package, one append to `services/core.py`, one new test tree under
`tests/reasoning/labos/`.

---

## 3. Design (as-built)

### 3.1 Package layout (`core/reasoning/labos/`)

| Module | Role |
|---|---|
| `schemas.py` | Input (`LabOsContext`, `LabOsReactor`, `LabOsIncident`, `LabOsMaintenanceItem`, `LabOsScheduleEntry`, `LabOsCommand`, `LabOsSafetyAlert`, `LabOsActionCatalogEntry`) + output (`PrioritizedEntity`, `RecommendedAction`, `RecommendedCheck`, `DeferredAction`, `DomainReasoningResponse`) models.  All `extra="forbid"`. |
| `context_normalizer.py` | Pure, deterministic normaliser — computes per-reactor `ReactorHealthView` with escalation rules: declared LabOS status is authoritative and never downgraded; critical incident / safety alert / overdue maintenance can escalate but not demote. |
| `priority_engine.py` | Bucket + score + stable-sort prioritisation.  Base score per bucket (CRITICAL 100 / HIGH 80 / MEDIUM 60 / LOW 40 / NOMINAL 10), deterministic bumps (+5 critical incident / safety alert, +3 overdue maintenance, +3 blocked schedule). |
| `recommendation_engine.py` | `RecommendationBundle` + `build_action()` — the **single mandatory chokepoint** through which every action emission flows.  Enforces the three invariants (see §5). |
| `usecases.py` | Five reasoners, each returns a fully populated `DomainReasoningResponse`.  No direct action emission — everything goes through `build_action`. |
| `__init__.py` | Public exports. |

### 3.2 The five reasoners

| Reasoning mode | What it surfaces | Emits actions? |
|---|---|---|
| `labos_reactor_daily_overview` | Ranked reactor focus list (attention + nominal); `open_reactor_detail` for CRITICAL/HIGH reactors. | ✅ (diagnostic, opt-in on unsafe targets) |
| `labos_incident_review` | Open-incident priority list; `acknowledge_critical_incident` (→ approval) or `acknowledge_incident` (→ recommend). | ✅ |
| `labos_maintenance_suggestions` | Overdue + due-soon maintenance; `run_calibration` / `run_maintenance` (→ approval bucket per catalog flag). | ✅ |
| `labos_schedule_runtime_review` | Failing + blocked schedules; `pause_schedule` (≥3 consecutive failures) or `investigate_schedule`. | ✅ |
| `labos_cross_domain_overview` | Combined operator focus list across all four signals; pure prioritisation — by design emits **no** actions. | ❌ |

### 3.3 Service surface (`services/core.py`)

Appended at the tail — mirrors the existing `get_routing_models`
envelope pattern:

```python
_LABOS_REASONING_MODES = (
    "reactor_daily_overview",
    "incident_review",
    "maintenance_suggestions",
    "schedule_runtime_review",
    "cross_domain_overview",
)

def _run_labos_reasoner(mode, context):
    # → {"error": "invalid_reasoning_mode", "detail": ...}
    # → {"error": "invalid_context", "detail": exc.errors()}
    # → DomainReasoningResponse.model_dump(mode="json")
    ...

def get_labos_reactor_daily_overview(context=None): ...
def get_labos_incident_review(context=None): ...
def get_labos_maintenance_suggestions(context=None): ...
def get_labos_schedule_runtime_review(context=None): ...
def get_labos_cross_domain_overview(context=None): ...
```

Each entry point is a thin delegate of
`core/reasoning/labos/usecases.py` with shared validation + error
envelope.  Any future CLI / HTTP / MCP surface layers forward
without re-implementing.

### 3.4 Non-changes

- `core/decision/`, `core/governance/`, `core/execution/`,
  `core/audit/`, `core/orchestration/` — untouched.  Reasoning
  is a pre-pipeline input producer, not a pipeline extension.
- `api_gateway/`, `interfaces/mcp/`, `scripts/abrain_control.py`,
  `frontend/` — untouched this turn.  Surfaces can be added
  incrementally; backend is the source of truth.
- No new dependency — pydantic v2 + stdlib only.
- No new store / schema / migration.

---

## 4. Public-surface effect

**Additive, caller-driven.**  No existing entry point changed
behaviour; five new entry points added on `services/core.py`.

Caller example (Smolit-AI-Assistant or any caller with a LabOS
snapshot):

```python
from services.core import get_labos_reactor_daily_overview

snapshot = mcp.labos.reactor_daily_overview()   # external
response = get_labos_reactor_daily_overview(snapshot)

# response is a plain dict with Response Shape V2 keys:
#   reasoning_mode, summary, highlights,
#   prioritized_entities, recommended_actions, recommended_checks,
#   approval_required_actions, blocked_or_deferred_actions,
#   used_context_sections, trace_metadata
```

Error envelope on bad input:

```python
>>> get_labos_reactor_daily_overview({"incidents": [{"bogus": 1}]})
{"error": "invalid_context", "detail": [...pydantic errors...]}
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| `no_invented_actions` — actions missing from supplied `action_catalog` surface as `DeferredAction` with `MISSING_ACTION_CATALOG_ENTRY`, never as `RecommendedAction`. | ✅ — enforced in `build_action` as the first check; pinned by tests. |
| `respects_approval` — catalog entries with `requires_approval=True` route into `approval_required_actions`, never into `recommended_actions`. | ✅ — enforced in `build_action`; pinned by tests. |
| `respects_safety_context` — targets with a safety alert or an `offline` reactor defer their actions, except opt-in diagnostic intents (`allow_on_unsafe_target=True`, e.g. `open_reactor_detail`). | ✅ — enforced in `build_action`; pinned by tests. |
| Decision → Governance → Approval → Execution → Audit → Orchestration unchanged | ✅ — reasoning is pre-pipeline; it does not execute anything. |
| Input-driven boundary — ABrain never calls LabOS | ✅ — no IO in `core/reasoning/labos/`; context must be supplied by caller. |
| Single `services/core.py` surface for cross-layer business callers | ✅ — five `get_labos_*` delegates mirror existing `get_routing_models` pattern. |
| Stable-schema emission (all Response Shape V2 keys always present) | ✅ — `DomainReasoningResponse` default-constructs every list; pinned by shared-invariant test. |
| Deterministic on identical input | ✅ — pure functions, stable sort; pinned by shared-invariant test. |
| `None`-signal honesty rule preserved | ✅ — no defaults injected where input is silent. |
| No parallel architecture introduced | ✅ — lives alongside existing `core/*/` layers, not outside them. |

---

## 6. Artifacts

| File | Change |
|---|---|
| `core/reasoning/__init__.py` | new — package docstring pinning V2 boundary |
| `core/reasoning/labos/__init__.py` | new — public exports |
| `core/reasoning/labos/schemas.py` | new — input + output pydantic models |
| `core/reasoning/labos/context_normalizer.py` | new — `normalize_labos_context` + `ReactorHealthView` |
| `core/reasoning/labos/priority_engine.py` | new — `prioritize` + deterministic bucket/score rules |
| `core/reasoning/labos/recommendation_engine.py` | new — `RecommendationBundle` + `build_action` chokepoint |
| `core/reasoning/labos/usecases.py` | new — five reasoners + `_assemble` helper |
| `services/core.py` | append — `_run_labos_reasoner` + five `get_labos_*` entry points |
| `tests/reasoning/__init__.py` | new — namespace marker |
| `tests/reasoning/labos/__init__.py` | new — namespace marker |
| `tests/reasoning/labos/test_context_normalizer.py` | new — 12 tests |
| `tests/reasoning/labos/test_priority_engine.py` | new — 7 tests |
| `tests/reasoning/labos/test_recommendation_engine.py` | new — 6 tests |
| `tests/reasoning/labos/test_usecases.py` | new — 36 tests |
| `README.md` | `+` section `🧠 ABrain V2 — Domain Reasoning for external systems` |
| `docs/reviews/phase_v2_labos_reasoning_review.md` | this doc |

No change to decision engine, governance, approvals, execution,
audit, orchestration, routing catalog, learning, MCP surface, HTTP
API, or CLI.

---

## 7. Test coverage

61 new tests across four files (all deterministic, all `unit`):

- **`test_context_normalizer.py` (12)** — nominal / warning /
  offline / incident-declared reactors; escalation by critical
  incident, overdue maintenance, safety alert; open-vs-closed
  incident filtering; separating critical / warning / info; overdue
  vs due-soon maintenance; failed vs blocked schedules;
  `used_context_sections` population; `action_catalog` uniqueness
  validator.
- **`test_priority_engine.py` (7)** — bucket assignment (critical
  incident > warning; overdue high-risk maintenance → critical;
  schedule-failure threshold 3 → HIGH, <3 → MEDIUM); determinism
  on repeated calls; nominal reactors hidden by default + opt-in
  `include_nominal_reactors`; `priority_reason` is always a
  non-empty string.
- **`test_recommendation_engine.py` (6)** — the three invariants,
  plus the `allow_on_unsafe_target=True` override for diagnostic
  intents.
- **`test_usecases.py` (36)** — per-use-case assertions (5
  classes) + parametrised shared invariants (Response Shape V2 key
  set, determinism, catalog containment of every emitted action,
  invalid-context error envelope shape, unknown reasoning mode
  error envelope).

---

## 8. Test gates

- Focused:
  `tests/reasoning/labos/` — **61 passed in 1.02 s**.
- Full suite
  (`.venv/bin/python -m pytest -o python_files='test_*.py' tests/ -q`)
  — **1992 passed, 1 skipped, 6 warnings in 31.10 s**
  (+61 from the 1931-passed baseline).
- `py_compile core/reasoning/labos/*.py services/core.py` — clean.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (V2 domain reasoning for LabOS, V1 subset) | ✅ |
| Idempotency rule honoured (no duplicate package / shape) | ✅ |
| No parallel architecture introduced | ✅ — lives in `core/reasoning/`, surfaces via `services/core.py` |
| Canonical control-plane reinforced | ✅ — five `get_labos_*` mirror `get_routing_models` |
| No business logic bypassing `build_action` | ✅ — use cases only call the chokepoint |
| No Schatten-Wahrheit (reasoner reads normaliser, normaliser reads input only) | ✅ |
| `None`-signal honesty rule preserved | ✅ |
| Stable-schema emission preserved | ✅ |
| Error envelope pattern consistent with `get_routing_models` | ✅ |
| Three invariants pinned by tests (`no_invented_actions`, `respects_approval`, `respects_safety_context`) | ✅ |
| Deterministic reasoning pinned by test | ✅ |
| Reasoning suite green (+61) | ✅ |
| Full suite green (+61 net) | ✅ |
| Documentation consistent with prior phase reviews | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

ABrain V2 V1 is complete: five use cases, three invariants, one
caller-driven entry surface.  Remaining directions, none urgent
and none blocking on `main`:

1. **Surface parity** — CLI (`./scripts/abrain reasoning labos
   <mode>` reading a snapshot file), HTTP
   (`/control-plane/reasoning/labos/<mode>`) and MCP
   (`abrain.reason_labos_*`) tools can mirror `services/core.py`.
   All three are additive delegates; no new business logic.
2. **Additional V2 use cases** — e.g.
   `labos_energy_budget_review`, `labos_reactor_lineup_planning`
   — once the LabOS MCP snapshots for those signals stabilise
   upstream.
3. **Second external system** — whatever the next
   Smolit-AI-Assistant caller asks for can live next to
   `labos/` as a sibling package (`core/reasoning/<system>/`)
   reusing the same invariants + Response Shape V2 contract.

Recommendation: merge V1, then pick up surface parity in the next
session once a concrete caller (Smolit-AI-Assistant) needs one.
