# Phase 3 / §6.4 – `abrain governance retention-prune` CLI surface review

**Branch:** `codex/phase_gov_retention_prune_cli`
**Date:** 2026-04-19
**Scope:** Expose the destructive `core.audit.retention_pruner.RetentionPruner`
as the operator CLI surface `abrain governance retention-prune`. Second
destructive-write CLI after `abrain learningops export`; reuses the same
dry-run-default / `--apply`-to-commit pattern. Closes the long-vertagte
§6.4 gap that every prior governance review explicitly flagged as
"destructive, out of scope".

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. Roadmap §6.4 (Data
Governance) has been green on the read-only side (`retention`, `pii`,
`provenance`, `sources`) since earlier turns; the destructive
`RetentionPruner` has been on main since `phase_gov_retention_pruner_review.md`
(commit `73f04bed`) but every governance-CLI turn deliberately
deferred it with the same note: *"RetentionPruner (destructive)
intentionally stays unreached for now"*. The preceding
`learningops export` turn (commit `98af2847`) established the
dry-run / `--apply` pattern; this turn applies the same pattern to
the retention pruner, so the §6.4 governance surface is now **fully
operator-reachable** — inspect + prune.

---

## 2. Idempotency check

| Primitive | On main? | Surfaced? |
|---|---|---|
| `RetentionScanner` + `RetentionPolicy` | ☑ | ☑ (via `governance retention`) |
| `RetentionPruner` + `RetentionPruneResult` | ☑ (commit `73f04bed`) | ❌ before this turn |
| `services.core.apply_retention_prune` | ❌ | added this turn |
| `abrain governance retention-prune` subcommand | ❌ | added this turn |

Idempotent checks before implementation:

- `grep` for `retention-prune` / `apply_retention_prune` /
  `_handle_governance_retention_prune` over `scripts/` + `services/` —
  no pre-existing surface.
- `grep` for `RetentionPruner` showed the primitive on main with a
  dedicated test file (`tests/audit/test_retention_pruner.py`), but no
  CLI/service wrapper.
- No parallel pruner added: the service constructs the canonical
  `RetentionPruner` and delegates `.prune(report, commit=apply)`.
- No parallel scanner: the service reuses the same `RetentionScanner`
  + `RetentionPolicy` shape as `get_retention_scan`.
- Existing `governance retention` CLI behaviour is untouched — the new
  command is a **new sibling subparser**, not a flag on the existing
  read-only command. This keeps the CLI invariant that a read-only
  command can never become destructive by a flag rename/typo.

---

## 3. Design

### 3.1 `services.core.apply_retention_prune`

Single entry that composes scanner + pruner, mirroring the sibling
`get_retention_scan`:

- Inputs: same retention-policy knobs as `get_retention_scan`
  (`trace_retention_days`, `approval_retention_days`, `trace_limit`,
  `keep_open_traces`, `keep_pending_approvals`) plus a single
  destructive-gate flag `apply` (default `False`).
- Flow:
  1. `_get_trace_state()` — if the TraceStore is absent, short-circuit
     with `error="trace_store_unavailable"` (same shape as other
     services).
  2. `RetentionPolicy(...)` + `RetentionScanner(...)` build the
     canonical `RetentionReport`.
  3. `RetentionPruner(...).prune(report, commit=bool(apply))` returns
     the canonical `RetentionPruneResult`.
  4. Payload = `result.model_dump(mode="json")` with the scanner
     report attached under `"report"` (so operators see the policy
     and totals that drove the prune) and an explicit `"apply"` field
     so the renderer can tell dry-run from applied without inferring.

The pruner itself trusts the scanner report and does not re-evaluate
policy — that invariant is preserved.

### 3.2 Dry-run vs apply contract

| Behaviour | dry-run (default) | `--apply` |
|---|---|---|
| Scanner read | ✅ | ✅ |
| Candidate list computed | ✅ | ✅ |
| `delete_trace` / `delete_request` invoked | ❌ | ✅ |
| Returned `dry_run` field | `True` | `False` |
| Returned `apply` field | `False` | `True` |
| `traces_deleted` / `approvals_deleted` semantics | "would be deleted" | "actually deleted" |
| Record in store after call | intact | removed |

In dry-run, `traces_deleted` reflects records that **would** be
deleted (the pruner's `_handle_trace` returns `get_trace(...) is not
None` under `dry_run=True`). The authoritative invariant is the
store state itself, which the integration tests enforce directly:
the trace is still present after a dry-run, and removed after an
applied call.

### 3.3 CLI shape

```
abrain governance retention-prune
    [--trace-retention-days N] [--approval-retention-days N]
    [--trace-limit N]
    [--include-open-traces] [--include-pending-approvals]
    [--apply]
    [--json]
```

Sits next to `retention`, `retention-prune` (new), `pii`, `provenance`,
and `sources` on the existing `governance` parent.

Handler clamps all `--*-days` and `--trace-limit` inputs via
`max(1, ...)` — same convention as `governance retention`.

### 3.4 Renderer

Two modes driven by `apply` + `dry_run` fields in the payload:

- `=== Governance Retention Prune (DRY-RUN) ===` with per-outcome
  lines (`[DEL ]` / `[SKIP]` markers, `dry_run=True`) and a trailing
  `dry-run (no record deleted; re-run with --apply to commit)` notice.
- `=== Governance Retention Prune (APPLIED) ===` with `dry_run=False`
  on every outcome and no dry-run notice.

Error payload: `[WARN] Retention prune unavailable: <error>` with
`detail=<trace_store_path>`.

Outcomes are capped at 40 lines with `... (N more)` tail, matching
the other governance renderers.

---

## 4. Public surface

```bash
# Dry-run: see which records a prune would touch (safe default)
abrain governance retention-prune --trace-retention-days 30

# Same policy, actually delete overdue records
abrain governance retention-prune --trace-retention-days 30 --apply

# CI: machine-readable dry-run summary as JSON
abrain governance retention-prune --json
```

Sample text (dry-run, one overdue trace):

```
=== Governance Retention Prune (DRY-RUN) ===
Executed at:              2026-04-01T12:00:00+00:00

Policy (from scanner):
  trace_retention_days:        30
  approval_retention_days:     30
  keep_open_traces:            True
  keep_pending_approvals:      True

Scanner totals:
  Trace candidates:            1
  Approval candidates:         0

Prune result:
  Trace candidates seen:       1
  Approval candidates seen:    0
  Traces deleted:              1
  Approvals deleted:           0

Outcomes (1):
  [DEL ] trace:t-...  dry_run=True

Status: dry-run (no record deleted; re-run with --apply to commit)
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| TraceStore sole trace/audit truth | ✅ — pruner operates on canonical `delete_trace` |
| ApprovalStore sole approval truth | ✅ — pruner operates on canonical `delete_request` |
| `RetentionScanner` / `RetentionPruner` unchanged | ✅ — no fields, no new governance checks |
| Scanner owns policy decisions; pruner trusts the report | ✅ — re-evaluation not introduced |
| `services/core.py` central service wiring | ✅ |
| `scripts/abrain` sole CLI | ✅ — surface added on existing `governance` parent |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — CLI sits on Governance over Audit |
| No business logic in CLI | ✅ — handler is pass-through, renderer is pure formatting |
| Destructive ops default to read-only / dry-run | ✅ — `--apply` is required to commit |
| Read-only `governance retention` unchanged | ✅ — new command is a separate subparser |
| No new heavy dependencies | ✅ — stdlib + pydantic only |
| No new runtime / no new stores | ✅ |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 service `apply_retention_prune` |
| `scripts/abrain_control.py` | +1 handler, +1 renderer, +1 subparser (`governance retention-prune`) |
| `tests/core/test_abrain_cli_gov_retention_prune.py` | new — 13 unit + integration tests |
| `docs/reviews/phase_gov_retention_prune_cli_review.md` | this doc |

---

## 7. Test coverage

13 tests, all green:

- **TestRenderer** (5)
  - dry-run summary: policy block, scanner totals, prune result,
    per-outcome `[DEL ]`/`[SKIP]` markers, dry-run notice;
  - applied summary: `APPLIED` header, `dry_run=False` on outcomes,
    no trailing dry-run notice;
  - `[SKIP]` marker rendered for `deleted=False` outcomes;
  - empty outcomes list renders `(none)`;
  - error payload rendered with `[WARN]` marker and trace-store path.
- **TestCliWiring** (4)
  - defaults delegation: all policy defaults forwarded with
    `apply=False`;
  - `--apply` plus every policy flag forwarded correctly;
  - non-positive `--*-days` and `--trace-limit` clamped to 1;
  - `--json` emits a JSON-dumpable payload.
- **TestServiceIntegration** (4)
  - missing TraceStore → `trace_store_unavailable`;
  - dry-run over a real TraceStore with an overdue trace: candidate
    counted, store still has the trace;
  - `apply=True` deletes only the overdue trace and leaves the fresh
    one intact;
  - `apply=True` on a store with no overdue traces is a no-op
    (empty outcomes, fresh trace still present).

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_gov_retention_prune.py` —
  **13 passed** (1.21s).
- Mandatory canonical suite: **1217 passed, 1 skipped** (+13 new).
- Full suite (`tests/` with `test_*.py`): **1803 passed, 1 skipped**
  (+13 new).
- `py_compile services/core.py scripts/abrain_control.py` — clean.
- CLI smoke: `python -m scripts.abrain_control governance retention-prune --help`
  renders cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (destructive op behind dry-run default + `--apply`) | ✅ |
| Idempotency rule honoured (no duplicate scanner/pruner/policy) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical service path reinforced (same `RetentionPolicy` + scanner chain) | ✅ |
| Canonical CLI path reinforced (new subparser on existing `governance` parent) | ✅ |
| Destructive write guarded | ✅ — `--apply` required; read-only `retention` command untouched |
| Mandatory suite green | ✅ |
| Full suite green (+13 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Roadmap §6.4 is now fully operator-surfaced: read-only inspection
(`retention`, `pii`, `provenance`, `sources`) and destructive
persistence / deletion (`learningops export`, `governance
retention-prune`). Natural next turns:

1. Roadmap §6.5 residual — *Quantisierung/Distillation für lokale
   Spezialmodelle evaluieren*. This is research-shaped, not a small
   operator-surface win; would need its own inventory turn before any
   implementation.
2. Phase 7 remains blocked on a real-traffic `promote` verdict via
   `abrain brain status`. No change in this turn. When a promote
   verdict lands, Phase 7 unblocks.
3. Optional smaller surfaces: `abrain governance retention-prune` now
   establishes the second destructive-CLI pattern. If operators want
   a bulk "approvals retention" variant (currently the same command
   handles both in one pass), that would be a small split — but today
   the single command is sufficient and not worth fragmenting.

No immediate blockers on main; all §6.4 governance gaps are closed.
