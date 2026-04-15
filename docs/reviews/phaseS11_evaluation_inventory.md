# Phase S11 — Evaluation Layer Inventory

**Date:** 2026-04-15
**Branch:** `codex/phaseS11-replay-compliance-regression`
**Purpose:** Baseline inventory before building the S11 evaluation layer.

---

## 1. Existing data available for replay and evaluation

### 1.1 Per-trace data (TraceStore / TraceSnapshot)

| Field | Source | Available since |
|-------|--------|----------------|
| `trace_id`, `workflow_name`, `task_id` | `TraceRecord` | always |
| `started_at`, `ended_at`, `status` | `TraceRecord` | always |
| `metadata.task_type` | `TraceRecord.metadata` | S1 |
| `metadata.plan_id`, `metadata.strategy` | `TraceRecord.metadata` | S1 |
| `spans` (list of `SpanRecord`) | `TraceSnapshot` | always |
| `explainability` (list of `ExplainabilityRecord`) | `TraceSnapshot` | S1 |
| `replay_descriptor` (`ReplayDescriptor`) | `TraceSnapshot` | **S10** |

### 1.2 Per-step explainability data (ExplainabilityRecord)

| Field | Available since | Notes |
|-------|----------------|-------|
| `step_id` | S1 | |
| `selected_agent_id` | S1 | |
| `candidate_agent_ids` | S1 | |
| `selected_score` | S1 | |
| `routing_reason_summary` | S1 | |
| `matched_policy_ids` | S1 | |
| `approval_required` | S1 | |
| `approval_id` | S1 | |
| `metadata.routing_decision` | S1 | full `RoutingDecision.model_dump()` incl. `task_type`, `required_capabilities`, `ranked_candidates` |
| `metadata.winning_policy_rule` | S1 | |
| `routing_confidence` | **S10** | first-class field |
| `score_gap` | **S10** | first-class field |
| `confidence_band` | **S10** | `"high"/"medium"/"low"` |
| `policy_effect` | **S10** | `"allow"/"deny"/"require_approval"` |
| `scored_candidates` | **S10** | list of `{agent_id, score, capability_match_score}` |

### 1.3 S10 ReplayDescriptor (read-time derived)

| Field | Notes |
|-------|-------|
| `can_replay` | `True` when `task_type` + candidate lists are present |
| `missing_inputs` | lists what context is absent |
| `step_inputs` | list of `ReplayStepInput` per explainability record |
| `ReplayStepInput.task_type` | from trace metadata or routing_decision metadata |
| `ReplayStepInput.required_capabilities` | from routing_decision metadata |
| `ReplayStepInput.selected_agent_id` | stored |
| `ReplayStepInput.candidate_agent_ids` | stored |
| `ReplayStepInput.routing_confidence` | S10 first-class field |
| `ReplayStepInput.confidence_band` | S10 first-class field |
| `ReplayStepInput.policy_effect` | S10 first-class field |

---

## 2. Inputs sufficient for a controlled routing dry-run

A routing dry-run via `RoutingEngine.route_intent(intent, descriptors)` requires:

| Required input | Available? | Source |
|---------------|-----------|--------|
| `task_type` | **YES** | `TraceRecord.metadata["task_type"]` or `ExplainabilityRecord.metadata["routing_decision"]["task_type"]` |
| `required_capabilities` | **YES** (for S10+ traces) | `ExplainabilityRecord.metadata["routing_decision"]["required_capabilities"]` |
| `domain` | Partially | not stored directly; default `"analysis"` sufficient for replay |
| `risk` | Partially | not stored directly; default `MEDIUM` sufficient for replay |
| `agent descriptors` | **YES** | live `AgentRegistry.list_descriptors()` — current catalog |

**Conclusion:** Routing dry-run is feasible for traces where `can_replay=True` (i.e., `task_type` and candidate list were captured). Domain/risk defaults are safe approximations.

---

## 3. Gaps for routing regression detection

| Gap | Impact | Mitigation in S11 |
|----|--------|------------------|
| `domain` not stored per step | Routing intent approximated | use `"analysis"` as default; mark as approximated |
| `risk` not stored per step | Same | use `MEDIUM` as default |
| Live catalog differs from historical | Expected by design | S11 detects and surfaces these deltas explicitly |
| Old traces (pre-S10) lack `routing_confidence` | No confidence comparison | mark as `non_replayable` if `can_replay=False` |

---

## 4. Inputs sufficient for policy compliance check

A policy evaluation via `PolicyEngine.evaluate(intent, descriptor, context)` requires:

| Required input | Available? | Source |
|---------------|-----------|--------|
| `task_type` | **YES** | same as routing |
| `required_capabilities` | **YES** | same as routing |
| `agent_id` (selected) | **YES** | `ExplainabilityRecord.selected_agent_id` |
| `source_type`, `execution_kind` | **PARTIAL** | reconstructed from current agent descriptor if available |
| `risk_level` | **PARTIAL** | not stored per-step; default `MEDIUM` |
| `estimated_cost`, `estimated_latency` | **NO** | not stored (not needed for basic compliance check) |
| `external_side_effect` | **NO** | not stored per-step |

**Stored ground truth for comparison:**
- `ExplainabilityRecord.policy_effect` — historical effect (allow/deny/require_approval)
- `ExplainabilityRecord.matched_policy_ids` — historical matched rules
- `ExplainabilityRecord.approval_required` — historical approval flag

**Conclusion:** Policy compliance comparison is feasible as "best-effort" — reconstructed context with available fields is sufficient to detect most regressions. Missing fields (cost, latency) are defensively defaulted to `None`.

---

## 5. What is already present for compliance baselines

| Signal | Stored | Notes |
|--------|--------|-------|
| `policy_effect` per step | YES (S10+) | first-class field on ExplainabilityRecord |
| `matched_policy_ids` per step | YES | available since S1 |
| `approval_required` per step | YES | available since S1 |
| `routing_confidence` per step | YES (S10+) | first-class field |
| `confidence_band` per step | YES (S10+) | first-class field |
| `score_gap` per step | YES (S10+) | first-class field |

These fields are sufficient to compute:
- policy compliance rate (what % of steps have unchanged `policy_effect`)
- approval consistency rate (what % have unchanged `approval_required`)
- routing confidence distribution (avg, band distribution)
- routing match rate (what % select the same agent today)

---

## 6. S11 canonical architecture decision

**Location:** `core/evaluation/`

Justification:
- It is a read-only decision-layer evaluation helper
- It calls existing canonical engines (RoutingEngine, PolicyEngine) in dry-run mode
- It reads from the canonical TraceStore
- It does NOT produce new traces, new approvals, or new executions
- It belongs beside `core/audit/`, `core/decision/`, `core/governance/` as a first-class evaluation primitive

**Not a test utility, not a CLI script, not a second trace store.**

---

## 7. What S11 will build

| Component | What it does |
|-----------|-------------|
| `core/evaluation/models.py` | `RoutingReplayResult`, `PolicyReplayResult`, `StepEvaluationResult`, `TraceEvaluationResult`, `BaselineReport` |
| `core/evaluation/harness.py` | `TraceEvaluator` — orchestrates per-trace and batch evaluation |
| `scripts/abrain_control.py` | `trace replay <id>`, `compliance check <id>` CLI commands |
| `tests/core/test_evaluation_harness.py` | Unit tests for all evaluation paths |

---

## 8. Explicit non-goals for S11

- No re-execution of real side effects
- No new TraceStore or second audit truth
- No automated online self-tuning based on evaluation results
- No approval bypass during replay
- No second routing engine or policy engine instance (reuses canonical ones)
