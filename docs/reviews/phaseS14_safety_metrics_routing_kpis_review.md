# Phase S14 — Safety Metrics + Routing KPIs

**Branch:** `codex/phaseS10-replay-forensics-trace-drilldown`
**Date:** 2026-04-15
**Reviewer:** automated phase gate

---

## Goal

Complete the two remaining Phase 1 open items identified in the S13 review:

1. **Safety-Metriken definieren** — policy compliance rate and approval bypass
   detection were not computed anywhere.  `BatchEvaluationReport` needed
   `approval_bypass_count` to surface steps where `approval_required=True` but
   no `approval_id` was recorded — a direct safety signal.

2. **Routing-Baseline-Metriken** — `BatchEvaluationReport` already held
   `routing_match_rate` and `avg_routing_confidence` from S11.  The remaining
   KPIs (trace success/failure rate, mean latency, P95 latency) were missing.

Both changes are **additive** — no existing fields or logic were modified.

---

## What changed

### `core/evaluation/models.py` — 6 new fields on `BatchEvaluationReport`

#### Routing KPIs

```python
trace_success_count: int = 0      # traces with status='completed'
trace_failed_count:  int = 0      # traces with status='failed'
trace_success_rate:  float | None = None  # success / (success + failed)
avg_duration_ms:     float | None = None  # mean duration of completed traces
p95_duration_ms:     float | None = None  # 95th-percentile duration
```

#### Safety metrics

```python
approval_bypass_count: int = 0
"""Steps where approval_required=True but no approval_id was recorded."""
```

### `core/evaluation/harness.py` — compute_baselines() extended

Three new accumulation blocks added inside the trace loop:

**Routing KPIs — success rate**
```python
if trace_status == "completed":
    report.trace_success_count += 1
elif trace_status == "failed":
    report.trace_failed_count += 1
```

**Routing KPIs — latency (completed traces only)**
```python
if ended_at and started_at and trace_status == "completed":
    delta_ms = (ended_at - started_at).total_seconds() * 1000.0
    if delta_ms >= 0.0:
        durations_ms.append(delta_ms)
```

**Safety metrics — approval bypass detection**
```python
for exp in snapshot.explainability:
    if exp.approval_required and not exp.approval_id:
        report.approval_bypass_count += 1
```

Derived rates computed after the loop:
```python
terminal_count = success + failed
if terminal_count:
    report.trace_success_rate = success / terminal_count

if durations_ms:
    report.avg_duration_ms = mean(durations_ms)
    p95_idx = min(int(0.95 * N), N-1)
    report.p95_duration_ms = sorted_durations[p95_idx]
```

### `tests/core/test_evaluation_harness.py` — 12 new tests (S14 section)

| Test | What it verifies |
|------|-----------------|
| `test_batch_report_new_safety_and_kpi_fields_default` | All 6 new fields have correct zero/None defaults |
| `test_compute_baselines_trace_success_rate_all_completed` | 3 completed traces → success_rate=1.0 |
| `test_compute_baselines_trace_success_rate_all_failed` | 2 failed traces → success_rate=0.0 |
| `test_compute_baselines_trace_success_rate_mixed` | 2 completed + 1 failed → success_rate≈0.667 |
| `test_compute_baselines_running_traces_excluded_from_success_rate` | In-progress traces not counted in terminal denominator |
| `test_compute_baselines_duration_computed_for_completed_traces` | avg_duration_ms and p95_duration_ms populated for completed traces |
| `test_compute_baselines_duration_none_when_no_completed_traces` | Failed-only traces → both duration fields remain None |
| `test_compute_baselines_empty_store_duration_none` | Empty store → all optional metrics are None |
| `test_compute_baselines_approval_bypass_counted` | approval_required=True, no approval_id → bypass_count=1 |
| `test_compute_baselines_approval_no_bypass_when_id_present` | approval_required=True, approval_id set → bypass_count=0 |
| `test_compute_baselines_approval_no_bypass_when_not_required` | approval_required=False, no id → bypass_count=0 |
| `test_compute_baselines_approval_bypass_count_accumulates` | 2 bypasses + 1 non-bypass across 3 traces → bypass_count=2 |

---

## Architecture check

### 1. No production code changed beyond the evaluation layer

`core/decision/`, `core/governance/`, `core/audit/`, `core/execution/` —
all unmodified.  Only `core/evaluation/models.py`, `core/evaluation/harness.py`,
and the test file changed.

### 2. Approval bypass signal is correctly scoped

`approval_bypass_count` counts **steps**, not traces.  A trace with 3 steps
each requiring approval but none having an `approval_id` contributes 3 to the
counter — matching the granularity of the underlying `ExplainabilityRecord`.

### 3. Latency tracked only for completed traces

Failed, running, and cancelled traces are excluded from `durations_ms`.
This matches the semantic intent: P95 latency is a "happy-path performance"
metric, not a measure of how long failures take.

### 4. success_rate denominator is terminal traces only

Running traces (`status != "completed" and status != "failed"`) are excluded
from the denominator.  This prevents an in-flight batch from artificially
depressing the success rate.

### 5. P95 formula

```
p95_idx = min(floor(0.95 * N), N - 1)
```

For N=1: index 0 (the only element).
For N=20: index 19 (last element, as expected for exact percentile).
For N=100: index 95.
No off-by-one at boundary cases.

---

## Test counts

| Suite | Tests before S14 | New in S14 | Total |
|-------|-----------------|-----------|-------|
| `tests/core/test_evaluation_harness.py` | 29 | 12 | 41 |
| Rest of CI suite | — | 0 | unchanged |

**Full suite:** 519 passed, 1 skipped, 0 failures

---

## Phase 1 completion status

| Item | Status |
|------|--------|
| Routing replay + compliance regression (S11) | DONE |
| Explainability depth + forensic replay (S10) | DONE |
| CI gates for all canonical modules (S13) | DONE |
| Adapter output schema contracts (S13) | DONE |
| Safety-Metriken: approval_bypass_count | **DONE (S14)** |
| Routing KPIs: trace success rate | **DONE (S14)** |
| Routing KPIs: avg + P95 latency | **DONE (S14)** |

All Phase 1 evaluation and metrics deliverables are now complete.

---

## Merge-readiness

| Check | Status |
|-------|--------|
| No production code outside evaluation layer changed | PASS |
| No parallel implementation | PASS |
| All 6 new fields have correct defaults | PASS |
| success_rate denominator excludes non-terminal traces | PASS |
| Duration tracked for completed traces only | PASS |
| P95 index formula correct at N=1,20,100 | PASS |
| Approval bypass counts steps, not traces | PASS |
| All 12 new tests green | PASS |
| Full suite green (519 passed, 1 skipped) | PASS |
| Phase 1 metrics roadmap fully closed | PASS |

**Merge-ready: YES**
