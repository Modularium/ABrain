# Phase M Control Plane Review

## Selected Existing UI

Phase M continues with `frontend/agent-ui` as the single operator UI.

## Alternatives Not Continued

- `monitoring/` remains an auxiliary monitoring area, not the main control plane.
- `archive/ui_legacy/*` remains historical.
- Smolitux-era bridge paths remain historical or disabled and are not the central UI truth.

## What Was Adapted

### Frontend

- Replaced the main control-plane pages with core-backed views:
  - overview
  - traces
  - approvals
  - plans
  - agents
- Removed older demo pages from the primary navigation.
- Pointed the UI toward the API gateway control-plane routes.
- Aligned the shared UI API base URL default to `http://localhost:8080`.

### Backend

- Added thin `/control-plane/*` routes to `api_gateway/main.py`.
- Kept all task, plan, approval, trace, and explainability behavior delegated to `services/core.py`.

### Core

- Added minimal read-only helpers for:
  - recent plans
  - recent governance decisions
  - projected agent catalog
  - governance state inspection

## How The UI Now Reflects The ABrain Core

- Trace and explainability data come from the canonical audit/trace layer.
- Approval actions call the existing pause/resume path.
- Plan execution uses `run_task_plan`.
- Task execution uses `run_task`.
- Governance visibility is derived from trace and explainability records rather than re-evaluated in the UI.

## Minimal Backend Additions

The backend additions were intentionally small and read-mostly:

- `services.core.list_recent_plans`
- `services.core.list_recent_governance_decisions`
- `services.core.list_agent_catalog`
- `services.core.get_governance_state`
- thin API gateway routes that forward to those helpers or to existing core entry points

## V1 Boundaries

- Plan history is still stronger for active or paused plans than for deep historical replay.
- Agent descriptor completeness depends on what the existing agent listing path exposes.
- The settings page remains local UI configuration rather than a full remote admin plane.

## Recommended Next Phase

- richer dashboard drilldowns
- trace replay and step-to-step debug support
- more explicit policy management UI
- sharper agent descriptor sourcing if the registry exposes full canonical metadata
- incremental MCP control-surface refinement
