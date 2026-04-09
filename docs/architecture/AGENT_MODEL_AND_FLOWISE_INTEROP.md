# Agent Model And Flowise Interop

## Role Of The Canonical Agent Model

ABrain keeps `AgentDescriptor` as its internal truth for agent identity, capabilities, routing inputs and later evaluation. This model lives in `core/decision/*` and is intentionally framework-neutral.

## Role Of Flowise

Flowise is only an interoperability and UI layer.

- import: a small Flowise artifact can be mapped into an `AgentDescriptor`
- export: an `AgentDescriptor` can be projected into a minimal Flowise-shaped artifact
- manual editing: exported artifacts may be adjusted in external tools without changing ABrain's internal truth

Flowise is not:

- a decision component
- an execution component
- a second registry
- the internal source of truth for ABrain

## Import

`adapters/flowise/importer.py` maps:

- `id`
- `name`
- `description`
- `tools`
- optional `metadata`

Unknown fields are preserved only under `metadata["flowise_extra"]`.

The importer sets:

- `source_type="flowise"`
- `execution_kind="workflow_engine"`
- `editable_in_flowise=True`

No execution binding is created during import.

## Export

`adapters/flowise/exporter.py` projects a canonical descriptor into a minimal `FlowiseAgent`.

Only these fields are exported:

- `id`
- `name`
- `description`
- `tools`
- `metadata`

This export is a projection, not a lossless round-trip of arbitrary Flowise internals.

## Runtime Boundary

The Flowise interop layer is not part of:

- `Planner`
- `CandidateFilter`
- `NeuralPolicyModel`
- `RoutingEngine`
- `ExecutionEngine`
- execution adapters

It does not participate in routing, execution or security decisions.
