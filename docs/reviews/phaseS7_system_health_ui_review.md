# Phase S7 — System Health UI: Implementation Review

**Branch:** `codex/phaseS7-system-health-ui`
**Date:** 2026-04-13

---

## 1. Health Signals Now Visible

The new `/health` route in `frontend/agent-ui` gives operators a single page with:

| Signal | Source | What it shows |
|---|---|---|
| Overall status banner | `health.overall` | healthy / attention / degraded with colour coding |
| Pending approval count | `health.pending_approval_count` | Amber counter + inline list with risk levels |
| Paused plan count | `health.paused_plan_count` | Count + per-plan row in "Recent Plans" |
| Failed plan count | `health.failed_plan_count` | Count + per-plan row in "Recent Plans" |
| Degraded agent count | `health.degraded_agent_count` | Count + "Agent Health" section |
| Offline agent count | `health.offline_agent_count` | Count + amber badge in "Agent Health" section |
| System warnings | `system.warnings` | Shown as rose banners in Attention Items |
| Layer statuses | `system.layers[].status` | Grid of available / unavailable badges |
| Attention items list | `health.attention_items` | Prioritised warning/info feed |
| Governance signals | `recent_governance[].effect` | Signal feed: allow / deny / require_approval |

---

## 2. Backend Helpers Used / Extended

### Extended: `services/core.py — get_control_plane_overview`

Two additions — both pure derivation, no new IO:

1. **`_compute_health_summary(agents, approvals, plans, warnings, layers)`**
   - Private helper, called at the end of `get_control_plane_overview`
   - Derives `overall`, counts, `has_warnings`, `attention_items` from already-gathered lists
   - No DB access, no external calls

2. **Layer status computation from read-failure flags**
   - `_safe_read` failure flags already captured in `warnings`
   - S7 maps these to `"unavailable"` layer status (previously hardcoded `"available"` for all)
   - Layer statuses now reflect actual read success, not a static string

3. **`health` key added to overview response dict**
   - `get_control_plane_overview` now returns `"health": {...}` alongside existing keys

### Extended: `api_gateway/schemas.py`

Two new Pydantic models:
- `HealthAttentionItem` — single attention-item entry
- `ControlPlaneHealthSummary` — typed health section on the response

`ControlPlaneOverviewResponse` gets a required `health: ControlPlaneHealthSummary` field.

### No new endpoints added

The health data is served via the existing `GET /control-plane/overview` endpoint.
No second "operator API", no new route, no new FastAPI router.

---

## 3. Existing Control Plane Extended (Not Replaced)

| Layer | Change |
|---|---|
| `services/core.py` | `_compute_health_summary` helper + `health` key in overview response + layer status derivation |
| `api_gateway/schemas.py` | Two new schema models; one new field on existing response model |
| `frontend/agent-ui/src/services/controlPlane.ts` | `HealthSummary` + `HealthAttentionItem` types; `ControlPlaneOverview.health` field |
| `frontend/agent-ui/src/pages/SystemHealthPage.tsx` | New page, uses existing `controlPlaneApi.getOverview()` |
| `frontend/agent-ui/src/components/layout/Sidebar.tsx` | One new nav item: `{ path: '/health', name: 'Health', icon: 'H' }` |
| `frontend/agent-ui/src/App.tsx` | One new `<Route path="/health" element={<SystemHealthPage />} />` |

---

## 4. Operator Gaps Closed

| Gap (from inventory) | Closed by |
|---|---|
| All layers hardcoded "available" | Layer status now derived from `_safe_read` failure flags |
| `system.warnings` never shown | Shown as rose banners in Attention Items on Health page |
| No top-level health indicator | Overall status banner (healthy / attention / degraded) |
| No degraded-agent visibility | Agent Health section with availability badges |
| No paused vs. failed plan breakdown | Plan status counts in quick-stats strip + per-plan rows |
| No attention-needed summary | Attention Items feed with warning/info levels |
| No governance signal feed | Governance Signals card on Health page |
| No pending-approval highlight | Amber badge on pending-approval count; inline list |

---

## 5. Architecture Cross-Check

1. **No second UI built.** `SystemHealthPage.tsx` is one page component in the existing SPA. Same router, same `BrowserRouter`, same `controlPlaneApi` facade.

2. **No `monitoring/` revival.** No new observability stack, no Prometheus/Grafana clone, no background polling process.

3. **No business logic in React.** Health derivation (`overall`, `attention_items`, counts) lives entirely in `services/core._compute_health_summary`. The React component only renders what the API returns.

4. **Only the existing Control Plane extended.** `get_control_plane_overview` was extended. No second "operator API" endpoint was added.

5. **S7 is operator-valuable and architecturally clean.** Operators now have one tab showing a derived health status, attention items, and signal feeds — built entirely on already-available canonical data.

---

## 6. Test Results

| Suite | Result |
|---|---|
| `tests/services/test_control_plane_views.py` | 14 passed (10 existing + 9 new S7 health tests) |
| `tests/core/test_api_gateway_openapi.py` | 5 passed (updated mock to include health field) |
| Full prescribed suite (`tests/state`, `mcp`, `approval`, `orchestration`, `execution`, `decision`, `adapters`, `core`, `services`, `integration`) | 231 passed, 1 skipped (pre-existing) |
| Frontend `npm run type-check` | 0 errors |
| Frontend `npm run build` | Clean build |
| Frontend `npm run lint` | 0 warnings |
