# Phase 6 – Brain v1 B6-S6: Brain Suggestion Feed

**Branch:** `codex/phase6-brain-v1-suggestion-feed`
**Date:** 2026-04-19
**Roadmap task:** *Phase 6 / "Brain-v1 nur als Vorschlagsmodell ausrollen, nicht als Policy-Ersatz"* — closes the final Phase-6 task by surfacing Brain's top-1 suggestion to operators without giving Brain any decision ownership.

---

## 1. Scope

Read-only operator-facing surface over existing `brain_shadow_eval` spans
(B6-S4) in the canonical `TraceStore`:

- filters shadow evaluations down to *actionable disagreements*
  (production_agent != brain_agent, both non-null) with an optional
  `score_divergence` floor;
- gated by an optional `BrainBaselineReport` — when supplied, entries are
  only surfaced on a `promote` verdict; any other verdict returns an
  empty feed with an explanatory `gate_reason` string;
- returns a structured `BrainSuggestionFeed` with traces scanned, shadow
  samples seen, disagreements counted, surfaced entries, gate state, and
  the filter threshold used.

Strictly suggestion-only: no writes to `TraceStore`, no touch on
production routing, policy, approval, or execution paths.

New file: `core/decision/brain/suggestion_feed.py`
Updated: `core/decision/brain/__init__.py`

---

## 2. Idempotency check

| Component | Status before B6-S6 |
|-----------|-------------------|
| `suggestion_feed.py` in `brain/` | **Did not exist** |
| Any module reading `brain_shadow_eval` into a per-decision feed | **Did not exist** |
| `BrainShadowRunner` emits `brain_shadow_eval` spans | ✅ on main (B6-S4) — **read-only input** |
| `BrainBaselineAggregator` / `BrainBaselineReport` | ✅ on main (B6-S5) — **used as gate** |
| `TraceStore.list_recent_traces` / `get_trace` | ✅ on main — **canonical reader** |

No parallel suggestion path existed — additive single-file step.

---

## 3. Design

### Pipeline

```
list_recent_traces(trace_limit)
  → for each trace: get_trace(trace_id)
  → spans where span_type == "brain_shadow_eval"
  → _summary_from_span(...)   (re-used from baseline_aggregator)
  → optional workflow_filter / version_filter
  → _entry_from_summary(summary):
        agreement | missing agent | same agent     → None
        genuine disagreement                       → BrainSuggestionEntry
  → score_divergence ≥ min_score_divergence        → keep
  → gate: baseline_report.recommendation == promote OR ungated
  → max_entries cap (optional)
  → BrainSuggestionFeed
```

### Pydantic schema (all `extra="forbid"`)

| Type | Purpose |
|------|---------|
| `BrainSuggestionEntry` | one actionable disagreement (per trace / span) |
| `BrainSuggestionFeed` | feed bundle — entries + scan/filter/gate context |

### Gating logic

| baseline_report | recommendation | `gated` | `gate_passed` | entries surfaced? |
|-----------------|---------------|---------|---------------|-------------------|
| `None` | — | `False` | `True` | yes (ungated) |
| present | `promote` | `True` | `True` | yes |
| present | `observe` | `True` | `False` | **no** (suppressed) |
| present | `reject`  | `True` | `False` | **no** (suppressed) |

Counts (`shadow_samples`, `disagreement_samples`) reflect the underlying
data regardless of gate state — only the `entries` list is suppressed.
This keeps the feed honest: operators can see *how many* suggestions
exist and *why* they are not being surfaced.

### Defensive parsing

Span parsing is delegated to `_summary_from_span` from
`baseline_aggregator.py` — same single-source-of-truth defensive shape:
malformed spans return `None` rather than raising, so span schema drift
cannot crash the feed.

### Why a separate module (not extended in `BrainBaselineAggregator`)?

- the aggregator answers *"is Brain good enough?"* (overall verdict);
- the feed answers *"which individual decisions would Brain change?"*.

Collapsing both into one class would mix per-decision action context
into aggregate metrics output and force the feed's promote-gate into
the aggregator's self-produced verdict (circular). Splitting them keeps
the aggregator pure and lets the feed consume the verdict cleanly.

---

## 4. Architecture-invariant checks

| Invariant | Status |
|-----------|--------|
| No parallel router / runtime / orchestrator | ✅ — pure read consumer |
| No second TraceStore / ModelRegistry | ✅ — `TraceStore` injected, only `list_recent_traces` + `get_trace` used |
| No model loading in feed | ✅ — Brain's decision already in the span |
| No business logic in CLI/UI/OpenAPI layer | ✅ — logic lives in `core/decision/brain/` |
| Read-only against canonical state | ✅ |
| Additive only | ✅ — one new file + `__init__.py` extension |
| No new heavy dependencies | ✅ — stdlib + pydantic |
| Defensive against span drift | ✅ — reuses `_summary_from_span` |
| Suggestion-only contract | ✅ — feed never touches `RoutingDecision`, gate defaults to `observe`-suppression |
| No shadow path for baseline verdict | ✅ — consumes `BrainBaselineReport` produced by B6-S5 |

---

## 5. Tests

**File:** `tests/decision/test_brain_suggestion_feed.py`
**Count:** 23 tests

| Test class | Tests | Focus |
|-----------|-------|-------|
| `TestEntryFromSummary` | 5 | disagreement→entry, agreement→None, None-agent on either side→None, same-agent-but-flag-drift→None |
| `TestBuildAgainstTraceStore` | 11 | empty store, non-shadow spans skipped, agreement-only yields no entries, genuine disagreement surfaced, `min_score_divergence` filter, workflow/version filter, `max_entries` cap, `trace_limit` cap, malformed span skipped, real `BrainShadowRunner` integration (single-candidate agreement path) |
| `TestBaselineGate` | 4 | ungated passes, `promote` surfaces, `observe` suppresses, `reject` suppresses — `disagreement_samples` preserved across suppression |
| `TestBuilderConstruction` | 1 | invalid `min_score_divergence` rejected on both sides of [0, 1] |
| `TestSchema` | 2 | entry + feed reject extra fields |

**Feed suite:** 23/23 green.
**Mandatory suite** (`tests/state tests/mcp tests/approval tests/orchestration tests/execution tests/decision tests/adapters tests/core tests/services tests/integration/test_node_export.py`): 1024 passed, 1 skipped (27s).
**Full suite:** 1524 passed, 1 skipped — +23 tests vs. B6-S5 (36s).
**py_compile:** clean on `suggestion_feed.py` and `__init__.py`.

---

## 6. Gate

| Check | Result |
|-------|--------|
| Scope correct (suggestion surface only) | ✅ |
| No production path touched | ✅ |
| No second TraceStore / ModelRegistry | ✅ |
| No model loaded by feed | ✅ |
| Gating explicit and documented | ✅ |
| Counts preserved even when gate suppresses | ✅ |
| Defensive against malformed spans | ✅ |
| Tests green (23 new + 1524 full) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 7. Phase 6 status after B6-S6

All three Phase-6 roadmap exit tasks for Brain v1 are now closed on main:

| Roadmap task | Step | Status |
|-------------|------|--------|
| *Zustandsrepräsentation / state schema / encoder* | B6-S1 | ✅ |
| *Trainingsdaten / Record Builder* | B6-S2 | ✅ |
| *Offline-Trainer + BRAIN_FEATURE_NAMES* | B6-S3 | ✅ |
| *Shadow-Mode für Brain-v1 einführen* | B6-S4 | ✅ |
| *Brain-v1 gegen heuristische Baseline evaluieren* | B6-S5 | ✅ |
| *Brain-v1 nur als Vorschlagsmodell ausrollen* | B6-S6 | ✅ |

End-to-end Phase-6 loop on main:

```
LearningRecord
  → BrainRecordBuilder        (B6-S2)
  → BrainRecord JSONL
  → BrainOfflineTrainer       (B6-S3)
  → ModelRegistry.register_brain (B6-S4)
  → BrainShadowRunner.evaluate → brain_shadow_eval span (B6-S4)
  → BrainBaselineAggregator   (B6-S5) → promote / observe / reject
  → BrainSuggestionFeedBuilder (B6-S6) → gated operator feed
```

Phase-6 exit criteria from the roadmap:

- *"das Decision-Netzwerk ist reproduzierbar besser als die Baseline"* —
  the infrastructure to measure and gate on this is complete; the
  empirical demonstration requires a real-traffic baseline run.
- *"es verletzt keine Safety- oder Governance-Invarianten"* — satisfied
  by construction: Brain owns no decision surface, gating defaults to
  suppress.
- *"es reduziert Fehlrouting, unnötige Kosten oder unnötige
  Genehmigungen messbar"* — measurable once the feed is populated from
  a real-traffic shadow run.

---

## 8. Next step

With Phase 6 closed in code, the natural next move is **Phase 7** or a
**cross-cutting Querschnitts-Workstream** from roadmap section 6:

1. **Phase 0/1/2 backfill audit** — before moving to Phase 7, verify
   Phase-0 consolidation and Phase-1 evaluability exit-criteria are
   actually met on main (replay-harness, policy-compliance suite,
   CI-gates). The roadmap explicitly lists Phase 0 and 1 as higher
   priority than Phase 7.

2. **Observability querschnittlich (§6.3)** — dashboard / report
   export for Brain aggregator + feed so operators can monitor the
   Phase-6 loop without bespoke queries.

3. **Phase 7 – Fortgeschrittenes Brain (hierarchisch, hybrid, simuliert
   trainierbar)** — only once a real-traffic baseline produces a
   `promote` verdict AND Phase 0/1 backfill is clean.

Recommend (1) first: the roadmap priority order is strict, and
confirming prior phases have no open gaps is a prerequisite for further
Brain work. Specifically: inventory whether *"Replay-Harness auf Basis
gespeicherter Traces"* and *"Policy-Compliance-Testkatalog"* from
Phase 1 exist on main in canonical form, or whether they still need a
Phase-1-S* step.
