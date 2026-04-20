# Phase V2 — RobotOps / Module Reasoning V1

**Branch:** `codex/phase_v2_robotops_reasoning`
**Date:** 2026-04-20
**Scope:** Extends the existing LabOS reasoner in `core/reasoning/labos/`
with five new use cases that treat LabOS modules / autonomous units
(RobotOps V1) as first-class reasoning subjects.  No new parallel
architecture, no new execution or safety engine — ABrain continues
to reason over caller-supplied snapshots and delegate execution to
LabOS.

---

## 1. Roadmap position

Builds on the V2 reasoner and surface-parity work:

| Turn | Commit | Layer |
|---|---|---|
| V2 reasoning V1 | `878fce39` | `core/reasoning/labos/*` + five ReactorOps use cases |
| V2 surface parity | `79ca5940` | CLI + HTTP + MCP over `run_labos_reasoning` |
| **V2 RobotOps V1 (this turn)** | — | `LabOsModule` + five module use cases + surface parity |

After this turn ABrain can reason about reactor modules, hydro / sampling
/ dosing / vision modules, workshop machines and (later) mobile robots
under a single RobotOps abstraction.  LabOS remains source of truth;
ABrain remains pure interpretation.

---

## 2. Idempotency check

Pre-turn survey:

- `grep 'LabOsModule\|module_daily\|robotops' core/reasoning/ interfaces/`
  → zero hits.  No shadow module reasoning existed.
- `run_labos_reasoning` already dispatches by string mode → extending
  the dispatcher needed only new entries in one tuple + one dict.
- Surface factories (HTTP, MCP) already iterate over the mode list
  they receive → they absorbed the new modes with one description
  table extension each.  No second dispatcher, no second factory.
- `TOOLS` allow-list test pinned 13 entries; extended in lock-step
  to 18.

Consequence: fully additive.  Zero new modules under
`core/reasoning/`; zero new packages under `interfaces/mcp/`; zero
new request/response shapes.

---

## 3. Design (as-built)

### 3.1 Domain schemas (`core/reasoning/labos/schemas.py`)

Three new pydantic models and three new enums:

- `ModuleAutonomyLevel` — `unknown / manual / assisted /
  semi_autonomous / autonomous`.  Mirrors the LabOS RobotOps V1
  taxonomy.  ABrain never *escalates* autonomy itself; the level is
  input only.
- `CapabilityStatus` — `ok / degraded / missing / unknown`.
- `ModuleDependencyKind` — `upstream / downstream / coupled`.
- `LabOsModuleCapability` — per-capability record with `critical`
  flag + `risk_level`.  ABrain treats a capability as *critical*
  when `critical=True` OR `risk_level ∈ {high, critical}` — this
  rule is applied in one place, in the normalizer.
- `LabOsModule` — the RobotOps unit itself: `module_id`,
  `module_class` (free-form string so upstream can add classes
  without an ABrain release), normalised `HealthStatus`,
  `autonomy_level`, `offline` / `disabled` / `maintenance_mode`
  flags, capability list, optional `linked_reactor_id` /
  `linked_asset_id` / `linked_device_id`, attention reasons.
- `LabOsModuleDependency` — a declared edge between two modules
  with `blocked` flag + optional detail.

`LabOsContext` gains two new optional sections — `modules` and
`module_dependencies` — both defaulting to `[]`.  Existing
ReactorOps callers are unaffected.

### 3.2 Normaliser (`core/reasoning/labos/context_normalizer.py`)

New derived structures on `NormalizedLabOsContext`:

- `modules_by_id`, `modules_by_class`
- `module_health` — dict of `ModuleHealthView` keyed by module_id
- `module_dependencies`, `blocked_dependencies`

`ModuleHealthView` follows `ReactorHealthView`'s template and adds
RobotOps signals: `missing_critical_capabilities`,
`degraded_critical_capabilities`, `has_blocked_dependency`.

Escalation rule `_escalate_module_status` is a deliberate cousin of
`_escalate_from_signals` (reactors), but with module-specific
signals ranked in explicit order:

1. `offline` → `OFFLINE`
2. `safety_alert` OR `critical incident` → `INCIDENT`
3. `missing critical capability` → `WARNING`
4. `warning incident` OR `overdue maintenance` → `WARNING`
5. `disabled` OR `maintenance_mode` OR `degraded critical capability` → `ATTENTION`

ABrain never *downgrades* a LabOS-declared status — promotion only.

Incident-to-module mapping is interpretation-only: a caller can tag
an incident with `metadata.module_id="…"` and the normaliser will
attribute it to that module.  No auto-correlation, no shadow
inference.

### 3.3 Priority engine (`core/reasoning/labos/priority_engine.py`)

- New `_module_candidate(view)` builds a `PrioritizedEntity` for
  one module with 11 possible contributing signals (offline,
  disabled, maintenance_mode, missing/degraded critical capability,
  incident, overdue maintenance, safety alert, blocked dependency,
  plus autonomy level as pure metadata).
- Score bumps extended so `module_critical_incident` lifts a
  module within its bucket exactly the way `critical_incident` does
  for an incident.
- `prioritize()` gains two new flags: `include_modules` (default
  `False`) and `include_nominal_modules` (default `False`).
  Reactor flags are untouched.  Mixed reactor+module ranking shares
  one plane.

### 3.4 Recommendation engine (`core/reasoning/labos/recommendation_engine.py`)

`_target_is_unsafe` extended to understand modules:

- module marked `offline` → unsafe
- module with `effective_status == INCIDENT` → unsafe
- any target with a safety alert keyed `("module", module_id)` →
  unsafe (already covered by the shared lookup)

Everything else still routes through `build_action`, so the three
invariants (`no_invented_actions`, `respects_approval`,
`respects_safety_context`) extend to modules for free.

### 3.5 Use cases (`core/reasoning/labos/usecases.py`)

Five new deterministic use cases, all using the existing
`_assemble` helper and emitting Response Shape V2 verbatim:

| Mode | Intent | Includes nominal? |
|---|---|---|
| `labos_module_daily_overview` | Focus list with attention / offline / nominal counts | Yes |
| `labos_module_incident_review` | Incident-state modules + inspect/acknowledge intents | No |
| `labos_module_coordination_review` | Blocked + impacted dependency edges | No |
| `labos_module_capability_risk_review` | Missing/degraded critical capabilities + autonomy-level trace | No |
| `labos_robotops_cross_domain_overview` | ReactorOps + RobotOps combined focus list | No |

Action catalog names the use cases *intend* but never invent:
`open_module_detail`, `inspect_module`,
`acknowledge_module_incident`, `inspect_module_dependency`,
`review_module_capabilities`.  Missing-catalog entries surface as
`DeferredAction`s via `build_action`, same as every other use case.

### 3.6 Service dispatcher (`services/core.py`)

- `LABOS_REASONING_MODES` extended from 5 → 10 modes.
- `reasoners` dict in `_run_labos_reasoner` extended.
- Five new `get_labos_module_*` / `get_labos_robotops_*` typed
  entry points for in-process Python callers.

### 3.7 Surfaces

- **CLI** (`scripts/abrain_control.py`): no code change — the
  `reasoning labos <mode>` subparser sources `choices` from
  `LABOS_REASONING_MODES` dynamically.
- **HTTP** (`api_gateway/main.py`):
  `_LABOS_REASONING_ENDPOINT_SUMMARIES` extended with five entries
  → `_register_labos_reasoning_endpoint` factory registers
  `POST /control-plane/reasoning/labos/{mode}` for each
  automatically.
- **MCP** (`interfaces/mcp/handlers/reasoning.py`):
  `_LABOS_REASONING_TOOL_DESCRIPTIONS` extended with five entries;
  five new handler classes created via the existing `type()`-based
  `_make_handler_class` factory; `LABOS_REASONING_HANDLERS` tuple
  grows from 5 → 10; `__init__.py` / `__all__` updated.

No parallel surface code path.  Every new mode is reachable through
CLI, HTTP and MCP with identical Response Shape V2.

---

## 4. Public-surface effect

**Additive, opt-in use cases.**  Every existing mode, tool,
endpoint and CLI subcommand behaves exactly as before.

### CLI

```bash
./scripts/abrain reasoning labos module_daily_overview --input ctx.json --json
./scripts/abrain reasoning labos module_coordination_review --stdin
./scripts/abrain reasoning labos robotops_cross_domain_overview --input-json '{"modules":[]}'
```

### HTTP

```
POST /control-plane/reasoning/labos/module_daily_overview
POST /control-plane/reasoning/labos/module_incident_review
POST /control-plane/reasoning/labos/module_coordination_review
POST /control-plane/reasoning/labos/module_capability_risk_review
POST /control-plane/reasoning/labos/robotops_cross_domain_overview
```

All share the strict `LabOsReasoningRequest` body
(`extra="forbid"`), `agents:read` scope, `400` on invalid context,
`422` on unknown top-level keys.

### MCP

```
abrain.reason_labos_module_daily_overview
abrain.reason_labos_module_incident_review
abrain.reason_labos_module_coordination_review
abrain.reason_labos_module_capability_risk_review
abrain.reason_labos_robotops_cross_domain_overview
```

Strict input schema; `isError=true` on service error envelopes.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Single reasoning core | ✅ — all logic under `core/reasoning/labos/` |
| `services/core.py` sole entry point | ✅ — `run_labos_reasoning` is the one dispatcher |
| Response Shape V2 across all modes | ✅ — module modes return the same 10 keys |
| `no_invented_actions` | ✅ — enforced via `build_action` |
| `respects_approval` | ✅ — tested on `open_module_detail` |
| `respects_safety_context` | ✅ — offline/incident modules trigger SAFETY_CONTEXT deferrals |
| No shadow truth (ABrain does not fetch / execute / persist) | ✅ — reasoner reads snapshots only |
| LabOS as source of truth | ✅ — module classes/capabilities/dependencies come from the caller |
| No new execution / safety engine | ✅ — only reasoning |
| Deterministic ranking (stable ranks, no ML scoring) | ✅ — `_assign_ranks` unchanged |
| Surface parity (CLI + HTTP + MCP identical) | ✅ — single dispatcher under all three |
| Tool-list allow-list guard updated | ✅ — 13 → 18 tools |

---

## 6. Artifacts

| File | Change |
|---|---|
| `core/reasoning/labos/schemas.py` | +`ModuleAutonomyLevel`, +`CapabilityStatus`, +`ModuleDependencyKind`, +`LabOsModuleCapability`, +`LabOsModule`, +`LabOsModuleDependency`; `LabOsContext` +`modules` / +`module_dependencies` |
| `core/reasoning/labos/context_normalizer.py` | +`ModuleHealthView`, module fields on `NormalizedLabOsContext`, +`_escalate_module_status`, +`_critical_capability_flags`, module normalization in `normalize_labos_context` |
| `core/reasoning/labos/priority_engine.py` | +`_module_candidate`, new score bumps, `include_modules` + `include_nominal_modules` flags on `prioritize()` |
| `core/reasoning/labos/recommendation_engine.py` | `_target_is_unsafe` handles offline / incident modules |
| `core/reasoning/labos/usecases.py` | +5 use cases + mode constants |
| `core/reasoning/labos/__init__.py` | exports extended |
| `services/core.py` | 5 new modes + 5 new typed entry points |
| `api_gateway/main.py` | 5 new endpoint summaries (factory registers them) |
| `interfaces/mcp/handlers/reasoning.py` | 5 new tool descriptions + 5 new handler classes |
| `interfaces/mcp/handlers/__init__.py` | imports + `__all__` updated |
| `tests/reasoning/labos/test_modules.py` | new — 36 tests |
| `tests/reasoning/labos/test_surface_cli.py` | `_MODES` tuple extended |
| `tests/reasoning/labos/test_surface_http.py` | `_MODES` tuple extended |
| `tests/mcp/test_reasoning_labos_tool.py` | `_MODES` tuple extended |
| `tests/mcp/test_run_task_tool.py` | allow-list 13 → 18 |
| `README.md` | use-case list split into ReactorOps / RobotOps |
| `docs/reviews/phase_v2_robotops_reasoning_review.md` | this doc |

No reasoner rework, no governance change, no store change, no
CLI/HTTP/MCP dispatcher change.

---

## 7. Test coverage

New — `tests/reasoning/labos/test_modules.py` (36 tests across 8
classes):

- **`TestModuleNormalization` (7)** — index-by-id/class, offline
  escalation, disabled bucket, critical-capability flagging,
  safety-alert escalation, blocked dependency propagation,
  nominal module stays nominal.
- **`TestModulePrioritization` (6)** — `include_modules` gating,
  `include_nominal_modules` gating, incident/safety-alert lifting
  DOSE-01 to critical, stable dense ranks, mixed reactor+module
  ranking, autonomy signal emission.
- **`TestModuleDailyOverview` (5)** — summary phrasing,
  prioritised entities, recommendation fan-out,
  `no_invented_actions` deferral path, nominal-only shortcut.
- **`TestModuleIncidentReview` (3)** — counts, acknowledge
  intent, nominal-only shortcut.
- **`TestModuleCoordinationReview` (3)** — blocked-edge highlight
  + recommendation, nominal-only summary, trace metadata edge
  counts.
- **`TestModuleCapabilityRiskReview` (3)** — missing capability
  recommendation, autonomy trace, nominal-only summary.
- **`TestRobotopsCrossDomainOverview` (3)** — mixed ranking plane,
  trace metadata, zero-signal summary.
- **`TestInvariantsOnModules` (3)** — `respects_approval` on
  `open_module_detail`, `respects_safety_context` with offline
  module + safety alert, `no_invented_actions` for coordination
  review.
- **`TestModuleInputValidation` (3)** — unknown field rejected,
  duplicate action_name rejected, `module_class` free-form
  strings accepted (workshop, mobile_robot).

Plus surface-parity tests extended via `_MODES` tuples:

- `tests/reasoning/labos/test_surface_cli.py` — delegation over
  all 10 modes (now 18 tests).
- `tests/reasoning/labos/test_surface_http.py` — delegation over
  all 10 modes (now 14 tests).
- `tests/mcp/test_reasoning_labos_tool.py` — delegation over all
  10 modes (now 15 tests).
- `tests/mcp/test_run_task_tool.py` — tool allow-list pinned to
  18 tools.

---

## 8. Test gates

- Focused module suite — `tests/reasoning/labos/test_modules.py`
  **36 passed**.
- Reasoning + surface combined:
  `tests/reasoning/labos/` + `tests/mcp/test_reasoning_labos_tool.py`
  + `tests/mcp/test_run_task_tool.py` — **148 passed**.
- Full suite — **2075 passed, 1 skipped** (+51 vs. the V2
  surface-parity baseline of 2024).

Commands:

```bash
.venv/bin/python -m pytest tests/reasoning/labos/test_modules.py -q

.venv/bin/python -m pytest -o python_files='test_*.py' \
    tests/reasoning/labos/ \
    tests/mcp/test_reasoning_labos_tool.py \
    tests/mcp/test_run_task_tool.py -q

.venv/bin/python -m pytest -o python_files='test_*.py' tests/ -q
```

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (RobotOps reasoning V1) | ✅ |
| Idempotency rule honoured | ✅ |
| No parallel architecture | ✅ |
| Canonical surface + service paths reinforced | ✅ |
| No business logic in surfaces | ✅ |
| No shadow truth (reasoner input-only) | ✅ |
| `no_invented_actions` enforced | ✅ |
| `respects_approval` enforced | ✅ |
| `respects_safety_context` enforced | ✅ |
| Module/reactor ranking shares one plane | ✅ |
| Surface parity preserved | ✅ |
| Tool-list allow-list guard updated | ✅ |
| Focused suite green (+36) | ✅ |
| Full suite green (+51) | ✅ |
| Documentation consistent with prior V2 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Possible follow-ups, none urgent:

1. **UI parity** — `frontend/agent-ui` could render the five
   module reasoning outputs.  Backend is complete; this is a
   frontend-only addition.
2. **LabOS integration** — wire Smolit-AI-Assistant's dossier
   pipeline to call the new MCP tools against a real LabOS
   snapshot.  Cross-repo change; ABrain side is ready.
3. **RobotOps V2** — once LabOS ships mission/task abstractions
   for autonomous units, add mission-review and fleet-coordination
   use cases.  Needs an upstream schema first.
4. **ITOps cross-domain** — defer until LabOS exposes ITOps
   primitives (explicit anti-goal in this turn).

No code blockers.
