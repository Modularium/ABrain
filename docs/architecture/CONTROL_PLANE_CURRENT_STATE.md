# Control Plane Current State

## Selected Base

The control plane builds on `frontend/agent-ui`.

## Entry Points

### Frontend

- `frontend/agent-ui/src/main.tsx`
- `frontend/agent-ui/src/App.tsx`

The frontend is a BrowserRouter-based SPA with a persistent sidebar/header shell.

### Backend Attachment

- `api_gateway/main.py`

Phase M attaches the operator UI to the API gateway instead of introducing a separate dashboard runtime.

## Route Structure

The Phase M control plane now exposes a focused route set:

- `/`
  - system overview
- `/traces`
  - recent traces, trace detail, explainability
- `/approvals`
  - pending approvals, approve, reject
- `/plans`
  - plan launch, recent plan runs, paused-step state
- `/agents`
  - agent capability and execution metadata view
- `/settings`
  - local UI/API endpoint settings

Older demo-oriented routes were removed from the main navigation so the control plane has a single visible truth.

## Data Flow

### Frontend flow

- Pages call `frontend/agent-ui/src/services/controlPlane.ts`.
- That client reads the shared UI API base URL from `useAppStore`.
- Requests go to `/control-plane/*` on the API gateway.

### Backend flow

- `api_gateway/main.py` exposes thin HTTP routes under `/control-plane/*`.
- These routes call canonical `services/core.py` helpers.
- `services/core.py` continues to own:
  - task execution entry
  - plan execution entry
  - approval pause/resume
  - trace and explainability reads
  - governance-derived read models

The UI does not call adapters, registries, or orchestration internals directly.

## Current Screens

### Overview

- Shows summary counts
- Shows active runtime layers
- Shows recent traces
- Shows pending approvals
- Shows recent governance decisions
- Allows controlled `run_task` submission through the canonical core

### Traces

- Lists recent traces
- Loads a full trace snapshot
- Displays spans and explainability records from the audit layer

### Approvals

- Lists pending approval requests
- Executes approve/reject through the existing core pause/resume path

### Plans

- Launches plans via `services.core.run_task_plan`
- Shows recent plan traces
- Surfaces paused step state from approval metadata where available

### Agents

- Shows projected capability metadata from the current agent listing path
- Displays `source_type` and `execution_kind` when the registry exposes them
- Clearly keeps incomplete projections honest

## Historical Mismatch Identified During Analysis

Before Phase M, the `frontend/agent-ui` shell was already the correct frontend basis, but several pages were still built around mock/demo entities rather than around the current ABrain core. That mismatch has now been reduced by moving the main control-plane views to canonical gateway/core-backed data.

## Build And Start Mechanism

### Frontend

- `cd frontend/agent-ui`
- `npm install`
- `npm run dev`
- `npm run build`

### Backend contract

- The frontend expects `VITE_API_URL` or the persisted UI setting to point to the API gateway.
- Default local target for Phase M is `http://localhost:8080`.

## Current Boundaries

- The control plane visualizes traces, approvals, governance, orchestration state, and agent metadata.
- It does not implement its own policy engine.
- It does not simulate approvals.
- It does not create a second runtime.
- It does not expose adapter internals directly.
