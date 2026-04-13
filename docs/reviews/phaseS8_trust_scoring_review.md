# Phase S8 — Trust Scoring Operationalization Review

## 1. Signals operationalized

S8 operationalizes the following already-existing signals into a canonical
per-agent quality summary:

| Signal | Source |
|---|---|
| `success_rate` | `AgentPerformanceHistory` (PerformanceHistoryStore / agent metadata) |
| `recent_failures` | `AgentPerformanceHistory` |
| `avg_user_rating` | `AgentPerformanceHistory` (from approval rating field) |
| `availability` | `AgentDescriptor.availability` enum (ONLINE / DEGRADED / OFFLINE / UNKNOWN) |
| `trust_level` | `AgentDescriptor.trust_level` enum (PRIVILEGED / TRUSTED / SANDBOXED / UNKNOWN) |

The following signals exist but are **not yet included** in the score (available
for future phases): `avg_latency`, `avg_cost`, `avg_token_count`, `load_factor`,
`fallback_triggered` count per agent.

---

## 2. How the score / summary works

### Location

`core/decision/agent_quality.py` — one file, one public function, no IO.

### Formula

```
quality_score = (
    success_component    * 0.50
  + reliability_component * 0.25
  + availability_component * 0.15
  + rating_component    * 0.10
) + trust_modifier        clamp([0.0, 1.0])
```

### Component definitions

| Component | Formula | Notes |
|---|---|---|
| `success_component` | `history.success_rate` | Neutral 0.5 when `data_sufficient=False` |
| `reliability_component` | `max(0, 1 - recent_failures * 0.15)` | Neutral 1.0 when `data_sufficient=False` |
| `availability_component` | ONLINE=1.0, UNKNOWN=0.7, DEGRADED=0.4, OFFLINE=0.0 | Fixed table |
| `rating_component` | `avg_user_rating / 5.0` | Neutral 0.5 when no data |
| `trust_modifier` | PRIVILEGED=+0.05, TRUSTED=0, SANDBOXED=-0.05, UNKNOWN=0 | Additive, small |

### Bands

| Band | Threshold |
|---|---|
| `"good"` | quality_score ≥ 0.70 |
| `"fair"` | quality_score ≥ 0.40 |
| `"poor"` | quality_score < 0.40 |

### Attention flags

`attention_flags` is a list of string codes, each independently derivable:

- `"insufficient_data"` — execution_count < MIN_EXECUTIONS (3)
- `"offline"` — availability == OFFLINE
- `"degraded"` — availability == DEGRADED
- `"high_recent_failures"` — recent_failures ≥ 3 (only when data_sufficient)
- `"low_success_rate"` — success_rate < 0.60 (only when data_sufficient)
- `"poor_user_rating"` — avg_user_rating > 0 and < 2.5 (only when data_sufficient)

### New-agent protection

`data_sufficient = execution_count >= MIN_EXECUTIONS`.  When False, success and
reliability components default to neutral values (0.5 and 1.0 respectively) so
new agents are never labelled "poor" solely due to absence of history.  The
`"insufficient_data"` flag communicates this clearly.

---

## 3. Where is it visible / usable?

| Surface | What changes |
|---|---|
| `GET /control-plane/agents` | `AgentCatalogEntry.quality` field added (optional, `AgentQualitySummary`) |
| `GET /control-plane/overview` | Same — agents in overview now carry quality summaries |
| `abrain agent list` (CLI) | New `quality` column: `good(0.93)` / `fair(0.55)` / `-` |
| `SystemHealthPage /health` (UI) | Degraded/offline agents now show quality band badge alongside availability badge |
| `core.decision` public API | `AgentQualitySummary`, `compute_agent_quality`, `MIN_EXECUTIONS` exported |

---

## 4. What future phases can build on this

- **S-Governance:** Policy rules can reference `quality_band` — e.g. deny POOR-band
  agents for high-risk steps.
- **S-Routing:** `RoutingEngine` can optionally weight or penalize agents with
  `quality_band == "poor"` (analogous to the existing DEGRADED penalty).
- **S-Alerting:** Attention flags are ready-made for operator notification rules.
- **S-History Persistence:** Persisting `AgentPerformanceHistory` to a durable
  store would allow quality summaries to survive process restarts, making the
  score more reliable.

---

## 5. Architecture confirmations

1. **No parallel implementation built.** There is exactly one canonical quality
   computation path: `compute_agent_quality()` in `core/decision/agent_quality.py`.

2. **No `managers/` revival.** No code from the old `managers/` world was
   re-introduced.  The formula is simpler and better-bounded than the old
   `MetaLearner._get_historical_performance` approach.

3. **No ML / MLflow / heavy-dependency regression.** The module imports only
   `pydantic` and other canonical `core.decision` types.  No `torch`, no
   `scipy`, no `mlflow`.

4. **Exactly one canonical trust/quality summary layer.** `core/decision/agent_quality.py`
   is the single source of truth.  API, CLI, and UI consume it without
   re-computing or re-interpreting.

5. **S8 is value-adding, auditable, and architecturally clean.**
   - Deterministic formula with fully documented weights
   - Transparent `score_components` in every response
   - Zero new data stores, zero new processes, zero new runtime infrastructure
   - Additive to S2-Governance (not a replacement — governance policies are unchanged)
   - Additive to S4.2-Routing (routing preferences are unchanged — quality is surfaced
     separately and not yet fed back into routing in S8)

---

## Test coverage

**New file:** `tests/decision/test_agent_quality.py` — 45 tests covering:
- Return type and structure
- Determinism
- `data_sufficient` protection (new agents not penalised)
- All six attention flag conditions
- Quality band thresholds (good / fair / poor)
- Availability component values
- Trust modifier values
- Recent failures and rating impact
- Score clamping at [0, 1]
- Pydantic model constraint validation

**Existing tests updated:**
- `tests/services/test_control_plane_views.py::test_list_agent_catalog_projects_existing_agent_listing`
  updated to assert the new `quality` field is present and valid.

**Full suite results:** 304 passed, 1 skipped (node export integration test, unchanged).
Frontend: type-check ✓, build ✓, lint ✓.
