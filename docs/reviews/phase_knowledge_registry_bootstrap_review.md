# Phase 3 / §6.4 – KnowledgeSourceRegistry persistence bootstrap review

**Branch:** `codex/phase_knowledge_registry_bootstrap`
**Date:** 2026-04-19
**Scope:** Add a persistent bootstrap loader for
`core.retrieval.registry.KnowledgeSourceRegistry` in `services.core`.
The registry stays the canonical in-process authority; the new loader
only populates it at first access from an operator-owned JSON file at
`ABRAIN_KNOWLEDGE_SOURCES_PATH`. Unblocks a future
`abrain governance provenance` operator surface over
`ProvenanceScanner`.

---

## 1. Roadmap position

Phase 0–6 closed on main; Phase 7 deferred. `ProvenanceScanner` has
been on main for a while, but **could not be safely surfaced as an
operator CLI** because the canonical `KnowledgeSourceRegistry` had no
persistence: every service-core invocation saw an empty registry, so a
`governance provenance` surface would always have reported zero
findings. This turn closes that gap by adding a bootstrap loader so
operators can declare the authoritative knowledge-source list in a
JSON file that is read once per process into the registry.

This turn is deliberately bootstrap-only: no CLI surface is added.
The follow-up turn (`abrain governance provenance`) can now drop
cleanly on top of a registry whose contents are deterministic.

---

## 2. Idempotency check

| Primitive | On main? | Persistence? |
|---|---|---|
| `KnowledgeSourceRegistry` | ☑ | ❌ before this turn — pure in-process |
| `KnowledgeSource` (pydantic model, `extra="forbid"`) | ☑ | — |
| `ProvenanceScanner` + `ProvenancePolicy` | ☑ | — (read-only over registry) |
| `ABRAIN_KNOWLEDGE_SOURCES_PATH` env var | ❌ | added this turn |
| JSON loader in `services.core` | ❌ | added this turn |

Idempotent checks before implementation:

- `grep knowledge_sources` / `grep ABRAIN_KNOWLEDGE_SOURCES_PATH` over
  `services/`, `scripts/`, `core/` — **no pre-existing loader**.
- The registry's docstring even calls out "Pure in-process store, no
  persistence. Persistence is a Phase-3 ingestion concern (R3 and
  later)." This is that Phase-3 ingestion concern.
- No duplicate loader added: the function is the only entry that
  constructs a registry from disk; the registry class itself remains
  unchanged.

---

## 3. Design

### 3.1 `services.core._get_knowledge_registry_state`

Mirrors the shape of the other canonical stateful accessors
(`_get_trace_state`, `_get_approval_state`, `_get_learning_state`):

- Caches on the function attribute `_state` for process lifetime.
- Reads `ABRAIN_KNOWLEDGE_SOURCES_PATH` (default
  `runtime/abrain_knowledge_sources.json`).
- If the file is absent, returns an empty registry with
  `file_present=False` and no warnings.
- If the file is present:
  - Unreadable JSON / OS errors surface as a single
    `knowledge_sources_unreadable: ...` load warning.
  - Non-list top-level surfaces `knowledge_sources_schema_invalid`.
  - Iterates entries with structured per-entry error attribution:
    - `entry_{idx}_schema_invalid` — not a JSON object
    - `entry_{idx}_validation_failed` — pydantic rejected the payload
    - `entry_{idx}_registration_failed` — `RegistrationError` from the
      registry (e.g. duplicate id, external without provenance)
  - Advisory warnings from successful `.register(source)` calls (PII
    without retention, external without license) are appended to
    `advisory_warnings`.
- `load_warnings` are logged as a single structured JSON line at
  WARNING level when any are present, matching the pattern used by
  other loaders on this module.

### 3.2 `services.core.get_knowledge_sources_status`

Minimal read-only status service (no CLI yet) so the bootstrap is
verifiable from Python without needing a future CLI surface:

- Returns `path`, `file_present`, `source_count`, `load_warnings`,
  `advisory_warnings`, and a compact `sources` list with the governance
  -relevant fields (`source_id`, `display_name`, `trust`,
  `source_type`, `pii_risk`, `has_provenance`, `has_license`,
  `retention_days`). Body strings are not exposed — the registry
  stores metadata, not corpus content, but the status function is
  intentionally small so it is safe to call even during cold starts.
- Returns fresh copies of the warnings lists so callers cannot mutate
  the cached state (test-enforced).

### 3.3 Registry model — unchanged

`KnowledgeSourceRegistry` itself is not touched. `register()` still
performs the exact same governance validation — the loader defers to
it, it does not re-implement it. `KnowledgeSource` is not touched
(still `extra="forbid"`, still pydantic-validated).

---

## 4. Public surface

```bash
# operator-owned file, one JSON list of KnowledgeSource objects
export ABRAIN_KNOWLEDGE_SOURCES_PATH=runtime/abrain_knowledge_sources.json
```

JSON schema (per entry) is `KnowledgeSource` verbatim:

```json
[
  {
    "source_id": "internal-docs",
    "display_name": "Internal Documentation",
    "trust": "trusted",
    "source_type": "document",
    "retention_days": 90
  }
]
```

No new env var for opt-out: a missing file is already the safe
default (empty registry, zero load warnings).

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| `KnowledgeSourceRegistry` is the sole source of truth | ✅ — loader registers through the canonical `.register()` entry |
| No parallel registration logic | ✅ — all governance checks still live in `registry.py` |
| `services/core.py` is the central service wiring | ✅ — loader lives next to other `_get_*_state` functions |
| `scripts/abrain` is the sole CLI | ✅ — no CLI surface added in this turn |
| Read-only over registry contents | ✅ — status service does not mutate |
| No new dependencies | ✅ — stdlib `json` + existing pydantic only |
| No new runtime / router / orchestrator | ✅ |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — retrieval registry sits on the Governance/Retrieval seam already defined in Phase 3 |

---

## 6. Artifacts

| File | Change |
|---|---|
| `services/core.py` | +1 accessor `_get_knowledge_registry_state`, +1 service `get_knowledge_sources_status` |
| `tests/core/test_knowledge_registry_bootstrap.py` | new — 11 unit tests |
| `docs/reviews/phase_knowledge_registry_bootstrap_review.md` | this doc |

---

## 7. Test coverage

11 tests, all green:

- **TestBootstrapLoader** (8)
  - missing file → empty registry, no warnings;
  - unreadable JSON → `knowledge_sources_unreadable:` warning,
    registry empty;
  - non-list top-level → `knowledge_sources_schema_invalid:` warning;
  - non-object entry → `entry_0_schema_invalid`, other entries still
    register;
  - pydantic validation failure → `entry_0_validation_failed`, next
    entry registers;
  - `RegistrationError` (external without provenance) →
    `entry_0_registration_failed`, next entry registers;
  - PII source without retention → registers with an advisory
    warning captured in `advisory_warnings`;
  - cache idempotency: re-writing the file does not cause a reload
    (`state_a is state_b`, `len(registry) == 1`).
- **TestStatusService** (3)
  - `get_knowledge_sources_status` exposes path, counts, sources
    with the expected governance fields;
  - returns a status even when the file is absent (file_present
    false, zero sources);
  - returns copies of warning lists so caller-side mutation cannot
    corrupt the cache.

The fixture helper `_fresh_core` clears the cached `_state` attribute
on each test so env-driven paths can be exercised independently.

---

## 8. Test gates

- Focused: `tests/core/test_knowledge_registry_bootstrap.py` —
  **11 passed**.
- Mandatory canonical suite: **1173 passed, 1 skipped** (+11 new).
- Full suite (`tests/` with `test_*.py`): **1759 passed, 1 skipped**
  (+11 new).
- `py_compile services/core.py` — clean.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (bootstrap-only, no new CLI, no new registry) | ✅ |
| Idempotency rule honoured (registry not rebuilt) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical service path reinforced (same `_get_*_state` shape) | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+11 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

With `KnowledgeSourceRegistry` now persistently loaded on first service
-core access, the follow-up turn is straightforward:

1. `abrain governance provenance` — wrap `ProvenanceScanner` over
   `_get_knowledge_registry_state()["registry"]`; add a CLI handler
   +renderer+subparser on the existing `governance` parent, matching
   the `retention` / `pii` shape. Expose `--require-retention-for-all`
   and per-trust-level overrides if needed; default policy mirrors the
   registry's registration-time checks.
2. Optional: surface `get_knowledge_sources_status` as
   `abrain governance sources` for operators to audit what the
   bootstrap loaded (zero findings vs. expected sources) ahead of
   running the provenance scanner.

Phase 7 remains blocked on a real-traffic `promote` verdict via
`abrain brain status`. This turn does not change that gate.
