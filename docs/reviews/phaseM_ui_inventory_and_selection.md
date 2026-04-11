# Phase M UI Inventory And Selection

## Purpose

This review identifies the already present UI, dashboard, and control-plane surfaces in the repository and selects exactly one canonical basis for Phase M.

## Inventory

### `frontend/agent-ui`

- Role: consolidated React single-page application for the main operator-facing UI.
- Evidence:
  - `frontend/agent-ui/package.json` defines the active Vite/React build and dev workflow.
  - `frontend/agent-ui/src/App.tsx` contains the current routed shell with sidebar, header, and page structure.
  - `docs/roadmap.md` and `docs/frontend_bridge.md` reference this directory as the current frontend path.
- Maturity: highest among repo UI surfaces.
- Status before Phase M: structurally current, but many pages still rendered mock/demo data instead of the current ABrain core.
- Reuse value: very high. Existing layout, routing shell, styling, and build stack were retained.

### `monitoring/`

- Role: auxiliary monitoring assets, sample monitoring API, reusable components, and Grafana/Prometheus support.
- Evidence:
  - `monitoring/package.json` defines a separate dashboard project.
  - `monitoring/monitoring/api/server.py` exposes an old monitoring-focused API with demo authentication and dashboard data aggregation.
  - `docs/observability/monitoring.md` describes this area as example monitoring infrastructure.
- Maturity: partial and fragmented.
- Status: auxiliary or historical, not the canonical operator UI.
- Reuse value: medium for observability ideas, low as the primary control plane.

### `archive/ui_legacy/*`

- Role: archived legacy UI artifacts.
- Evidence:
  - `docs/ui_migration_audit.md` explicitly states that legacy widgets and dashboard pieces were archived under `archive/ui_legacy`.
- Maturity: historical only.
- Status: legacy/historical, not active.
- Reuse value: low. Useful as reference only.

### Historical Smolitux / bridge surfaces

- Relevant paths:
  - `docs/BenutzerHandbuch/smolitux-ui.md`
  - `api/endpoints.py`
  - `server/main.py`
- Role: earlier bridge-era UI and API integration surfaces.
- Status: historical or transitional.
- Notes:
  - `api/endpoints.py` still contains explicitly disabled `/smolitux/*` routes.
  - `server/main.py` remains a bridge-style server, but `docs/frontend_bridge.md` places the frontend against the API gateway, not against a second standalone UI runtime.

## Selection

### Chosen canonical basis: `frontend/agent-ui`

This is the only credible Phase M base because it already provides:

- the active React/Vite application shell
- a consolidated routing structure
- repository documentation that points to it as the frontend reference path
- an existing visual language that can be evolved without opening a second UI

## Rejected As Canonical Bases

### `monitoring/`

Rejected because it behaves as a parallel dashboard stack rather than the current single UI truth. It is valuable for observability support, but not as the main control plane.

### `archive/ui_legacy/*`

Rejected because it is explicitly archived.

### Smolitux-era routes and bridge pages

Rejected because they are historical and because the modern control-plane requirement is to show canonical core state, not revive earlier UI/runtime assumptions.

## Legacy / Historical Labeling For Phase M

The following surfaces should be treated as legacy, historical, or auxiliary rather than as competing entry points:

- `monitoring/`
- `archive/ui_legacy/*`
- `docs/BenutzerHandbuch/smolitux-ui.md`
- `api/endpoints.py` Smolitux compatibility routes
- `server/main.py` as an older bridge-oriented API surface, not the preferred canonical operator contract

## Decision Summary

- Canonical UI basis: `frontend/agent-ui`
- Canonical external backend attachment for the UI: `api_gateway/main.py`
- Historical or auxiliary surfaces: `monitoring/`, `archive/ui_legacy/*`, Smolitux-era bridge paths
