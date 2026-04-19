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
