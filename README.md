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

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

pytest
````

Run a task:

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
abrain-mcp
```

Available tools:

* `abrain.run_task`
* `abrain.run_plan`
* `abrain.approve`
* `abrain.reject`
* `abrain.get_trace`
* `abrain.explain`

---

## ⚙️ Docker (fast setup)

```bash
cp .env.example .env
docker compose up --build
```

---

## 🧰 CLI

```bash
agentnn ask "Check system health"
```

> Yes, `agentnn` is legacy — kept for compatibility.

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
* Docker-first setup
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

