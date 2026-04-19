# §6.4 – Governance PII CLI surface review

**Branch:** `codex/phase_gov_pii_cli`
**Date:** 2026-04-19
**Scope:** `abrain governance pii` CLI subcommand backed by a new
`services.core.get_retention_pii_annotation` wrapper composing
`RetentionScanner` + `PiiDetector` via
`core.audit.pii.annotate_retention_candidates`.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. The §6.4 governance
primitives are all on main at the primitive level (`PiiDetector`,
`RetentionScanner`, `RetentionPruner`, `ProvenanceScanner`,
`DatasetSplitter`). The previous turn closed the operator-surface gap
for `RetentionScanner` (`abrain governance retention`); this turn
closes it for `PiiDetector`.

The chosen surface is the **compositional** one: `PiiDetector` is
already paired with `RetentionScanner` via the
`annotate_retention_candidates` helper inside `core.audit.pii`. Wrapping
that helper (rather than the bare detector) gives operators the
high-leverage answer "*which retention candidates also contain PII?*"
in one call, mirroring the Phase-6 `BrainOperationsReporter`
composition pattern (baseline + suggestion-feed bundled).

---

## 2. Idempotency check

| Primitive | On main? | Operator surface? |
|---|---|---|
| `RetentionScanner` | ☑ | ☑ (last turn — `abrain governance retention`) |
| `PiiDetector` + `annotate_retention_candidates` | ☑ (commit `ffa47a08`) | ❌ — closed by this turn |
| `RetentionPruner` | ☑ | ❌ — destructive, out of scope |
| `ProvenanceScanner` | ☑ | ❌ — separate next turn |
| `EnergyEstimator` / `AgentPerformanceReport` | ☑ | ❌ — `ops` parent subparser, separate turn |
| `DatasetSplitter` | ☑ | ❌ — LearningOps consumer |

The composer `annotate_retention_candidates` is consumed verbatim — no
detection / scanning logic is duplicated.

---

## 3. Design

### 3.1 `services.core.get_retention_pii_annotation`

```python
def get_retention_pii_annotation(
    *,
    trace_retention_days: int = 90,
    approval_retention_days: int = 90,
    trace_limit: int = 10_000,
    keep_open_traces: bool = True,
    keep_pending_approvals: bool = True,
    enabled_categories: list[str] | None = None,
) -> Dict[str, Any]: ...
```

- Reuses canonical `_get_trace_state()` + `_get_approval_state()`.
- Builds a `RetentionPolicy` from the supplied governance window (same
  knobs as `get_retention_scan`), runs `RetentionScanner.scan(...)`,
  then constructs a `PiiPolicy` (default = built-in conservative set;
  `enabled_categories=None` → `DEFAULT_PII_CATEGORIES`) and a
  `PiiDetector`.
- Calls `annotate_retention_candidates(...)` to scope the PII scan to
  the records already flagged by retention.
- Returns `{retention_report, pii_annotation, policy}` — both source
  reports are preserved verbatim so the JSON consumer can drill into
  either side without a second call.
- Defensive trace-store-unavailable error payload mirrors the existing
  `brain status` / `governance retention` pattern.

### 3.2 `scripts/abrain_control.py`: `governance pii` subcommand

Added under the existing `governance` parent subparser (introduced last
turn for `retention`). Flags:

- `--trace-retention-days`, `--approval-retention-days`,
  `--trace-limit` — same retention knobs as `governance retention`,
  clamped `>= 1`.
- `--include-open-traces`, `--include-pending-approvals` — flip
  `keep_*` defaults.
- `--categories` — comma-separated list; whitespace and empty entries
  are stripped. Omitted → service uses
  `core.audit.pii.DEFAULT_PII_CATEGORIES`.
- `--json` — machine-readable mode.

Renderer surfaces:

- header + policy line (`enabled_categories`),
- retention totals (so operators see the candidate denominator),
- PII totals (`total_candidates`, `candidates_with_findings`,
  per-category counts, sorted),
- flagged candidate list (capped at first 20, with overflow tail).

Error payloads render as `[WARN] PII scan unavailable: <error>`.

---

## 4. Public surface

```bash
abrain governance pii [--trace-retention-days N] \
                       [--approval-retention-days N] \
                       [--trace-limit M] \
                       [--include-open-traces] \
                       [--include-pending-approvals] \
                       [--categories email,ipv4,...] \
                       [--json]
```

Exit code is always `0`; error payloads route through the renderer.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| TraceStore is the sole trace truth | ✅ — `_get_trace_state()` only |
| ApprovalStore is the sole approval truth | ✅ — `_get_approval_state()` only |
| `services/core.py` is the central service wiring | ✅ |
| `scripts/abrain` is the sole CLI | ✅ |
| Read-only — no mutation of either store | ✅ — composer is documented read-only |
| No new dependencies | ✅ |
| `PiiDetector` / `RetentionScanner` semantics unchanged | ✅ — wrapper only |
| No second policy surface for PII or retention | ✅ — both policies built from CLI flags only |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only on Audit/Approval tail |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 function `get_retention_pii_annotation` |
| `scripts/abrain_control.py` | +1 subaction (`governance pii`), +1 handler, +1 renderer |
| `tests/core/test_abrain_cli_governance_pii.py` | new — 9 unit tests |
| `docs/reviews/phase_gov_pii_cli_review.md` | this doc |

---

## 7. Test coverage

9 tests, all green:

- **TestRenderer** (3) — populated annotation; "no findings" path
  renders `(none)` for both category counts and flagged list; error
  payload surfaces trace_store path.
- **TestCliWiring** (6)
  - delegates to `services.core.get_retention_pii_annotation` with
    parsed args (defaults: `enabled_categories=None`, both
    `keep_*=True`);
  - `--categories " email , ipv4 , ,api_key"` splits + trims to
    `["email", "ipv4", "api_key"]`;
  - `--include-*` flags flip `keep_*` to `False`;
  - `--json` mode emits a JSON-loadable composite payload;
  - retention day / trace-limit minimums clamp to `1`;
  - service error payload surfaces via `[WARN] PII scan unavailable`.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_governance_pii.py` —
  **9 passed**.
- Mandatory canonical suite: **1207 passed, 1 skipped**
  (+9 vs. last turn's 1198 baseline).
- Full suite (`tests/` with `test_*.py`): **1706 passed, 1 skipped**
  (+9 vs. last turn's 1697 baseline).
- CLI smoke: `bash scripts/abrain --version` ok;
  `python -m scripts.abrain_control governance pii --help` renders
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
| Full suite green (+9 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Same gap-fill pattern remains for:

1. `abrain governance provenance` — wrap `ProvenanceScanner` over
   `KnowledgeSourceRegistry` (read-only); closes the last §6.4 primitive
   without an operator surface.
2. `abrain ops cost` / `abrain ops energy` — wrap
   `AgentPerformanceReport` and `EnergyEstimator` over
   `PerformanceHistoryStore`; introduces a new `ops` parent subparser
   and closes the §6.5 operator gap.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate.
