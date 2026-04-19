# §6.2 Documentation audit — docs/ inventory

**Branch:** `codex/phase-doc-audit`
**Date:** 2026-04-19
**Scope:** every non-review Markdown file under `docs/`, classified as
**current** / **historical** / **experimental** with pointer to the
canonical replacement where applicable.

`docs/reviews/` (121 files) is deliberately excluded: review documents
are frozen per-phase artifacts that should not be retagged after the
fact. Their provenance is their date and the phase they reviewed.

---

## Classification rules

- **current** — canonical design / usage doc that describes an
  actively supported path on main. Safe to cite without caveats.
- **historical** — superseded by a canonical replacement; kept for
  provenance. Must link to its replacement.
- **experimental** — proposal or unshipped plan, or describes scope
  that has not yet landed. Must be clearly marked as experimental.

---

## Architecture — `docs/architecture/` (19 files)

| File | Tag | Canonical pointer / notes |
|---|---|---|
| `AGENT_MODEL_AND_FLOWISE_INTEROP.md` | current | Canonical `AgentDescriptor` + Flowise interop rules |
| `AUDIT_AND_EXPLAINABILITY_LAYER.md` | current | Phase K audit / explainability surface |
| `CANONICAL_REPO_STRUCTURE.md` | current | Phase O single source of truth for repo layout |
| `CANONICAL_RUNTIME_STACK.md` | current | Canonical runtime entrypoints and services |
| `CONTROL_PLANE_API_MAPPING.md` | current | Phase M control-plane HTTP surface mapping |
| `CONTROL_PLANE_TARGET_STATE.md` | current | Phase M operator-facing control plane scope |
| `DECISION_LAYER_AND_NEURAL_POLICY.md` | current | Decision layer + neural policy contract |
| `decisions/phase5_phase6.md` | historical | Phase 5/6 integration decision log — references `archive/legacy`. Kept for provenance; subsequent phases supersede the recommendations. |
| `EXECUTION_LAYER_AND_AGENT_CREATION.md` | current | Execution layer + agent creation contract |
| `GOVERNANCE_LAYER.md` | current | Governance layer canonical design |
| `HITL_AND_APPROVAL_LAYER.md` | current | Phase I HITL / approval contract |
| `MCP_V2_INTERFACE.md` | current | Canonical MCP V2 interface contract |
| `MULTI_AGENT_ORCHESTRATION.md` | current | Phase H multi-agent orchestration design |
| `NATIVE_DEV_AGENT_ADAPTERS.md` | current | Phase F1 native dev agent adapters |
| `PERSISTENT_STATE_AND_DURABLE_RUNTIME.md` | current | Phase N persistent state design — active |
| `PERSISTENT_STATE_STORAGE_DECISIONS.md` | current | Phase N storage decisions (SQLite / JSON) |
| `SETUP_AND_BOOTSTRAP_FLOW.md` | current | Canonical `scripts/setup.sh` bootstrap flow |
| `SETUP_ONE_LINER_FLOW.md` | current | Canonical `./scripts/abrain setup` flow |
| `WORKFLOW_ADAPTER_LAYER.md` | current | Phase F2 workflow-adapter (n8n / Flowise) contract |

---

## Guides — `docs/guides/` (2 files)

| File | Tag | Canonical pointer / notes |
|---|---|---|
| `API_USAGE.md` | current | Canonical HTTP API usage reference |
| `MCP_USAGE.md` | current | Canonical MCP V2 usage reference |

---

## Integrations — `docs/integrations/adminbot/` (6 files)

| File | Tag | Canonical pointer / notes |
|---|---|---|
| `ADMINBOT_AGENT_CONTRACT.md` | current | AdminBot agent contract |
| `AGENT_NN_ADMINBOT_INTEGRATION_PLAN.md` | current | Active integration plan — paths (`core/models/adminbot.py`, `adapters/adminbot/*`, `core/tools/*`) exist on main |
| `REVIEW_CHECKLIST.md` | current | Review checklist for AdminBot integration changes |
| `SECURITY_INVARIANTS.md` | current | AdminBot security invariants |
| `TOOL_SURFACE.md` | current | Default-agent-allowed AdminBot tool surface |
| `USAGE.md` | current | AdminBot integration usage guide |

---

## MCP — `docs/mcp/` (2 files)

| File | Tag | Canonical pointer / notes |
|---|---|---|
| `README.md` | current | Points to canonical `interfaces/mcp/*` + `docs/guides/MCP_USAGE.md` |
| `MCP_SERVER_USAGE.md` | historical | **Self-declared historical archive.** Canonical replacement: `docs/guides/MCP_USAGE.md`. Legacy V1 server code (`interfaces/mcp_v1/*`, `abrain-mcp-v1`) removed in Phase O. |

---

## Root — `docs/`

| File | Tag | Canonical pointer / notes |
|---|---|---|
| `ROADMAP_consolidated.md` | current | Canonical roadmap (this turn updates completion markers) |

---

## Summary

- **Total non-review docs inventoried:** 30
- **current:** 28
- **historical:** 2 (`docs/architecture/decisions/phase5_phase6.md`, `docs/mcp/MCP_SERVER_USAGE.md`)
- **experimental:** 0

**Experimental count is zero by construction:** unfinished or proposal-
stage design work lives either in `docs/reviews/*` (frozen per-phase
artifacts) or is not yet committed. Future proposal docs added under
`docs/architecture/` should carry an explicit `**Status:** Experimental`
header.

Historical docs are already self-marked: `MCP_SERVER_USAGE.md` has an
explicit "Diese Datei ist nur noch Archivdokumentation" header, and
`decisions/phase5_phase6.md` is under the `decisions/` subfolder which
by convention is append-only provenance. Neither needs a rewrite.

---

## Why `docs/reviews/` was excluded

Reviews are frozen, dated artifacts of a specific phase turn. Tagging
them as historical after the fact would be redundant (they are already
dated and scoped) and could invite rewrites that break the audit
trail. Each review links forward to subsequent reviews where needed;
that forward chain is the canonical replacement pointer for any
review whose conclusions have since been superseded.
