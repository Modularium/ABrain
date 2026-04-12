# 🧠 ABrain

> Deterministic Multi-Agent Core with Governance, Approval & Audit — built for control, security and explainability.

[![Repo](https://img.shields.io/badge/GitHub-Modularium%2FABrain-blue)](https://github.com/Modularium/ABrain)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-informational)](#)
[![Docker](https://img.shields.io/badge/docker-ready-informational)](#docker--compose)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)

---

## 🚀 What is ABrain?

**ABrain is a hardened multi-agent execution system** with a strict, verifiable control flow:

```

Decision → Governance → Approval → Execution → Feedback → Audit

````

Unlike typical AI-agent frameworks, ABrain focuses on:

- ✅ **Determinism over randomness**
- ✅ **Security boundaries (AdminBot isolation)**
- ✅ **Explicit governance & approval**
- ✅ **Full traceability (Audit + Explainability)**

---

## ⚡ TL;DR

| Feature | Description |
|--------|------------|
| 🧠 Multi-Agent Core | Structured planning & execution |
| 🔐 Governance Layer | Deterministic policy enforcement |
| 👤 Approval (HITL) | Human-in-the-loop control |
| ⚙️ Static Tooling | No dynamic tool injection |
| 📜 Audit & Trace | Full execution transparency |
| 🔌 MCP v2 Interface | Standardized tool API |

---

## 🧩 Core Philosophy

ABrain is built around **control, not autonomy**.

> "AI should execute — but never decide unchecked."

Key principles:

- No uncontrolled tool execution  
- No hidden decisions  
- No silent failures  
- No bypass of governance  

---

## 🏗️ Architecture Overview

```mermaid
flowchart TB
  UI --> GW[API Gateway]

  subgraph Core
    DECISION --> POLICY
    POLICY -->|allow| EXECUTION
    POLICY -->|approval| APPROVAL
    APPROVAL --> EXECUTION
    EXECUTION --> FEEDBACK
    EXECUTION --> AUDIT
  end

  EXECUTION --> ADAPTERS
  ADAPTERS --> ADMINBOT
````

---

## ⚡ Quickstart (Minimal)

```bash
git clone https://github.com/Modularium/ABrain
cd ABrain

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

pytest
```

---

## 🐳 Docker Setup

```bash
cp .env.example .env
# set API keys if needed

docker compose up --build
```

### Default Services

| Service     | URL                                            |
| ----------- | ---------------------------------------------- |
| API Gateway | [http://localhost:8000](http://localhost:8000) |
| Frontend    | [http://localhost:3000](http://localhost:3000) |
| Prometheus  | [http://localhost:9090](http://localhost:9090) |

---

## 🧪 Run a Task

```bash
curl -X POST http://localhost:8000/control-plane/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "system_status",
    "description": "Check system health"
  }'
```

---

## 🧠 Core Components

| Layer      | Responsibility                 |
| ---------- | ------------------------------ |
| Decision   | Planning & task decomposition  |
| Governance | Policy enforcement             |
| Approval   | Human control (HITL)           |
| Execution  | Deterministic execution engine |
| Adapters   | External system bridges        |
| Audit      | Trace + explainability         |

---

## 🔐 Security Model

ABrain enforces **strict execution boundaries**:

### 🚫 What is NOT allowed

* Dynamic tool injection
* Direct system access
* Bypassing governance

### ✅ What IS allowed

* Predefined tools only
* Policy-checked execution
* Approval-controlled actions

---

## 🔌 MCP v2 Interface

ABrain exposes a **Model Context Protocol (MCP) server**:

```bash
abrain-mcp
```

### Available tools

* `abrain.run_task`
* `abrain.run_plan`
* `abrain.approve`
* `abrain.reject`
* `abrain.get_trace`
* `abrain.explain`

---

## 🧰 CLI Usage

```bash
agentnn ask "Check system health"
agentnn queue status
agentnn governance trust score <agent-id>
```

> ⚠️ `agentnn` is a legacy name (kept for compatibility)

---

## ⚙️ Configuration

### `.env`

```env
OPENAI_API_KEY=...
DATABASE_URL=postgresql://...

API_AUTH_ENABLED=false
VITE_API_URL=http://localhost:8000
```

---

## 📂 Project Structure

```
core/
  decision/
  governance/
  execution/
  approval/
  audit/

adapters/
  adminbot/
  flowise/
  codex/

services/
  api_gateway/
  registry/
  dispatcher/

interfaces/
  mcp/

frontend/
```

---

## 🧪 Development

```bash
pip install ruff black mypy pytest

ruff check .
black .
mypy .
pytest
```

---

## 🧠 Design Invariants (VERY IMPORTANT)

These rules must NEVER be broken:

1. ❗ Core execution is deterministic
2. ❗ Governance always runs before execution
3. ❗ No tool execution without registry
4. ❗ AdminBot remains isolated (read-only)
5. ❗ All actions must be traceable

---

## 🤝 Contributing

1. Create an issue first
2. Use feature branches
3. Run tests before PR
4. Respect core invariants

---

## 📜 License

MIT License

---

## ❓ FAQ

### Why "Agent-NN" still exists?

Legacy naming for compatibility — will be removed gradually.

---

### Is ABrain autonomous?

No. It is **controlled execution**, not autonomous AI.

---

### Can it run locally?

Yes — fully self-hostable.

---

### Does it support real-world execution?

Yes — but always through controlled adapters.

---

## 🧭 Roadmap

* [ ] Persistent orchestration state
* [ ] Advanced policy engine
* [ ] Distributed agent execution
* [ ] UI for governance & approvals
* [ ] Plugin system (controlled)

---

## 🧾 References

* Core: `services/core.py`
* MCP: `interfaces/mcp/`
* AdminBot: `adapters/adminbot/`
* Docs: `docs/architecture/`

---

## 🛠 Maintainer Notes

* Add CI workflow
* Add LICENSE file
* Maintain CHANGELOG
* Validate security invariants on every PR

---

## 🔥 Final Thought

ABrain is not about making AI more powerful.

It is about making AI **safe, controllable, and understandable**.
