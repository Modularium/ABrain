# Phase 6 – §6.3 Observability: BrainOperationsReport review

**Branch:** `codex/phase6-brain-operations-report`
**Date:** 2026-04-19
**Scope:** `core/decision/brain/operations_report.py` — compositional read-only
surface that bundles `BrainBaselineAggregator` (B6-S5) and
`BrainSuggestionFeedBuilder` (B6-S6) into one operator lagebericht.

---

## 1. Roadmap position

Phase 0, Phase 1, Phase 2–5 and Phase 6 (B6-S1…B6-S6) are all closed on main
(see `docs/reviews/phase0_1_backfill_audit.md`, `phase2_5_spot_check_audit.md`,
`phase6_B5_review.md`, `phase6_B6_review.md`). Phase 7 is deferred until a
real-traffic promote verdict is on record.

The roadmap §6 Querschnitts-Workstreams list observability as §6.3. The
Phase-0/1 audit explicitly recommended this step as the next move:

> **Querschnitts-Workstreams (§6)** — a good first pick is **§6.3 Observability**:
> a small operator surface that aggregates Brain baseline + suggestion feed
> output into a single report, since Phase 6 is now the newest moving part.

`BrainOperationsReport` is exactly that surface.

---

## 2. Design

The reporter owns no span-scanning logic of its own. It is a thin
wiring layer that:

1. Runs `BrainBaselineAggregator.aggregate(...)` with the shared scan
   parameters (`trace_limit`, `workflow_filter`, `version_filter`).
2. Passes the resulting `BrainBaselineReport` as the `baseline_report` gate
   into `BrainSuggestionFeedBuilder.build(...)` with the same shared scan
   parameters.
3. Wraps both outputs plus the scan params and a generation timestamp into a
   single `BrainOperationsReport` Pydantic model (`extra="forbid"`).

### Why compositional, not a rewrite

- Keeps a single source of truth for `brain_shadow_eval` span parsing
  (`_summary_from_span` in `baseline_aggregator.py`), reused unchanged.
- Preserves the suggestion-only contract of B6-S6: the feed is gated
  identically whether invoked directly or via the reporter, because the
  reporter passes the aggregator's actual report into the builder — the
  gate logic lives exactly where it did before.
- No new TraceStore queries; no duplicate scan; no risk of drift between the
  two primitives' filter semantics.

### Defaults vs injection

`BrainOperationsReporter.__init__` accepts optional pre-configured
`aggregator=` and `feed_builder=` arguments. Omitted → constructed with
their standard defaults. This supports:

- the common "just show me what Brain says" case (one-line construction);
- operator-tuned thresholds (pass a custom aggregator with adjusted
  `min_agreement_for_promote` / `max_divergence_for_promote` /
  `min_samples_for_promote`);
- a higher `min_score_divergence` cutoff on the feed builder.

The reporter does not revalidate that both injected components share the
same `TraceStore` — keeping the wiring trivial and the surface honest
about its compositional nature.

---

## 3. Public API

```python
from core.decision.brain import BrainOperationsReport, BrainOperationsReporter

reporter = BrainOperationsReporter(trace_store=trace_store)
report = reporter.generate(
    trace_limit=500,
    workflow_filter="code_review_flow",
    version_filter="brain_v1-20260419",
    max_feed_entries=10,
)

# report.baseline          -> BrainBaselineReport (B6-S5 shape)
# report.suggestion_feed   -> BrainSuggestionFeed (B6-S6 shape, gated on
#                              report.baseline.recommendation)
# report.generated_at / trace_limit / workflow_filter / version_filter
```

### Gate propagation

| Baseline verdict | Feed `gate_passed` | Feed `entries` |
|---|---|---|
| `promote` | `True` | populated (up to `max_feed_entries`) |
| `observe` | `False` | empty list (counts preserved) |
| `reject` | `False` | empty list (counts preserved) |

Counts (`shadow_samples`, `disagreement_samples`) are populated regardless
of gate state, so operators can see *what would have surfaced* even while
Brain stays observational.

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No ownership of production `RoutingDecision` / policy / approval / execution | ✅ — pure observer |
| No second `TraceStore` / `ModelRegistry` / policy stack | ✅ — delegates to existing primitives |
| No writes to any store | ✅ — `TraceStore` handed through read-only |
| No duplicate span-scan implementation | ✅ — reuses `_summary_from_span` transitively |
| No new dependencies | ✅ — stdlib + pydantic only |
| Additive only | ✅ — one new module + lazy exports + one test file + this doc |
| Suggestion-only contract (B6-S6) | ✅ — gate behavior identical to direct feed use |

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/decision/brain/operations_report.py` | `BrainOperationsReport`, `BrainOperationsReporter` |
| `core/decision/brain/__init__.py` | lazy exports for the two symbols |
| `tests/decision/test_brain_operations_report.py` | 10 unit tests |
| `docs/reviews/phase6_obs_report_review.md` | this doc |

---

## 6. Test coverage

10 tests, all green:

- **TestReporterConstruction** (2) — default wiring; injected components
  accepted verbatim.
- **TestGenerate** (6)
  - Empty store → `observe` + empty gated feed.
  - `promote` verdict surfaces all disagreement entries.
  - `observe` verdict suppresses `entries` but preserves `shadow_samples`
    / `disagreement_samples`.
  - Shared `workflow_filter` + `version_filter` reach both primitives
    identically (cross-filter slice shrinks both counts in lockstep).
  - `trace_limit` caps both primitives' `traces_scanned`.
  - `max_feed_entries` caps only the feed, not the baseline.
- **TestSchema** (2) — `extra="forbid"` and required-field enforcement.

---

## 7. Test gates

- Mandatory suite (`tests/state tests/mcp tests/approval tests/orchestration
  tests/execution tests/decision tests/adapters tests/core tests/governance
  tests/services tests/integration/test_node_export.py`): **1121 passed,
  1 skipped**.
- Full suite (`tests/` with `test_*.py`): **1534 passed, 1 skipped**
  (+10 new tests over the 1524 baseline).

---

## 8. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (composition, no new production path) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical paths reinforced | ✅ |
| No new shadow source-of-truth | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+10 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 9. Next step

With §6.3 Observability landed, the natural next candidates by roadmap
priority are:

1. Another §6 Querschnitts-Workstream — e.g. §6.4 Data Governance (trace
   retention / PII-aware export) or §6.5 Efficiency (Brain-call cost
   accounting).
2. Phase 7 — deferred until a real-traffic `promote` verdict is produced
   by `BrainOperationsReporter` on actual shadow traces.

Phase 7 remains blocked on real-traffic validation; this turn does not
change that gate.
