# §6.4 – Governance Retention CLI surface review

**Branch:** `codex/phase_gov_retention_cli`
**Date:** 2026-04-19
**Scope:** `abrain governance retention` CLI subcommand backed by a new
`services.core.get_retention_scan` wrapper around `RetentionScanner`.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred until a real-traffic
`promote` verdict from `BrainOperationsReporter`. The roadmap §6.4
"Daten und Governance" items are all checked at the **primitive** level
(`RetentionScanner`, `RetentionPruner`, `PiiDetector`,
`ProvenanceScanner`, `DatasetSplitter`), but a `services/core.py` /
`scripts/abrain` audit confirmed **no operator surface wraps any of the
§6.4 governance primitives**:

```
$ rg 'PiiDetector|ProvenanceScanner|RetentionScanner|RetentionPruner' \
     services/core.py scripts/abrain_control.py
(no matches)
```

That mirrors the gap we closed last turn for `BrainOperationsReporter`
with `abrain brain status`. This turn applies the same pattern to the
most operator-essential §6.4 primitive — the read-only retention
scanner — so retention candidates become reviewable from the canonical
CLI without writing Python.

`RetentionPruner` (destructive) intentionally stays unreached for now:
the scanner is a precondition for any pruning workflow, and a scanner
surface lets operators dial in a policy and dry-run it before any
write-side surface is wired.

---

## 2. Idempotency check

Per master-prompt section C:

| Primitive | On main? | Operator surface? |
|---|---|---|
| `RetentionScanner` | ☑ (commit `31f315fb`) | ❌ — closed by this turn |
| `RetentionPruner` | ☑ (commit `73f04bed`) | ❌ — out of scope (destructive) |
| `PiiDetector` | ☑ (commit `ffa47a08`) | ❌ — separate next turn |
| `ProvenanceScanner` | ☑ (commit `da37347c`) | ❌ — separate next turn |
| `DatasetSplitter` | ☑ (commit `a89156e4`) | ❌ — LearningOps consumer |
| `EnergyEstimator` | ☑ (commit `94fcb2f8`) | ❌ — §6.5 surface, separate turn |
| `AgentPerformanceReport` | ☑ (commit `bd157ef5`) | ❌ — §6.5 surface, separate turn |

No part of this turn rebuilds existing primitive code; the
`RetentionScanner` is consumed verbatim.

---

## 3. Design

Two thin, additive layers — both read-only:

### 3.1 `services.core.get_retention_scan`

```python
def get_retention_scan(
    *,
    trace_retention_days: int = 90,
    approval_retention_days: int = 90,
    trace_limit: int = 10_000,
    keep_open_traces: bool = True,
    keep_pending_approvals: bool = True,
) -> Dict[str, Any]: ...
```

- Reuses the canonical `_get_trace_state()` and `_get_approval_state()`
  accessors — **no second TraceStore / ApprovalStore wiring**.
- Returns `{"error": "trace_store_unavailable", "trace_store_path": ...}`
  if no TraceStore is wired (matches the `brain status` defensive
  pattern; ApprovalStore is always created on first access so no
  parallel guard is needed).
- Constructs a fresh `RetentionPolicy` per call from the supplied scan
  parameters, hands it to `RetentionScanner`, calls `.scan(...)` and
  returns `report.model_dump(mode="json")` — same serialisation contract
  as the rest of `services.core`.

### 3.2 `scripts/abrain_control.py`: `governance retention` subcommand

- New `governance` parent subparser added before `health` (mirrors
  `brain` parent layout from the previous turn).
- Single action `retention` with flags:
  - `--trace-retention-days` (default 90, clamped `>= 1`)
  - `--approval-retention-days` (default 90, clamped `>= 1`)
  - `--trace-limit` (default 10000, clamped `>= 1`)
  - `--include-open-traces` (flips `keep_open_traces` to False)
  - `--include-pending-approvals` (flips `keep_pending_approvals` to False)
  - `--json` for machine-readable mode
- `_render_governance_retention(payload)` emits a human-readable
  lagebericht: header, policy block, totals, candidate list (capped to
  the first 20 with a "... (N more)" tail). Error payload renders as
  `[WARN] Retention scan unavailable: <error>`.

Renderer surface (sample):

```
=== Governance Retention Report ===
Generated at:        2026-04-19T00:00:00+00:00
Evaluation time:     2026-04-19T00:00:00+00:00
Trace scan limit:    5000

Policy:
  trace_retention_days:    30
  approval_retention_days: 14
  keep_open_traces:        True
  keep_pending_approvals:  True

Totals:
  Traces scanned:      100
  Approvals scanned:   25
  Trace candidates:    1
  Approval candidates: 1

Candidates (2):
  - [trace] trace-1  age=45.70d  retention=30d
  - [approval] appr-1  age=22.00d  retention=14d
```

---

## 4. Public surface

```bash
abrain governance retention [--trace-retention-days N] \
                             [--approval-retention-days N] \
                             [--trace-limit M] \
                             [--include-open-traces] \
                             [--include-pending-approvals] \
                             [--json]
```

Exit code is always `0`. Error payloads surface via the renderer (same
convention as `brain status`, `health`, `runtime`).

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| TraceStore is the sole trace truth | ✅ — `_get_trace_state()` only |
| ApprovalStore is the sole approval truth | ✅ — `_get_approval_state()` only |
| `services/core.py` is the central service wiring | ✅ |
| `scripts/abrain` is the sole CLI | ✅ |
| Read-only, no destructive ops | ✅ — pruning stays in `RetentionPruner` |
| No new dependencies | ✅ |
| `RetentionScanner` semantics unchanged | ✅ — wrapper only |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only on Audit/Approval tail |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 function `get_retention_scan` |
| `scripts/abrain_control.py` | +1 subparser (`governance retention`), +1 handler, +1 renderer |
| `tests/core/test_abrain_cli_governance.py` | new — 8 unit tests |
| `docs/reviews/phase_gov_retention_cli_review.md` | this doc |

---

## 7. Test coverage

8 tests, all green:

- **TestRenderer** (3) — populated report; empty candidate list rendered
  as `(none)`; error payload surfaces trace_store path.
- **TestCliWiring** (5)
  - delegates to `services.core.get_retention_scan` with parsed args;
  - `--include-open-traces` / `--include-pending-approvals` flip the
    `keep_*` defaults to `False`;
  - `--json` mode emits a JSON-loadable payload;
  - `--trace-retention-days 0`, `--approval-retention-days -5`,
    `--trace-limit 0` are all clamped to `1`;
  - service error payload surfaces via the `[WARN] Retention scan
    unavailable` render path.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_governance.py` — **8 passed**.
- Mandatory canonical suite (`tests/state tests/mcp tests/approval
  tests/orchestration tests/execution tests/decision tests/adapters
  tests/core tests/governance tests/services
  tests/integration/test_node_export.py`): **1198 passed, 1 skipped**
  (+8 vs. last turn's 1190 baseline).
- Full suite (`tests/` with `test_*.py`): **1697 passed, 1 skipped**
  (+8 vs. last turn's 1689 baseline).
- CLI smoke: `bash scripts/abrain --version` ok;
  `python -m scripts.abrain_control governance retention --help` renders
  argparse help cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (additive operator surface, no new logic) | ✅ |
| Idempotency rule honoured (no §6.4 primitive rebuilt) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical CLI / services / store paths reinforced | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+8 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Same gap-fill pattern remains for the other §6.4 / §6.5 primitives:

1. `abrain governance pii` — wrap `PiiDetector` (read-only).
2. `abrain governance provenance` — wrap `ProvenanceScanner` over
   `KnowledgeSourceRegistry` (read-only).
3. `abrain ops cost` / `abrain ops energy` — wrap
   `AgentPerformanceReport` and `EnergyEstimator` over
   `PerformanceHistoryStore`.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate; it only
extends operator visibility into the §6.4 governance surface.
