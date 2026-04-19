# Phase 3 / §6.4 – `abrain governance sources` CLI surface review

**Branch:** `codex/phase_gov_sources_cli`
**Date:** 2026-04-19
**Scope:** Expose `services.core.get_knowledge_sources_status` as the
operator CLI surface `abrain governance sources` — a small read-only
twin to `governance provenance` that lets operators audit the
`KnowledgeSourceRegistry` bootstrap state *before* running the
scanner.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. Roadmap §6.4 (Governance)
is green. The previous turn shipped `abrain governance provenance`
wrapping `ProvenanceScanner`, and its review explicitly listed
`abrain governance sources` as the natural small follow-up:
operators running the scanner want to see what the bootstrap actually
loaded (`load_warnings`, `advisory_warnings`, `source_count`, raw
governance fields) before drawing conclusions from a zero-finding
report. This turn closes that gap.

Strictly operator-surface gap-fill — no new primitives, no new
persistence.

---

## 2. Idempotency check

| Primitive | On main? | Surfaced? |
|---|---|---|
| `services.core.get_knowledge_sources_status` | ☑ (bootstrap turn) | ❌ before this turn |
| `_get_knowledge_registry_state` | ☑ (bootstrap turn) | — |
| `abrain governance sources` subcommand | ❌ | added this turn |

Idempotent checks before implementation:

- `grep` for `governance sources` / `_handle_governance_sources` /
  `_render_governance_sources` over `scripts/` — no pre-existing
  surface.
- The service already existed (added in the bootstrap turn) and was
  only consumed by the bootstrap tests. No duplicate service added;
  the CLI just wraps it.
- No new registry accessor: the service reuses
  `_get_knowledge_registry_state()` and its process-lifetime cache.

---

## 3. Design

### 3.1 CLI handler

`_handle_governance_sources` is a near-empty pass-through — it calls
`core.get_knowledge_sources_status()` with no arguments and emits via
`_emit(...)`. No flags, no parsing: the status is a pure snapshot.

### 3.2 Renderer

`_render_governance_sources` follows the existing governance-surface
shape:

- header,
- path / file_present / source_count / warning counts block,
- load_warnings block (capped at 20) — only rendered when non-empty,
- advisory_warnings block (capped at 20) — only rendered when
  non-empty,
- compact per-source list capped at 40 with the governance-relevant
  fields (`source_id`, `display_name`, `trust`, `source_type`,
  `pii_risk`, `has_provenance`, `has_license`, `retention_days`).
  `retention=-` placeholder when unset.

No error branch — the underlying service never returns an error
payload (a missing file is the happy path with `file_present=False`,
`source_count=0`).

### 3.3 Subparser

```
abrain governance sources [--json]
```

Sits next to `retention`, `pii`, `provenance` on the existing
`governance` parent. Only `--json` (standard CLI convention).

---

## 4. Public surface

```bash
# Plain-text status — what did the bootstrap load?
abrain governance sources

# Machine-readable for pipelines (e.g. CI governance gate)
abrain governance sources --json
```

Sample text output (loaded bootstrap, clean):

```
=== Knowledge Sources Registry ===
Path:                 /.../abrain_knowledge_sources.json
File present:         True
Source count:         2
Load warnings:        0
Advisory warnings:    0

Sources (2):
  - docs  name=Internal Docs  trust=trusted   type=document  pii=False  prov=False  lic=True   retention=30
  - ext   name=Ext            trust=external  type=document  pii=False  prov=True   lic=False  retention=-
```

With a broken bootstrap file, `Load warnings:` is non-zero and the
listed warnings are shown verbatim so operators can fix the file and
retry.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| `KnowledgeSourceRegistry` sole knowledge-source truth | ✅ — service reads via `_get_knowledge_registry_state()` |
| `services/core.py` central service wiring | ✅ — no new service, only CLI wrapper |
| `scripts/abrain` sole CLI | ✅ — surface added on the existing `governance` parent |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — CLI sits on the Governance seam |
| Read-only over registry state | ✅ — no mutation |
| No business logic in CLI | ✅ — handler is pass-through, renderer is pure formatting |
| No new dependencies / no new runtime / no new persistence | ✅ |

---

## 6. Artifacts

| File | Change |
|---|---|
| `scripts/abrain_control.py` | +1 handler, +1 renderer, +1 subparser (`governance sources`) |
| `tests/core/test_abrain_cli_gov_sources.py` | new — 8 unit + integration tests |
| `docs/reviews/phase_gov_sources_cli_review.md` | this doc |

`services/core.py` unchanged.

---

## 7. Test coverage

8 tests, all green:

- **TestRenderer** (4)
  - header, path, counts, per-source line with `retention=N` and
    `retention=-`;
  - load_warnings + advisory_warnings blocks rendered when non-empty;
  - empty registry: `Source count: 0`, `(none)` placeholder;
  - warning blocks omitted entirely when lists are empty.
- **TestCliWiring** (2)
  - `abrain governance sources` delegates once to the service and
    renders the text output;
  - `--json` emits a JSON-dumpable payload round-trippable through
    `json.loads`.
- **TestServiceIntegration** (2)
  - real registry scan from a bootstrap JSON file (path, count,
    `load_warnings=[]`);
  - missing bootstrap file → `file_present=False`, empty sources list.

---

## 8. Test gates

- Focused: `tests/core/test_abrain_cli_gov_sources.py` — **8 passed**
  (0.98s).
- Mandatory canonical suite: **1192 passed, 1 skipped** (+8 new).
- Full suite (`tests/` with `test_*.py`): **1778 passed, 1 skipped**
  (+8 new).
- `py_compile scripts/abrain_control.py` — clean.
- CLI smoke: `python -m scripts.abrain_control governance sources --help`
  renders cleanly.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (CLI-only wrapper, no new service) | ✅ |
| Idempotency rule honoured (no duplicate status fn) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical service path reinforced (same `_emit(...)` + `_json_mode(...)` shape) | ✅ |
| Canonical CLI path reinforced (same governance-subcommand shape) | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+8 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

Roadmap §6.4 (Governance) is now fully surfaced as operator CLIs:
`retention`, `pii`, `provenance`, `sources`. Natural next turns:

1. `abrain learningops export` — destructive/writing scope: writes a
   curated `TrainingDataset` to disk. Needs its own review with
   explicit I/O invariants, dry-run default, and destructive-flag
   handling (analogue to `abrain governance retention --prune`).
2. Roadmap §6.5 residuals: only one unchecked item
   (*Quantisierung/Distillation für lokale Spezialmodelle
   evaluieren*) — research-shaped, not a quick operator-surface win.
3. Phase 7 remains blocked on a real-traffic `promote` verdict via
   `abrain brain status`. No change in this turn.
