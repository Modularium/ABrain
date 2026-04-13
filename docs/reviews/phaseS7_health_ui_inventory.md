# Phase S7 — System Health UI: Inventory

**Branch:** `codex/phaseS7-system-health-ui`
**Date:** 2026-04-13
**Scope:** Extend the existing `frontend/agent-ui` control plane with an operator-facing System Health tab. No second UI, no new runtime, no monitoring revival.

---

## 1. What the UI Already Shows (today)

| Page | Route | Data source | Operator value |
|---|---|---|---|
| Overview / Dashboard | `/` | `GET /control-plane/overview` | Summary counts (agents, approvals, traces, plans, governance); layer list; pending approvals; recent traces; governance decisions |
| Traces | `/traces` | `GET /control-plane/traces` | Recent audit traces with status |
| Approvals | `/approvals` | `GET /control-plane/approvals` | Pending approvals list, approve/reject actions |
| Plans | `/plans` | `GET /control-plane/plans` | Recent plan executions with status |
| Agents | `/agents` | `GET /control-plane/agents` | Agent catalog with capabilities, trust, availability |
| Settings | `/settings` | local store | API URL, theme |

---

## 2. Operator Gaps (today)

| Gap | Where it hurts |
|---|---|
| All system layers hardcoded `"available"` | Operator cannot see when a layer is actually unhealthy |
| `system.warnings` collected but never surfaced in UI | Silent failure signals ignored |
| No top-level health/readiness indicator | Operator must mentally scan all tabs |
| No degraded-agent count in summary | DEGRADED agents blend into the catalog |
| No paused vs. failed plan breakdown | Plan counts are undifferentiated |
| No attention-needed summary | No single place to see "what needs action" |
| Overview page shows data but no health interpretation | Data without signal priority |
| No fallback / policy-deny signal feed | S4 fallbacks invisible to operator |

---

## 3. Existing Canonical Signals Already Available

### Backend (`services/core.py` + `get_control_plane_overview`)
| Signal | How produced | Available today? |
|---|---|---|
| `system.layers[].status` | Hardcoded `"available"` | ✓ (but static) |
| `system.warnings` | `_safe_read` error captures | ✓ (never shown in UI) |
| `system.governance` | `get_governance_state()` | ✓ (never shown in UI) |
| Agent `availability` field | `AgentDescriptor.availability` (UNKNOWN/ONLINE/DEGRADED/OFFLINE) | ✓ in agents list |
| `pending_approvals` list | `list_pending_approvals()` | ✓ |
| `recent_plans[].status` | `list_recent_plans()` | ✓ — includes `paused`, `failed`, `completed` |
| `recent_governance[].effect` | `list_recent_governance_decisions()` | ✓ — includes `allow`, `deny`, `require_approval` |
| `recent_traces[].status` | `list_recent_traces()` | ✓ |

### What can be derived without new infrastructure
- `degraded_agent_count` — count agents where `availability == "degraded"`
- `offline_agent_count` — count agents where `availability == "offline"`
- `paused_plan_count` — count plans where `status == "paused"`
- `failed_plan_count` — count plans where `status == "failed"`
- `attention_items` — priority list: pending approvals + paused plans + degraded agents + warnings
- `overall` — "healthy" | "attention" | "degraded" derived from the above

---

## 4. Why `frontend/agent-ui` Remains the Only UI Truth

- There is already exactly one SPA with one router (`BrowserRouter` + `Routes`) in `frontend/agent-ui/src/App.tsx`
- All pages read from the same `controlPlaneApi` facade in `services/controlPlane.ts`
- No second app, no separate dashboard process, no monitoring revival
- S7 adds one new route (`/health`) and one new page component — consistent with the existing 6-tab pattern

---

## 5. S7 Implementation Plan

### Backend extension (minimal)
`services/core.py` — `get_control_plane_overview` extended to derive and return a `health` section:
```python
{
  "health": {
    "overall": "healthy" | "attention" | "degraded",
    "degraded_agent_count": int,
    "offline_agent_count": int,
    "paused_plan_count": int,
    "failed_plan_count": int,
    "pending_approval_count": int,
    "has_warnings": bool,
    "attention_items": [{"level": "warning"|"info", "label": str, "detail": str}]
  }
}
```

`api_gateway/schemas.py` — `ControlPlaneHealthSummary` model + `ControlPlaneOverviewResponse.health` field

### Frontend extension
`controlPlane.ts` — `HealthSummary` interface, `ControlPlaneOverview.health` field
`pages/SystemHealthPage.tsx` — new page, reads from existing `getOverview()` call
`components/layout/Sidebar.tsx` — add `{ path: '/health', name: 'Health', icon: 'H' }`
`App.tsx` — add `<Route path="/health" element={<SystemHealthPage />} />`

### Tests
`tests/services/test_control_plane_views.py` — tests for health section derivation

---

## 6. Invariants

1. One UI, one router, one API facade — no second dashboard
2. No new runtime, no new observability stack
3. No business logic in React — health derivation is in `services/core.py`
4. No direct store/DB access from the frontend
5. `get_control_plane_overview` extended, not replaced
