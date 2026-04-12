# 🧠 ABrain

> Stop prompting AI. Start controlling it.

**ABrain is a deterministic, governance-first AI agent system.**  
It doesn’t just *generate answers* — it **plans, controls and executes actions safely**.

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

Run a control-plane task:

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
```

`./scripts/agentnn` remains only as a thin compatibility wrapper around the
canonical Bash CLI `./scripts/abrain`.

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

* [ ] Persistent execution state
* [ ] Distributed agents
* [ ] Advanced governance engine
* [ ] UI for approvals & traces
* [ ] Plugin system (controlled)

---

## 📜 License

MIT

---

## 🧠 Final thought

ABrain is not trying to make AI more powerful.

It’s trying to make AI
**safe enough to trust.**
