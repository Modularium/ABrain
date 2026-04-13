# Phase S10 — Trace Drilldown & Replay Readiness for Forensics

**Branch:** `codex/phaseS10-replay-forensics-trace-drilldown`
**Date:** 2026-04-13
**Reviewer:** automated phase gate

---

## Goal

Deepen the existing ABrain trace/audit/explainability layer to give operators and developers significantly better forensic insight into how each routing decision was made — without building a second trace system, a second audit store, or an automated replay engine.

---

## What changed

### `core/audit/trace_models.py` — `ExplainabilityRecord` extended

Five new first-class forensics fields, all nullable/defaulted for backwards compatibility:

| Field | Type | Previously | Now |
|-------|------|-----------|-----|
| `routing_confidence` | `float \| None` | buried in `metadata.routing_decision` | first-class field |
| `score_gap` | `float \| None` | buried in `metadata.routing_decision` | first-class field |
| `confidence_band` | `str \| None` | buried in `metadata.routing_decision` | first-class field |
| `policy_effect` | `str \| None` | only at trace level, not per step | per-step, first-class |
| `scored_candidates` | `list[dict]` | buried in `metadata.routing_decision` | first-class list |

All new string fields go through the existing `normalize_strings` validator. All new fields have safe defaults — old records read as `None`/`[]`.

### `core/audit/trace_models.py` — new `ReplayStepInput` and `ReplayDescriptor` models

```python
class ReplayStepInput(BaseModel):
    step_id: str
    task_type: str | None
    required_capabilities: list[str]
    selected_agent_id: str | None
    candidate_agent_ids: list[str]
    routing_confidence: float | None
    confidence_band: str | None
    policy_effect: str | None

class ReplayDescriptor(BaseModel):
    trace_id: str
    workflow_name: str
    task_type: str | None
    task_id: str | None
    started_at: str | None
    step_inputs: list[ReplayStepInput]
    can_replay: bool           # True when task_type + candidates are present
    missing_inputs: list[str]  # what's missing for reproducibility
    metadata: dict[str, Any]
```

### `core/audit/trace_models.py` — `TraceSnapshot` extended

```python
class TraceSnapshot(BaseModel):
    ...
    replay_descriptor: ReplayDescriptor | None = None  # NEW
```

Included in the existing `GET /control-plane/traces/{id}` response automatically — no new endpoint.

### `core/audit/trace_store.py` — schema migration and persistence

- `_ensure_schema()` runs `ALTER TABLE explainability ADD COLUMN ...` for each new field (idempotent — `try/except` swallows duplicate-column errors on existing databases)
- `store_explainability()` writes all 5 new columns
- `_row_to_explainability()` reads them with `key in row.keys()` guard for old rows
- `_build_replay_descriptor()` private method derives `ReplayDescriptor` from stored trace + explainability at read time — no additional IO
- `get_trace()` calls `_build_replay_descriptor()` and includes it in the returned `TraceSnapshot`

### `services/core.py` — `_store_trace_explainability()` enriched

Populates all 5 new first-class fields from the live `RoutingDecision` and `PolicyDecision` objects at the moment the explainability record is written:

```python
routing_confidence=decision.routing_confidence,
score_gap=decision.score_gap,
confidence_band=decision.confidence_band,
policy_effect=policy_decision.effect,
scored_candidates=[
    {"agent_id": c.agent_id, "score": c.score, "capability_match_score": c.capability_match_score}
    for c in decision.ranked_candidates
],
```

### `scripts/abrain_control.py` — CLI forensics improvements

**`trace show`** now renders inline decision table:
- Columns: `step_id`, `selected_agent`, `score`, `confidence`, `policy_effect`, `approval`
- Replay-readiness summary line: `Replay-readiness: can_replay=yes  missing=-`

**`explain`** table enriched:
- New columns: `score`, `confidence`, `band`, `gap`, `policy_effect`
- Per-step candidate breakdown table (agent_id, score, cap_match) if `scored_candidates` populated

**`trace drilldown <trace_id>`** — new forensics command:
- Full structured decision reconstruction per step
- Shows: selected agent + score, confidence band + routing_confidence + gap, policy effect, approval info, ranked candidate table, matched policies, routing reason
- Replay-readiness footer: can_replay, task_type, missing inputs, plan_id, strategy

### `api_gateway/schemas.py`

Added imports of `ReplayDescriptor` and `ReplayStepInput` — both flow through `TraceSnapshot` into the existing `TraceDetailResponse` without any schema changes.

### `frontend/agent-ui/src/services/controlPlane.ts`

- `ExplainabilityRecord` interface updated with 5 new forensics fields
- New `ReplayStepInput` and `ReplayDescriptor` TypeScript interfaces
- `TraceSnapshot.replay_descriptor?: ReplayDescriptor | null` added

---

## Forensics capabilities added

| Capability | Before S10 | After S10 |
|-----------|-----------|----------|
| See routing_confidence per step | Only via opaque metadata.routing_decision | First-class field on ExplainabilityRecord |
| See score_gap (discrimination) | Only via opaque metadata | First-class field |
| See confidence_band per step | Only via opaque metadata | First-class field |
| See policy_effect per step | Only trace-level, not per step | Per-step, first-class |
| See ranked candidate scores | Only via opaque metadata | First-class scored_candidates list |
| CLI drilldown view | Only raw metadata dump | `trace drilldown` command with structured forensics view |
| Replay-readiness | Not available | ReplayDescriptor in every TraceSnapshot |
| API replay metadata | Not available | Included in GET /control-plane/traces/{id} |

---

## Replay readiness

`ReplayDescriptor.can_replay = True` when:
- `task_type` is present (from trace metadata or routing_decision metadata)
- At least one decision step has `candidate_agent_ids` populated

`missing_inputs` lists what is absent. This is a **descriptive** readiness flag — not an execution trigger. No replay happens automatically.

---

## Tests added

**`tests/core/test_trace_forensics.py`** — 21 unit tests:
- `ExplainabilityRecord` new fields: defaults, acceptance, normalisation, extra fields forbidden
- `ReplayStepInput`: minimal, full, extra fields forbidden
- `ReplayDescriptor`: minimal, can_replay, model_dump, extra fields forbidden
- `TraceSnapshot.replay_descriptor` defaults to `None` when no explainability
- `TraceStore`: persists new columns, reads them, old rows without columns produce `None`/`[]`
- `_build_replay_descriptor`: built from explainability, `can_replay=True`, missing task_type, missing candidates, `None` without explainability, multi-step plan

**Full test suite:** 280 passed, 1 skipped (pre-existing), 0 failures.

---

## Architecture check

### No parallel implementation
There is no second trace pipeline. `ExplainabilityRecord` is unchanged conceptually — only enriched with first-class fields that were previously buried in its `metadata` dict.

### TraceStore remains the only audit/trace truth
`ReplayDescriptor` is derived at read time from stored explainability records — no second write path, no second table, no additional persistence beyond the 5 new `ALTER TABLE ADD COLUMN` columns on the existing `explainability` table.

### No second replay/debug/forensics world
`trace drilldown` is a read-only CLI view over existing `TraceStore.get_trace()` data. `ReplayDescriptor` is a structural description, not an execution engine.

### No policy/approval/governance bypass
S10 touches only the read side (new display fields, CLI renderer, API types). The routing, governance, approval, and execution flows are unchanged.

### Value delivered
Operators can now answer the following questions from a single `trace drilldown <id>` call — something that previously required manually parsing nested JSON:
- What score did the selected agent receive? What was the runner-up?
- How confident was the routing engine? Was it a clear win or a close call?
- What governance effect applied to this step?
- Is there enough context to reproduce this routing decision?

---

## What follows from S10

- **S11+**: If replay-readiness is consistently `True` across production traces, a future phase can build a controlled dry-run reproducer that re-routes a stored task through the current agent catalog — exercising `RoutingEngine.route_intent()` with the captured `task_type`/`required_capabilities` without executing.
- **UI**: The `scored_candidates` and `replay_descriptor` fields are now in the TypeScript types; a future trace detail panel can render the candidate score table and replay-readiness badge directly.
