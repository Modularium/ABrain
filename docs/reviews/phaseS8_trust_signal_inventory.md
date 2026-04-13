# Phase S8 — Trust / Quality Signal Inventory

## 1. Which trust/quality/cost/health/feedback signals already exist?

### A. `AgentPerformanceHistory` (core/decision/performance_history.py)

| Field | Type | Description |
|---|---|---|
| `success_rate` | float [0,1] | Rolling average of successful executions |
| `avg_latency` | float ≥ 0 | Rolling average in seconds |
| `avg_cost` | float ≥ 0 | Rolling average cost per execution |
| `avg_token_count` | float ≥ 0 | Rolling average token count |
| `avg_user_rating` | float ≥ 0 | Rolling average of approval-derived ratings (0–5 scale) |
| `recent_failures` | int ≥ 0 | Failure streak; resets to 0 on success |
| `execution_count` | int ≥ 0 | Total observed executions |
| `load_factor` | float [0,1] | Current relative load |

### B. `AgentDescriptor` enum fields (core/decision/agent_descriptor.py)

| Field | Values |
|---|---|
| `trust_level` | UNKNOWN / SANDBOXED / TRUSTED / PRIVILEGED |
| `availability` | UNKNOWN / ONLINE / DEGRADED / OFFLINE |
| `cost_profile` | UNKNOWN / LOW / MEDIUM / HIGH / VARIABLE |
| `latency_profile` | UNKNOWN / INTERACTIVE / BACKGROUND / BATCH |

### C. `RoutingDecision` confidence signals (core/decision/routing_engine.py — S4.2)

| Field | Type | Description |
|---|---|---|
| `routing_confidence` | float or None | Top candidate score |
| `score_gap` | float or None | Gap between #1 and #2 candidate |
| `confidence_band` | "high"\|"medium"\|"low"\|None | Categorical routing certainty |

### D. `FeedbackUpdate` (core/decision/feedback_loop.py)

| Field | Description |
|---|---|
| `score_delta` | +1 on success, -1 on failure |
| `reward` | Computed reward from online updater (if active) |
| `user_rating` | Float extracted from approval decision metadata |
| `warnings` | e.g. "approval_outcome_not_learned" |

### E. Fallback involvement (core/orchestration/orchestrator.py — S4)

Available in trace span attributes and step metadata:

| Key | Description |
|---|---|
| `fallback_triggered` | bool — whether fallback was used |
| `primary_agent_id` | Agent that failed |
| `primary_error_code` | Error code triggering fallback |
| `fallback_agent_id` | Agent that executed the fallback step |

### F. Health signals (services/core.py — S7)

Derived per control-plane overview:

| Signal | Description |
|---|---|
| `degraded_agent_count` | Agents with availability=degraded |
| `offline_agent_count` | Agents with availability=offline |
| `paused_plan_count` | Plans in paused state |
| `failed_plan_count` | Plans in failed/rejected state |
| `pending_approval_count` | Approvals awaiting decision |
| `attention_items` | Prioritised list of operator-relevant items |
| `overall` | "healthy" / "attention" / "degraded" |

### G. Neural policy feature encoding (core/decision/feature_encoder.py)

`FeatureEncoder.encode()` already uses all of the above signals as a combined feature vector for neural scoring.  Encoded fields include: `capability_match_score`, `success_rate`, `avg_latency`, `avg_cost`, `recent_failures`, `execution_count`, `load_factor`, `trust_level`, `availability`, `cost_profile`, `latency_profile`, `source_type`, `execution_kind`, plus 8-dim task embedding.

---

## 2. Where do these signals originate?

| Signal | Origin |
|---|---|
| `success_rate`, `recent_failures`, `execution_count` | `PerformanceHistoryStore.record_result()` called from `FeedbackLoop.update_performance()` after each execution |
| `avg_latency`, `avg_cost`, `avg_token_count` | `ExecutionResult.duration_ms`, `.cost`, `.token_count` → FeedbackLoop |
| `avg_user_rating` | `ApprovalDecision.rating` (int 1–5) extracted in `FeedbackLoop` |
| `trust_level`, `availability` | Static agent registry JSON (`runtime/abrain_agents.json` or Flowise catalog) |
| `routing_confidence`, `score_gap` | Computed post-MLP in `RoutingEngine.route_intent()` (S4.2) |
| `fallback_triggered` | `Orchestrator._execute_plan_step()` (S4) |
| Health overview | `_compute_health_summary()` in `services/core.py` (S7) |

---

## 3. Where are they stored today?

| Signal | Storage |
|---|---|
| `AgentPerformanceHistory` | In-memory `PerformanceHistoryStore`; optionally serialized to JSON via `save_json()` — **not automatically persisted** |
| Agent descriptor fields | Agent registry JSON file (runtime/) |
| Trace spans / events | SQLite `abrain_traces.sqlite3` via `TraceStore` |
| Approval records | `abrain_approvals.json` / approval store |
| Plan state | `abrain_plan_state.sqlite3` |
| Routing decisions | Inside trace span attributes (SQLite) |
| Health summary | Computed live in `get_control_plane_overview()`, not persisted |

---

## 4. Where are they used today?

| Signal | Used in |
|---|---|
| `success_rate`, `avg_latency`, `avg_cost`, `recent_failures` | `FeatureEncoder.encode()` → neural policy scoring |
| `availability=DEGRADED` | `_apply_degraded_penalty()` in `RoutingEngine` (S4.2) |
| `cost_profile` | `_apply_cost_tiebreak()` in `RoutingEngine` (S4.2) |
| `routing_confidence`, `confidence_band` | Span attributes + `routing_low_confidence` event (S4.2) |
| `availability`, `trust_level` | `AgentCatalogEntry` exposed via control-plane API |
| `availability` (degraded/offline) | `_compute_health_summary()` → `SystemHealthPage` (S7) |
| `fallback_triggered` | Span attributes, step metadata, audit trail |
| `avg_user_rating` | Neural policy feature (via encoder) |

---

## 5. Gaps

| Gap | Impact |
|---|---|
| No canonical per-agent quality summary | Operators cannot tell at a glance how reliable/trustworthy an agent is |
| `AgentPerformanceHistory` is in-memory only | Control-plane catalog API cannot show runtime performance data unless static metadata is pre-populated in the agent JSON |
| No quality band in agent list (CLI or UI) | Operators must infer quality from separate signals |
| No quality signal in explainability records | Routing decisions don't include "why this agent was considered reliable" |
| Fallback involvement not accumulated in `AgentPerformanceHistory` | Repeated fallback-triggering agents appear equally rated as stable agents |
| No minimum-data protection in public trust signal | New agents could be unfairly rated on 1–2 samples |

---

## What S8 will operationalize

A single, small, deterministic `AgentQualitySummary` in `core/decision/agent_quality.py` that:
- combines `success_rate`, `recent_failures`, `availability`, `avg_user_rating`, `trust_level`
- produces a `quality_score` (float [0,1]) with documented formula
- produces a `quality_band` ("good" / "fair" / "poor")
- surfaces `attention_flags` for operator visibility
- protects new agents via `data_sufficient` flag
- is exposed in: agent catalog API, CLI agent list, SystemHealthPage agent health section

No new ML model, no new data store, no second trust world, no managers/ revival.
