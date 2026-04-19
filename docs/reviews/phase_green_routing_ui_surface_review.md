# §6.5 Green AI — `RoutingPage` catalog tab

**Branch:** `codex/phase_green_routing_ui_surface`
**Date:** 2026-04-19
**Scope:** Replaces the mock `Model` catalog on
`frontend/agent-ui/src/pages/RoutingPage.tsx` with a live read of
the canonical `/control-plane/routing/models` endpoint (Turn 17).
Closes the four-surface parity (CLI / HTTP / MCP / UI) for the
§6.5 routing-catalog observability track.

---

## 1. Roadmap position

Ninth turn of the §6.5 Green-AI track; fourth and final
observability-surface turn after CLI (Turn 16), HTTP (Turn 17) and
MCP (Turn 18):

| Turn | Commit | Surface |
|---|---|---|
| Turn 15 | `f73948fe` | Per-decision energy signal (descriptor / dispatcher / auditor) |
| Turn 16 | `64e175b8` | CLI column on `abrain routing models` |
| Turn 17 | `38026e94` | HTTP endpoint `/control-plane/routing/models` |
| Turn 18 | `8eb8e870` | MCP tool `abrain.list_routing_models` |
| **Turn 19 (this turn)** | — | UI tab on `RoutingPage` (agent-ui) |

The routing catalog now renders through every canonical surface —
operator CLI, external dashboard HTTP client, AI-tool MCP caller,
and the in-product React UI — with identical payload shape and
lineage / energy semantics.

---

## 2. Idempotency check

- `grep '/control-plane/routing/models\|RoutingModels\|energy_profile'
  frontend/agent-ui/src` before this turn — zero hits.
- `RoutingPage.tsx` existed but only ever rendered hard-coded
  `mockModels` (`id: 'gpt-4-turbo' / 'claude-3-opus' / 'local-llama'`)
  with a fictional `Model` shape (`version`, `pricing.currency`,
  `limits.requestsPerMinute`, `stats.successRate`) that has no
  corresponding field on the canonical `ModelDescriptor`.
- No second catalog reader in the frontend — `controlPlane.ts`
  had no `getRoutingModels` method.
- No parallel branch.

Consequence: a **replacement**, not a second truth.  The Schatten-
Wahrheit mock catalog is deleted; the live catalog takes its slot
on the existing `'models'` tab.

---

## 3. Design (as-built)

### 3.1 API client — `src/services/controlPlane.ts`

Added canonical TypeScript types mirroring the OpenAPI /
MCP structuredContent schema verbatim:

```ts
export interface RoutingModelEntry {
  model_id: string
  display_name: string
  provider: string
  tier: string
  purposes: string[]
  context_window: number
  cost_per_1k_tokens: number | null
  p95_latency_ms: number | null
  supports_tool_use: boolean
  supports_structured_output: boolean
  is_available: boolean
  quantization: RoutingModelQuantization | null
  distillation: RoutingModelDistillation | null
  energy_profile: RoutingModelEnergyProfile | null
}

export interface RoutingModelsResponse {
  total: number
  catalog_size: number
  filters: { tier, provider, purpose, available_only }
  tiers: Record<string, number>
  providers: Record<string, number>
  purposes: Record<string, number>
  models: RoutingModelEntry[]
}
```

And the fetcher:

```ts
controlPlaneApi.getRoutingModels(filters = {}) {
  const params = new URLSearchParams()
  if (filters.tier) params.set('tier', filters.tier)
  if (filters.provider) params.set('provider', filters.provider)
  if (filters.purpose) params.set('purpose', filters.purpose)
  if (filters.available_only) params.set('available_only', 'true')
  const query = params.toString()
  return request<RoutingModelsResponse>(
    `/control-plane/routing/models${query ? `?${query}` : ''}`
  )
}
```

- Types track the canonical service payload — every field is
  either required (reserved enum position) or nullable (honesty
  rule for `quantization` / `distillation` / `energy_profile` /
  `cost_per_1k_tokens` / `p95_latency_ms`).
- Request path reuses the shared `request<T>()` helper (same
  header + error-detail handling as every other endpoint in
  `controlPlaneApi`).
- Empty filters omit the query string entirely — the gateway and
  MCP defaults already normalise `None` to "no filter", so the UI
  doesn't need to repeat the rule.

### 3.2 Page — `src/pages/RoutingPage.tsx`

Replaced the `Model` mock interface and `mockModels` array with:

- `useState<RoutingModelsResponse | null>(null)` for the catalog
- `useState<string | null>(null)` for errors
- `useState<RoutingModelFilters>({})` for filter state
- `useEffect` that refetches whenever `catalogFilters` changes,
  with a `cancelled` flag to drop in-flight results on unmount

Matches the `useState` + `useEffect` pattern already used by
`AgentsPage.tsx` (the closest neighbour that also reads a
`controlPlaneApi.*` endpoint).  No new dependency on TanStack
Query — the rest of the page doesn't use it either.

`ModelCard` was rewritten to render canonical fields only:

- Header: `display_name`, `tier` badge, `model_id` (monospace),
  `provider`, `is_available` pill.
- Purposes row — every `purpose` enum rendered as a chip.
- Capability flags — `supports_tool_use`, `supports_structured_output`.
- Catalog stats — `context_window` (thousands-separated),
  `cost_per_1k_tokens` (`—` when null, `free` when `0`),
  `p95_latency_ms` (`—` when null).
- Dedicated **§6.5 lineage + energy section** — `quantization`,
  `distillation`, `energy_profile`, each rendered as
  *"not declared"* when `null`.  Mirrors the CLI's
  `TestEnergyProfileRendering` output conventions exactly.

Filter bar on the tab:

- Four controls: `tier` / `provider` / `purpose` selects +
  `available_only` checkbox — same four filters the service
  accepts.  No client-side search or other filters (doesn't
  exist on the backend).
- Each control sets state via `setCatalogFilters` which retriggers
  the effect.  Empty-string selections map to `null` — the gateway
  and MCP treat both as unset.

Catalog meta line (`total of catalog_size`) renders the service's
own counts verbatim — no UI-side re-counting.

The `'models'` tab overview-card count now reads
`availableCatalogModelCount = catalog.models.filter(m =>
m.is_available).length` via `useMemo`, instead of counting the
mock array — so the number is live and honest, and falls back to
`—` when the catalog hasn't loaded.

### 3.3 Non-changes

- `services/core.py`, `core/routing/`, `api_gateway/`,
  `interfaces/mcp/`, `scripts/abrain_control.py` — all untouched.
- Other pages (`AgentsPage`, `TracesPage`, `ApprovalsPage`,
  `PlansPage`, `Dashboard`, `SystemHealthPage`) — untouched.
- Zustand store — untouched (routing catalog is read-only and
  view-scoped, no cross-page reuse needed yet).
- `hooks/useApi.ts` — untouched (the existing `api.ts` client it
  wraps is a separate auth path; routing catalog uses the
  `controlPlaneApi` client, matching every other `control-plane/*`
  consumer).
- `package.json` — untouched (no new dependency).

---

## 4. Public-surface effect

**Replaces one tab's mock data with live data on the same page.**
Tab ordering, URL route, header, stats-overview layout, rules
tab and analytics tab are all unchanged.  The `'Available Models'`
overview card goes from a static `3` (count of mock entries with
`status === 'available'`) to a live count that matches `abrain
routing models --available` and `/control-plane/routing/models?
available_only=true`.

Renders on the models tab (real DEFAULT_MODELS catalog, 10
entries, `available_only=false`):

- Header — `total of catalog_size` line (e.g. `10 of 10 models
  match current filters`).
- Grid of `ModelCard`s — each with canonical fields,
  tier badge, capability chips and the dedicated §6.5 lineage +
  energy section.
- Empty state when filters yield zero matches.
- Error state with service `detail` string on `invalid_tier`
  etc. — the gateway raises HTTP 400 and the existing
  `request<T>()` helper surfaces the detail as the `Error.message`.

---

## 5. Invariants preserved

| Invariant | Status |
|---|---|
| Single catalog truth (`services.core.get_routing_models`) | ✅ — UI reads via HTTP, no second projection |
| No parallel architecture in the frontend | ✅ — uses existing `controlPlaneApi` + `useEffect` pattern |
| Decision → Governance → Approval → Execution → Audit → Orchestration | ✅ — read-only UI, no pipeline change |
| No business logic in the UI layer | ✅ — filter normalisation is "empty → unset"; everything else is service |
| `None`-signal honesty rule preserved | ✅ — `quantization` / `distillation` / `energy_profile` render *not declared* when null; `cost_per_1k_tokens` / `p95_latency_ms` render `—` when null |
| Stable-schema emission preserved | ✅ — every canonical field is present on the TypeScript type and rendered |
| No new runtime / store dependency | ✅ — same stdlib `fetch` via `request<T>()` helper |
| No new frontend dependency | ✅ — `package.json` untouched |
| CLI + HTTP + MCP + UI share one catalog projection | ✅ — all four call `get_routing_models` through the same service |
| Shadow-Wahrheit eliminated on the models tab | ✅ — mock `Model` interface + `mockModels` array deleted |
| Backend tests untouched + still green | ✅ — 1931 passed / 1 skipped (same as Turn 18 baseline) |

---

## 6. Artifacts

| File | Change |
|---|---|
| `frontend/agent-ui/src/services/controlPlane.ts` | + `RoutingModel*` types + `getRoutingModels` fetcher |
| `frontend/agent-ui/src/pages/RoutingPage.tsx` | Removed mock `Model` + `mockModels`; wired `useEffect` fetch; rewrote `ModelCard`; added filter bar on `'models'` tab; updated `Available Models` overview count |
| `docs/reviews/phase_green_routing_ui_surface_review.md` | this doc |

No descriptor change, no dispatcher change, no auditor change, no
service change, no HTTP change, no CLI change, no MCP change, no
catalog change, no test change.

---

## 7. Test coverage

No new automated tests.  `frontend/agent-ui` has no test runner
configured (`package.json` scripts: `dev`, `build`, `lint`,
`type-check`, `format`, `preview` — no `test` / vitest / jest).
Bringing up a test harness is outside the §6.5 scope and not
required by the existing `frontend/agent-ui` baseline.

Gates used:

- `npm run type-check` — TypeScript compilation of the full UI
  tree (tsc --noEmit), catches every shape mismatch against the
  canonical types.
- `npm run lint` — eslint `--max-warnings 0`.
- `npm run build` — full vite production build (tsc -b + vite
  build), catches any runtime-only import or syntax issue tsc
  alone might miss.
- Full Python suite — 1931 passed / 1 skipped.

Manual smoke against the existing `/control-plane/routing/models`
endpoint would confirm the live render end-to-end, but is not
required in-session.

---

## 8. Test gates

- `npm run type-check` — **pass** (clean, no output).
- `npm run lint` — **pass** (clean, no output).
- `npm run build` — **pass** (52 modules transformed, dist
  bundle produced, PWA service worker regenerated).
- Full backend suite (`tests/` with `test_*.py`) — **1931
  passed, 1 skipped, 6 warnings in 48.66s** — same as Turn 18
  baseline.

---

## 9. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (UI tab backed by `get_routing_models`) | ✅ |
| Idempotency rule honoured (no duplicate catalog / types) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical HTTP + service paths reinforced | ✅ |
| No business logic in the UI | ✅ |
| No Schatten-Wahrheit (mock `Model` deleted, live catalog on the same tab) | ✅ |
| `None`-signal honesty rule preserved | ✅ |
| Stable-schema emission preserved (all canonical fields rendered) | ✅ |
| Error surface clean (fetch error → red banner with service detail) | ✅ |
| No new frontend dependency | ✅ |
| Frontend gates green (type-check + lint + build) | ✅ |
| Backend suite green (no regressions) | ✅ |
| Documentation consistent with prior §6.5 + §263 turns | ✅ |
| **Merge-ready** | ✅ |

---

## 10. Next step

The §6.5 Green-AI track now has complete symmetric catalog
observability across every canonical caller surface:

| Surface | Turn | Catalog | Lineage | Energy |
|---|---|---|---|---|
| Auditor span | Turn 15 | — | ✅ | ✅ |
| CLI (`abrain routing models`) | Turn 7 / 16 | ✅ | ✅ | ✅ |
| HTTP (`/control-plane/routing/models`) | Turn 17 | ✅ | ✅ | ✅ |
| MCP (`abrain.list_routing_models`) | Turn 18 | ✅ | ✅ | ✅ |
| UI (`RoutingPage` → models tab) | **Turn 19** | ✅ | ✅ | ✅ |

Every in-session code lever for §6.5 catalog observability is
now pulled.  The only §6.5 work remaining is operator-seitig:

1. Shadow-mode real-traffic run of Brain-v1 via
   `BrainOperationsReporter` — unblocks Phase 6 E1/E3 + Phase 7.
   Cannot land in-session.
2. Real quant/distill benchmarks → `quality_delta_*` registration.
   Closes §Phase 4 §263 + §6.5 line 428 Eval-Ausführung.  Cannot
   land in-session.

Recommendation: stop here and surface the session state — every
code-side §6.5 observability surface is now live, and the
remaining two items require a running production environment.

No immediate code blockers on `main`.
