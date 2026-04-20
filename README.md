# 🧠 ABrain

> Stop prompting AI. Start controlling it.

**ABrain is a deterministic, governance-first AI agent system.**  
It doesn’t just *generate answers* — it **plans, controls and executes actions safely**.

ABrain ist die Weiterentwicklung des früheren Projekts. Der alte Name wird
nicht mehr verwendet.

---

## ⚡ Why ABrain exists

Most AI agent frameworks today:

- ❌ Execute tools without real control  
- ❌ Hide decisions behind LLM reasoning  
- ❌ Have no real security boundary  
- ❌ Are unpredictable in production  

**ABrain fixes this.**

---

## 🚀 What makes ABrain different?

| Feature | ABrain | Typical Agent Frameworks |
|--------|--------|------------------------|
| Deterministic execution | ✅ | ❌ |
| Governance before execution | ✅ | ❌ |
| Human approval (HITL) | ✅ | ⚠️ optional |
| Static tool registry | ✅ | ❌ dynamic |
| Full traceability | ✅ | ❌ |
| Security boundaries | ✅ | ❌ |

---

## 🧠 The Core Idea

```

AI should never execute blindly.

```

ABrain enforces a strict execution pipeline:

```

Decision → Governance → Approval → Execution → Audit

````

Every action:
- is **planned**
- is **validated**
- can be **approved**
- is **fully traceable**

---

## ⚡ See it in action (30 sec)

```bash
git clone https://github.com/Modularium/ABrain
cd ABrain

./scripts/abrain setup

.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/state \
  tests/mcp \
  tests/approval \
  tests/orchestration \
  tests/execution \
  tests/decision \
  tests/adapters \
  tests/core \
  tests/services \
  tests/integration/test_node_export.py
````

Start the API gateway:

```bash
.venv/bin/python -m uvicorn api_gateway.main:app --reload
```

Inspect the canonical developer HTTP surface in the browser:

```text
http://localhost:8000/docs
http://localhost:8000/redoc
http://localhost:8000/openapi.json
```

The public HTTP developer surface is the existing `api_gateway` and focuses on
the canonical `/control-plane/*` routes. See `docs/guides/API_USAGE.md` for
examples and guidance on when to use HTTP API vs MCP vs CLI.

Run the same core paths directly from the canonical CLI:

```bash
./scripts/abrain task run system_status "Check system health"
./scripts/abrain plan run workflow_automation "Trigger deployment workflow"
./scripts/abrain approval list
./scripts/abrain trace list
./scripts/abrain health --json
```

Run a control-plane task through the canonical HTTP surface:

```bash
curl -X POST http://localhost:8000/control-plane/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "system_status",
    "description": "Check system health"
  }'
```

---

## 🧩 What ABrain actually does

ABrain turns this:

> “Check system health and fix issues”

into:

1. Structured plan
2. Policy validation
3. Optional human approval
4. Controlled execution
5. Full audit trail

---

## 🧠 ABrain V2 — Domain Reasoning for external systems

ABrain V2 adds a deterministic **domain-reasoning layer** that interprets
external-system context (starting with **LabOS**) and emits structured,
governance-aware recommendations — without ever executing anything itself.

The reasoner is **input-driven**: the caller (e.g. Smolit-AI-Assistant)
pulls a snapshot from LabOS MCP, hands it to ABrain, and receives a
Response Shape V2 it can render. ABrain does **not** call LabOS,
does **not** invent tool names, and **respects** the LabOS action
catalogue, approval flags and safety context.

**Canonical boundary:**

```
Smolit-AI-Assistant → ABrain (Domain Reasoning) → LabOS MCP → LabOS API/DB
```

**Use cases supported:**

ReactorOps V1:

- `labos_reactor_daily_overview` — reactor focus list (attention vs. nominal)
- `labos_incident_review` — prioritised open-incident review
- `labos_maintenance_suggestions` — overdue/due calibration + maintenance
- `labos_schedule_runtime_review` — failing / blocked schedules and commands
- `labos_cross_domain_overview` — combined operator focus list

RobotOps V1 (module-scoped reasoning — reactor modules, hydro /
sampling / dosing / vision modules, workshop machines, mobile robots):

- `labos_module_daily_overview` — module focus list (attention / offline / disabled / nominal)
- `labos_module_incident_review` — modules with open incidents or capability impact
- `labos_module_coordination_review` — blocked/impacted module dependency edges
- `labos_module_capability_risk_review` — modules with missing/degraded critical capabilities + autonomy-level signals
- `labos_robotops_cross_domain_overview` — combined ReactorOps + RobotOps focus list

**Invariants enforced by the reasoner (pinned by tests):**

1. `no_invented_actions` — actions missing from the supplied
   `action_catalog` surface as `DeferredAction`, never as
   `RecommendedAction`.
2. `respects_approval` — `requires_approval=True` entries route into
   `approval_required_actions`, never `recommended_actions`.
3. `respects_safety_context` — targets with a safety alert or an
   offline reactor defer their actions (except explicitly opt-in
   diagnostic intents like `open_reactor_detail`).

**Entry points** live on `services/core.py` as
`get_labos_<usecase>(context)` and are thin delegates of
`core/reasoning/labos/usecases.py`. The surface dispatcher
`run_labos_reasoning(mode, context)` shares a single code path
across CLI, HTTP and MCP. See
[`docs/reviews/phase_v2_labos_reasoning_review.md`](docs/reviews/phase_v2_labos_reasoning_review.md)
and
[`docs/reviews/phase_v2_labos_surface_parity_review.md`](docs/reviews/phase_v2_labos_surface_parity_review.md)
for the full design notes.

**Surfaces (identical Response Shape V2):**

```bash
# CLI — reads context from file / stdin / inline JSON
./scripts/abrain reasoning labos reactor_daily_overview --input ctx.json --json
cat ctx.json | ./scripts/abrain reasoning labos incident_review --stdin
./scripts/abrain reasoning labos maintenance_suggestions --input-json '{"maintenance_items":[]}'
```

```bash
# HTTP — one endpoint per mode
curl -X POST http://localhost:8080/control-plane/reasoning/labos/reactor_daily_overview \
     -H 'Content-Type: application/json' \
     -d '{"context": {"reactors": [{"reactor_id":"R1","status":"warning"}]}}'
```

```jsonc
// MCP — one tool per mode, strict input schema
{
  "method": "tools/call",
  "params": {
    "name": "abrain.reason_labos_reactor_daily_overview",
    "arguments": {"context": {"reactors": [{"reactor_id":"R1","status":"warning"}]}}
  }
}
```

Invalid contexts surface symmetrically: CLI exit code `1` with
`{"error":"invalid_context", ...}`, HTTP `400`, MCP `isError=true`
with `status: "error"`.

---

## 🏗️ Architecture (simplified)

```mermaid
flowchart LR
  USER --> CORE
  CORE --> GOVERNANCE
  GOVERNANCE --> APPROVAL
  APPROVAL --> EXECUTION
  EXECUTION --> AUDIT
```

---

## 🔐 Built for real-world usage

ABrain is not a demo framework.

It is built for:

* 🏢 Infrastructure automation
* 🔐 Security-sensitive systems
* 🤖 Controlled AI agents
* 🧠 Multi-agent orchestration

---

## 🚫 What ABrain will NOT do

* Run arbitrary tools
* Execute unchecked actions
* Bypass governance
* Hide decisions

---

## 🔌 MCP-compatible (AI-native)

ABrain exposes a **Model Context Protocol (MCP) server**:

```bash
.venv/bin/python -m interfaces.mcp.server
```

`./scripts/abrain setup` refreshes the editable installation and regenerates
the local runtime; `./scripts/abrain setup cli` is the narrow targeted rerun for
the MCP console entry only.

Available tools:

* `abrain.run_task`
* `abrain.run_plan`
* `abrain.approve`
* `abrain.reject`
* `abrain.get_trace`
* `abrain.explain`

---

## 🖥️ UI build

```bash
cd frontend/agent-ui
npm ci
npm run type-check
npm run build
```

---

## 🧰 CLI

```bash
./scripts/abrain --version
./scripts/abrain help
./scripts/abrain setup
./scripts/abrain status
./scripts/abrain task run system_status "Check system health"
./scripts/abrain plan list
./scripts/abrain approval list
./scripts/abrain trace show <trace_id>
./scripts/abrain explain <trace_id>
./scripts/abrain agent list
./scripts/abrain health --json
```

`./scripts/abrain` is the single canonical CLI for local developer and operator
workflows.

---

## 🧠 Philosophy

ABrain is built on one principle:

> **Control > Autonomy**

---

## 🔥 Why developers like ABrain

* No magic black box
* Predictable execution
* Easy to debug
* Safe to run in production
* Works with existing tools

---

## 🧪 Designed for engineers

* FastAPI-based services
* One-line local bootstrap
* Clean architecture
* Strong invariants
* Extensible adapters

---

## 📂 Project structure

```
core/        # canonical execution path
adapters/    # external integrations
services/    # runtime services
interfaces/  # MCP + API
frontend/    # control plane UI
```

---

## 🧨 The difference in one sentence

Other frameworks:

> “Let the AI decide”

ABrain:

> “Make the AI explain and prove every step”

---

## 🤝 Contributing

We welcome contributions — but:

> ❗ Core invariants must never be broken

---

## 🛣 Roadmap

The canonical, phased roadmap lives in
[`docs/ROADMAP_consolidated.md`](docs/ROADMAP_consolidated.md). It bundles
Phase 0 (consolidation), Phase 1 (evaluability), Phase 2 (controlled
extensibility), Phase 3 (retrieval), Phase 4 (system-level MoE), Phase 5
(LearningOps), Phase 6 (Brain v1), and Phase 7 (advanced brain).

Historical planning notes are kept in [`ROADMAP.md`](ROADMAP.md) and
[`Roadmap.md`](Roadmap.md) for archival reference only.

---

## 📜 License

MIT

---

## 🧠 Final thought

ABrain is not trying to make AI more powerful.

It’s trying to make AI
**safe enough to trust.**
