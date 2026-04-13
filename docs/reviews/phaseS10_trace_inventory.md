# Phase S10 — Trace / Audit / Explainability Inventory

**Date:** 2026-04-13

---

## 1. What trace/audit/explainability data exists today

### `TraceRecord` (SQLite `traces` table)
- `trace_id`, `workflow_name`, `task_id`
- `started_at`, `ended_at`, `status`
- `metadata` — opaque dict; contains `plan_id`, `plan_status`, `policy_effect`, `step_count`, `strategy` (written at finish time by orchestrator/services/core)

### `SpanRecord` (SQLite `spans` table)
- `span_id`, `trace_id`, `parent_span_id`
- `span_type`, `name` — e.g. `orchestration/execute_plan`, `step/routing`, `step/execution`
- `started_at`, `ended_at`, `status`
- `attributes` — opaque dict per span type (includes `plan_id`, `step_id`, `agent_id`, `success`, etc.)
- `events` — list of `TraceEvent(event_type, timestamp, message, payload)`
- `error` — dict when span failed

### `ExplainabilityRecord` (SQLite `explainability` table)
- `trace_id`, `step_id`
- `selected_agent_id`
- `candidate_agent_ids` — list of IDs only (no scores)
- `selected_score` — top candidate score
- `routing_reason_summary` — free-text string
- `matched_policy_ids` — list of matched rule IDs
- `approval_required`, `approval_id`
- `metadata` — opaque dict containing:
  - `routing_decision` — full `RoutingDecision` model dump (ranked_candidates with scores, routing_confidence, score_gap, confidence_band, diagnostics)
  - `rejected_agents` — list of rejected agent dicts (with rejection reason)
  - `candidate_filter` — CandidateFilter diagnostics
  - `created_agent` — dynamically created agent descriptor if any
  - `winning_policy_rule` — winning rule ID

### `TraceSnapshot` (read API)
- Groups trace + spans + explainability in one response
- Returned by `GET /control-plane/traces/{id}`

### `RoutingDecision` (computed, available in memory)
- `ranked_candidates` — all scored candidates with `score`, `capability_match_score`, `feature_summary`, `model_source`
- `routing_confidence` — top score (honest proxy for decision certainty)
- `score_gap` — gap between #1 and #2 (discrimination measure)
- `confidence_band` — "high"/"medium"/"low"
- `diagnostics` — includes rejected agents, filter diagnostics

### Explainability storage path
`services/core._store_trace_explainability()` is called at every routing decision point. It captures the `RoutingDecision`, `PolicyDecision`, and approval state and serializes them into an `ExplainabilityRecord`.

---

## 2. Where drilldown gaps exist

### Gap 1 — Key signals buried in `metadata` dict
`routing_confidence`, `score_gap`, `confidence_band` exist in `metadata.routing_decision` but are NOT first-class `ExplainabilityRecord` fields. A forensics query must parse nested JSON to access them.

### Gap 2 — No per-candidate scores in `candidate_agent_ids`
`ExplainabilityRecord.candidate_agent_ids` is a list of IDs only. The actual scores are buried in `metadata.routing_decision.ranked_candidates`. You cannot answer "what score did the second-best candidate get?" without parsing opaque metadata.

### Gap 3 — `policy_effect` not on `ExplainabilityRecord`
The governance effect ("allow" / "deny" / "require_approval") is stored only in `trace.metadata.policy_effect` (top-level trace field), not on the individual `ExplainabilityRecord`. For multi-step plans, you cannot determine the governance effect of a specific step without reconstructing it.

### Gap 4 — CLI `trace show` doesn't render explainability inline
`_render_trace_show()` only prints `"Explainability records: N"` — a count with no content. The operator must run a second `trace explain <id>` command and manually cross-reference.

### Gap 5 — CLI `explain` doesn't surface scores or confidence
`_render_explainability()` renders a table with `step_id`, `selected_agent`, `approval_required`, `approval_id`, `matched_policies`. There are no score columns, no confidence_band, no policy_effect column, no ranked candidate breakdown.

### Gap 6 — No replay-readiness metadata
There is no canonical structure describing "what inputs would be needed to reproduce this trace." A developer cannot quickly determine whether a trace is reproducible.

### Gap 7 — No forensics drilldown command
There is no `trace drilldown` CLI command that renders the full decision path in a structured, human-readable form.

---

## 3. What is missing for true forensics

| Signal | Currently stored? | Location | First-class? |
|--------|------------------|----------|-------------|
| selected_agent_id | Yes | ExplainabilityRecord | Yes |
| selected_score | Yes | ExplainabilityRecord | Yes |
| candidate IDs | Yes | ExplainabilityRecord | Yes (IDs only) |
| candidate scores | Yes | metadata.routing_decision | No — buried |
| routing_confidence | Yes | metadata.routing_decision | No — buried |
| score_gap | Yes | metadata.routing_decision | No — buried |
| confidence_band | Yes | metadata.routing_decision | No — buried |
| policy_effect | Yes (trace-level) | trace.metadata | No — step-level: missing |
| winning_policy_rule | Yes | metadata.winning_policy_rule | No — buried |
| rejected agents | Yes | metadata.rejected_agents | No — buried |
| approval rationale | Partial | approval_id only | No rating/comment |
| task_type context | Yes | metadata.routing_decision | No — not first-class |
| replay inputs needed | No | — | Missing entirely |

---

## 4. What would be valuable for replay-readiness

Minimum viable replay descriptor:
- What was the `task_type` and `required_capabilities`?
- What agents were candidates (with their states at the time)?
- What governance policy was active (which rules matched)?
- Was approval required and by whom?
- What was the confidence level of the decision?
- What inputs/context would a re-run need to reproduce the decision?

This is not a full re-execution engine — it is a structured summary that lets a developer say "here's what was needed; here's whether we can reproduce it."

---

## Conclusion

The existing trace infrastructure is solid — the data is all present. The issue is accessibility: key signals are buried in opaque `metadata` dicts, the CLI barely surfaces them, and there is no structured replay-readiness concept. S10 can deliver significant forensics value by surfacing existing signals as first-class fields and adding a focused `trace drilldown` command.
