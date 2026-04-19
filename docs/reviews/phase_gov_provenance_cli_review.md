# Phase 3 / §6.4 – `abrain governance provenance` CLI surface review

**Branch:** `codex/phase_gov_provenance_cli`
**Date:** 2026-04-19
**Scope:** Expose `core.retrieval.provenance.ProvenanceScanner` as the
operator CLI surface `abrain governance provenance`, wrapping it over
the persistently bootstrapped `KnowledgeSourceRegistry` from the
preceding turn. Handler, renderer and subparser mirror the existing
`governance retention` / `governance pii` shape.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. The previous turn closed
the bootstrap gap by adding `ABRAIN_KNOWLEDGE_SOURCES_PATH` and
`_get_knowledge_registry_state()` to `services.core`. That made the
registry deterministic across process restarts and unblocked this
turn: `ProvenanceScanner` now has real input to scan, so a
governance CLI surface over it returns meaningful findings instead of
always reporting an empty registry.

This turn is strictly operator-surface gap-fill — no new primitives,
no new persistence. All governance logic still lives in
`core.retrieval.provenance`.

---

## 2. Idempotency check

| Primitive | On main? | Surfaced? |
|---|---|---|
| `ProvenanceScanner` + `ProvenancePolicy` | ☑ | ❌ before this turn |
| `KnowledgeSourceRegistry` bootstrap loader | ☑ (prev. turn) | — |
| `services.core.get_provenance_report` | ❌ | added this turn |
| `abrain governance provenance` subcommand | ❌ | added this turn |

Idempotent checks before implementation:

- `grep -n "governance provenance\|get_provenance_report\|ProvenanceScanner"`
  over `services/core.py` + `scripts/abrain_control.py` — no
  pre-existing surface (only the forward-reference in the bootstrap
  review).
- No parallel policy or scanner implementation added: the service
  constructs `ProvenancePolicy` + `ProvenanceScanner` directly and
  delegates `.scan()`; no shadow governance checks.
- No new registry accessor: the service reuses
  `_get_knowledge_registry_state()` verbatim, honouring its process
  -lifetime cache.

---

## 3. Design

### 3.1 `services.core.get_provenance_report`

Mirrors the signature of other `get_*_report` services (pure inputs,
pure dict return):

- `require_provenance_for: list[str] | None` — trust levels as strings
  (CLI-friendly); `None` falls back to the registry's default
  enforcement set (`external`, `untrusted`).
- `require_license_for: list[str] | None` — same shape, same default.
- `require_retention_for_pii: bool = True` — matches
  `KnowledgeSourceRegistry.register()`'s advisory.
- `require_retention_for_all: bool = False` — operator-strictness knob.

Flow:

1. Coerce string trust-level lists to `SourceTrust` enum members.
   Unknown values surface as a single-return error payload
   `{"error": "provenance_policy_invalid", "detail": ...}` — the
   service never raises into the CLI.
2. Construct `ProvenancePolicy`; any pydantic `ValidationError` maps
   to the same error payload.
3. Pull the registry + load/advisory warnings from
   `_get_knowledge_registry_state()` (no re-bootstrap).
4. Run `ProvenanceScanner(...).scan()`, dump the report with
   `model_dump(mode="json")`, and attach a `registry` block with
   `path`, `file_present`, `load_warnings`, `advisory_warnings` so
   operators can see what the scan actually covered.

### 3.2 `scripts/abrain_control._handle_governance_provenance` / `_render_governance_provenance`

- Handler parses comma-separated trust-level lists (strips whitespace,
  drops empties), passes retention flags through, and delegates to
  `services.core.get_provenance_report`.
- Renderer follows the existing governance-surface shape:
  - header, registry source block (path, file_present, warning counts),
  - policy block with trust-level lists joined by `, ` (or `(default)`
    when the operator did not override),
  - totals block (sources_scanned, compliant_sources,
    sources_with_findings),
  - sorted finding-counts histogram with `(none)` fallback,
  - optional load-warnings block capped at 20,
  - compact per-source list capped at 40 with `[OK  ]` / `[FAIL]`
    markers and indented `* kind: message` finding lines.
- Error payloads render as `[WARN] Provenance report unavailable: …`
  + `detail=` line; CLI always exits 0 (standard for this surface).

### 3.3 Subparser

Added to the existing `governance` parent (next to `retention` and
`pii`):

```
abrain governance provenance [--require-provenance-for L[,L...]]
                             [--require-license-for L[,L...]]
                             [--require-retention-for-pii |
                              --no-require-retention-for-pii]
                             [--require-retention-for-all]
                             [--json]
```

---

## 4. Public surface

```bash
# Default policy (mirrors registry registration checks)
abrain governance provenance

# Operator strictness: require retention on every source
abrain governance provenance --require-retention-for-all

# Narrow provenance enforcement to external only
abrain governance provenance --require-provenance-for external --json
```

Output (text mode, one `ext` finding):

```
=== Governance Provenance Report ===

Registry:
  Path:                 /.../abrain_knowledge_sources.json
  File present:         True
  Load warnings:        0
  Advisory warnings:    0

Policy:
  require_provenance_for:      external, untrusted
  require_license_for:         external, untrusted
  require_retention_for_pii:   True
  require_retention_for_all:   False

Totals:
  Sources scanned:       2
  Compliant sources:     1
  Sources with findings: 1

Finding counts (2):
  - license_missing: 1
  - provenance_missing: 1

Sources (2):
  [OK  ] docs   (trust=trusted)
  [FAIL] ext    (trust=external)
    * provenance_missing: Source 'ext' (trust=external) has no provenance declared.
    * license_missing:    Source 'ext' (trust=external) has no license declared.
```

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| `KnowledgeSourceRegistry` sole knowledge-source truth | ✅ — service reads via `_get_knowledge_registry_state()` |
| `ProvenanceScanner` / `ProvenancePolicy` unchanged | ✅ — no new fields, no new governance checks |
| `services/core.py` central service wiring | ✅ — new `get_provenance_report` lives next to siblings |
| `scripts/abrain` sole CLI | ✅ — surface added on the existing `governance` parent |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — CLI sits on the Governance seam |
| Read-only over registry state | ✅ — no registry mutation |
| No new dependencies / no new runtime / no new persistence | ✅ |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 service `get_provenance_report` |
| `scripts/abrain_control.py` | +1 handler, +1 renderer, +1 subparser (`governance provenance`) |
| `tests/core/test_abrain_cli_gov_provenance.py` | new — 11 unit + integration tests |
| `docs/reviews/phase_gov_provenance_cli_review.md` | this doc |

---

## 7. Test coverage

11 tests, all green:

- **TestRenderer** (4)
  - totals, policy, statuses, per-finding detail lines;
  - load-warnings block only rendered when present (count + capped list);
  - empty registry: `(none)` placeholders for both counts and sources;
  - error payload: rendered with warning marker + detail.
- **TestCliWiring** (3)
  - defaults delegation: `None/None/True/False` forwarded verbatim;
  - comma-list parsing strips whitespace and empties; retention flags
    flip correctly; `--require-retention-for-all` passes through;
  - `--json` mode emits the raw service payload (JSON-dumpable).
- **TestServiceIntegration** (4)
  - unknown trust level → `provenance_policy_invalid` error payload;
  - real registry scan from bootstrap JSON: ext without license →
    `license_missing: 1`, docs clean;
  - `require_retention_for_all=True` widens findings to
    `retention_missing: 1` on a retention-less trusted source;
  - bootstrap schema warnings (non-list JSON) propagate into
    `report["registry"]["load_warnings"]`.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_gov_provenance.py` —
  **11 passed** (2.35s).
- Mandatory canonical suite: **1184 passed, 1 skipped** (+11 new).
- Full suite (`tests/` with `test_*.py`): **1770 passed, 1 skipped**
  (+11 new).
- `py_compile services/core.py scripts/abrain_control.py` — clean.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (operator-surface gap-fill only) | ✅ |
| Idempotency rule honoured (no duplicate scanner / policy) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical service path reinforced (same `get_*_report` shape) | ✅ |
| Canonical CLI path reinforced (same governance-subcommand shape) | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+11 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

With `abrain governance provenance` now surfaced, natural next turns:

1. `abrain governance sources` — surface `get_knowledge_sources_status`
   as a read-only CLI so operators can audit what the bootstrap
   actually loaded (load_warnings, advisory_warnings, per-source
   governance fields) *before* running the scan. Small, single-file
   scope; same renderer/handler/subparser shape.
2. `abrain learningops export` — destructive/writing scope (writes a
   curated dataset to disk); warrants its own review with explicit
   I/O invariants and dry-run guarantees.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate.
