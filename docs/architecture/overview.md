# Architecture Overview

ABrain now exposes a stabilized foundations stack around a hardened execution core. The repository still contains historical services and legacy paths, but the current architectural truth is the combination of canonical agent modeling, decision, execution and learning around `services/core.py`.

## Core Repository Folders

- **core/decision/** – canonical agent model, planner, candidate filter, neural policy and learning
- **core/execution/** – dispatcher plus execution engine and static adapters
- **adapters/adminbot/** – verified AdminBot-v2 adapter
- **adapters/flowise/** – Flowise import/export interoperability layer
- **interfaces/mcp_v1/** – thin MCP interface layer
- **services/** – canonical runtime and service wrappers
- **api/** and **server/** – API-facing entry points and bridges
- **sdk/** – CLI and SDK utilities with historical technical names where needed

## Foundations Pipeline

1. **Planner** – derives required capabilities from the task
2. **CandidateFilter** – enforces deterministic safety and capability constraints
3. **NeuralPolicyModel** – ranks only the already safe candidates
4. **RoutingEngine** – materializes a routing decision
5. **ExecutionEngine** – selects a static adapter and executes
6. **FeedbackLoop** – updates performance history and learning data best-effort
7. **Training Components** – dataset, reward model and trainer improve routing quality over time

For the current architectural reference, prefer `PROJECT_OVERVIEW.md`. Historical MCP diagrams such as `overview_mcp.md` remain documentation of legacy evolution, not the current foundations truth.
