# Control Plane Target State

## Goal

Provide one operator-facing control plane that makes the current ABrain core visible and usable without duplicating core logic.

## V1 Scope

Phase M deliberately keeps the slice focused.

### 1. System Overview

- Show the main runtime layers:
  - Decision
  - Execution
  - Learning
  - Orchestration
  - Approval
  - Governance
  - Audit/Trace
  - MCP v2
- Show recent traces, approvals, governance decisions, and plan activity.
- Allow controlled `run_task` submission via the canonical core path.

### 2. Trace And Explainability

- Show recent traces.
- Show trace detail.
- Show explainability records and policy context already stored by the audit layer.

### 3. Approvals

- Show pending approvals.
- Allow approve/reject actions.
- Reflect pause/resume through the existing core orchestration path.

### 4. Plans / Orchestration

- Allow `run_task_plan`.
- Show recent plan executions.
- Show paused-step state when approval metadata exposes it.
- Show returned plan result immediately after launch.

### 5. Agents / Capabilities

- Show the currently available agent listing.
- Surface capabilities, source type, execution kind, and availability when exposed.
- Mark projected or incomplete metadata honestly.

## Explicit Non-Goals For V1

- No second frontend
- No custom governance engine in the UI
- No trace replay engine
- No direct adapter inspection APIs
- No direct registry or store reads from the browser
- No large settings/admin rebuild

## Target Interaction Model

The intended operator flow is:

1. View recent runtime health and events on the overview.
2. Inspect traces and explainability when a task or plan behaves unexpectedly.
3. Approve or reject paused work from the approval queue.
4. Launch a task or plan only through canonical core entry points.
5. Inspect agent capability exposure without inventing a second descriptor model.

## Honest V1 Constraints

- Completed plan history is primarily trace-driven.
- Detailed step state is strongest for paused plans because approval metadata retains plan-state snapshots.
- Agent descriptor completeness depends on what the current listing path exposes.

These constraints are acceptable for V1 because the UI remains honest about what is projected and what is fully canonical.
