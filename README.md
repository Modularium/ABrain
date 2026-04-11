<!--
ABrain README (DE)
Meta (suggested):
- description: Gehärteter Multi-Agent- und Service-Stack mit kanonischem Core (Decision/Governance/Approval/Execution/Learning/Audit) und strikt read-only AdminBot-v2 Adapter.
- keywords: multi-agent, orchestration, governance, approval, mcp, model-context-protocol, fastapi, adminbot, security, tracing, audit, neural-policy
- topics (GitHub): multi-agent, mcp, orchestration, fastapi, governance, security, llm, python, docker
-->

# ABrain

[![Repo](https://img.shields.io/badge/GitHub-Modularium%2FABrain-blue)](https://github.com/Modularium/ABrain)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-informational)](#)
[![Docker](https://img.shields.io/badge/docker-ready-informational)](#docker--compose)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#lizenz)
<!-- Suggested badges (adapt once CI is known):
[![CI](https://github.com/Modularium/ABrain/actions/workflows/ci.yml/badge.svg)](https://github.com/Modularium/ABrain/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-TODO-lightgrey)](#)
[![MCP v2](https://img.shields.io/badge/MCP-2025--06--18-informational)](#mcp-v2-stdio-json-rpc)
-->

ABrain ist der aktuelle Projektname für den gehärteten Multi-Agent- und Service-Stack in diesem Repository. Der sicherheitsrelevante Schwerpunkt liegt auf:

- **kanonischem Core-Pfad** (Decision → Governance/Policy → Approval/HITL → Execution → Feedback/Learning → Audit/Trace)
- **statischem Tool-Dispatcher/Registry** (keine dynamische Tool-Expansion im Core)
- **streng typisiertem, read-only AdminBot-v2 Adapter** (AdminBot bleibt Sicherheitsgrenze)
- **MCP v2 Thin Interface** über dem kanonischen Core (capability-/policy-/approval-/trace-aware)

> Hinweis zur Umbenennung: **Agent-NN ist der alte technische Name**. Slugs wie `agentnn` / `agent-nn` bleiben vorerst absichtlich bestehen, um Import-/Deploy-Regressions zu vermeiden.

## Executive Summary

ABrain verbindet einen deterministischen, überprüfbaren Kern (Registry/Dispatcher, CandidateFilter + Governance/Policy) mit einem kontrollierten Orchestrations- und Execution-Layer: Entscheidungen werden strukturiert geplant und (nach Policy/Approval) über statische Adapter ausgeführt; Ergebnisse fließen über Feedback in ein best-effort Learning-System zurück. Audit/Trace/Explainability sind als Nachvollziehbarkeitsschicht vorgesehen.

Dieses Repo enthält außerdem eine service-orientierte Laufzeit (API Gateway + mehrere Services) für lokale/Container-basierte Setups, inkl. Redis/Postgres/Prometheus.

## Quickstart

### Minimaler Prüfpfad für den gehärteten Core (Tests)

```bash
cd <repo-root>

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip
pip install pydantic pytest httpx

python -m pytest -o python_files='test_*.py' \
  tests/decision \
  tests/execution \
  tests/adapters \
  tests/core \
  tests/services \
  tests/integration/test_node_export.py
```

Einmal „alles“ für lokales Arbeiten (pip)

bash

cd <repo-root>
python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

Frontend lokal starten (falls benötigt)

bash

cd <repo-root>/frontend/agent-ui
npm install
npm run dev

    ⚠️ Frontend/API-Basis-URL ist deploymentabhängig (siehe .env.example, VITE_API_URL).

Installation
Lokale Installation

Voraussetzungen (empfohlen):

    Python 3.10+
    optional: Poetry
    optional: Node.js 18+ (für frontend/agent-ui)

Install (pip):

bash

python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

Install (Poetry, optional):

bash

poetry install --no-root

Docker & Compose

ABrain liefert ein docker-compose.yml mit mehreren Services (API Gateway, Dispatcher, Registry, Session Manager, Vector Store, LLM Gateway, Routing Agent, …).

Setup:

bash

cd <repo-root>
cp .env.example .env
# Editiere .env und setze mindestens OPENAI_API_KEY (oder konfiguriere LLM_BACKEND)
docker compose up --build

Ports (Default aus Compose / Images):

    API Gateway: http://localhost:8000
    Frontend (nginx): http://localhost:3000
    Redis: localhost:6379
    Postgres: localhost:5434
    Prometheus: http://localhost:9090

    Hinweis: docker-compose.yml überschreibt die Dockerfile-Default-CMD pro Service.
    Maintainer-Check: Das Dockerfile referenziert als Default uvicorn api.server:app; verifizieren, ob dieses Entry-Module in der aktuellen Branch-Struktur existiert und/oder ob Compose die primäre Startform ist.

Konfiguration

ABrain nutzt sowohl .env (Compose/Services/UI) als auch SDK-spezifische RC/Env-Konfiguration.
.env (Compose/Runtime)

Startpunkt ist .env.example → .env.

Minimal (Beispiel):

dotenv

OPENAI_API_KEY=...              # falls LLM_BACKEND=openai
DATABASE_URL=postgresql://postgres:postgres@db:5432/agent_nn

API_AUTH_ENABLED=false
CORS_ALLOW_ORIGINS=*

# UI
VITE_API_URL=http://localhost:8000

SDK/CLI-Konfiguration (~/.agentnnrc + Env)

Das SDK liest ~/.agentnnrc und Environment:

json

{
  "host": "http://localhost:8000",
  "api_token": "CHANGE_ME"
}

Alternativ per Environment:

bash

export AGENTNN_HOST="http://localhost:8000"
export AGENTNN_API_TOKEN="CHANGE_ME"

Wichtige Environment Variablen (Auswahl)
Kategorie	Variable	Beispiel	Zweck
Core Trace	ABRAIN_TRACE_DB_PATH	runtime/abrain_traces.sqlite3	Pfad zur Trace/Explainability DB
Core Governance	ABRAIN_POLICY_PATH	policies/policy.toml	Policy Registry Pfad
Gateway Auth	API_AUTH_ENABLED	true/false	Aktiviert Scope-Checks
Gateway Auth	API_GATEWAY_KEY	changeme	X-API-Key für einfache Gate-Auth
JWT	JWT_SECRET	secret	Signaturkey
Routing	ROUTING_URL	http://routing_agent:8111	Routing Service
LLM	OPENAI_API_KEY	...	API-Key für OpenAI
Frontend	VITE_API_URL	http://localhost:8000	UI → REST Base

    Vollständige Liste: siehe .env.example.

Nutzung
Kontrolle über die Control Plane (HTTP)

Das API Gateway stellt Control-Plane-Endpunkte bereit (Beispiele):

    GET /control-plane/overview – Systemübersicht
    GET /control-plane/agents – Agent-Katalog (projektiert)
    POST /control-plane/tasks/run – Single Task via kanonischem Core
    POST /control-plane/plans/run – Plan-Ausführung
    Approval: POST /control-plane/approvals/{approval_id}/approve|reject
    Traces: GET /control-plane/traces, GET /control-plane/traces/{trace_id}, .../explainability

Beispiel: Single Task starten

bash

curl -sS -X POST "http://localhost:8000/control-plane/tasks/run" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "system_status",
    "description": "Read current status",
    "input_data": {},
    "options": {}
  }' | jq

CLI (Typer)

Die CLI wird als agentnn bereitgestellt (Altname, bleibt vorerst als technischer Slug).

bash

# Version / globale Flags
agentnn --version
agentnn --verbose --debug

# Quick dispatch
agentnn ask "Check system health" --task-type dev

# Queue status
agentnn queue status

# Governance helpers
agentnn governance contract view <agent-id>
agentnn governance trust score <agent-id>

MCP v2 (stdio JSON-RPC)

ABrain bietet einen MCP v2 Server als stdio-JSON-RPC.

Start:

bash

# via console script (empfohlen)
abrain-mcp

# oder modulbasiert
python -m interfaces.mcp.server

Tool Discovery:

    tools/list liefert u. a.:
    abrain.run_task, abrain.run_plan, abrain.approve, abrain.reject, abrain.list_pending_approvals, abrain.get_trace, abrain.explain

Beispiel: tools/call für abrain.run_task

json

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "abrain.run_task",
    "arguments": {
      "task_type": "system_status",
      "description": "Read current status",
      "input_data": {},
      "preferences": {}
    }
  }
}

Architektur
Kanonischer Überblick (Mermaid)

mermaid

flowchart TB
  UI[Control Plane UI<br/>frontend/agent-ui] --> GW[API Gateway<br/>api_gateway/main.py]

  subgraph CanonicalCore["Canonical Core (Foundations)"]
    CORE[services/core.py<br/>run_task / run_task_plan] --> PLANNER[Planner]
    PLANNER --> FILTER[CandidateFilter<br/>(deterministisch)]
    FILTER --> NN[NeuralPolicyModel<br/>(Ranking)]
    NN --> GOV[Governance/Policy Engine]
    GOV -->|allow| EXEC[ExecutionEngine<br/>core/execution/*]
    GOV -->|require approval| HITL[Approval Store/Policy<br/>core/approval/*]
    HITL -->|approve/reject| EXEC
    EXEC --> ADAPTERS[Static ExecutionAdapters<br/>AdminBot/OpenHands/Codex/Claude/n8n/Flowise]
    EXEC --> FEEDBACK[Feedback Loop + Learning<br/>core/decision/learning/*]
    CORE --> TRACE[Trace/Audit/Explainability<br/>core/audit/*]
  end

  GW -->|/control-plane/*| CORE
  GW -->|/chat, /agents, /embed ...| SVC[Service Mesh (compose)]
  subgraph ServiceMesh["Services (docker-compose.yml)"]
    DISP[Task Dispatcher :8001] --> ROUTE[Routing Agent :8111]
    REG[Agent Registry :8002]
    SESS[Session Manager :8005]
    VEC[Vector Store :8004]
    LLM[LLM Gateway :8003]
  end

  ADAPTERS -->|UDS IPC| ADMINBOT[(AdminBot v2 Daemon<br/>/run/adminbot/adminbot.sock)]

Komponentenvergleich
Komponente	Pfad(e)	Rolle	Stabilität	Security-Notiz
Hardened Tool Execution	core/tools/*, core/execution/dispatcher.py	Statische Tool Registry + Validation	hoch	keine dynamischen Tools
Canonical Core	services/core.py	Kanonischer Run-Pfad	hoch	Policy/Approval vor Execution
Decision Layer	core/decision/*	Planner/Filter/NN/Routing	mittel	NN rankt nur gefilterte Kandidaten
Governance Layer	core/governance/*	deterministische Policy Checks	mittel	kann allow/deny/approval
Approval/HITL	core/approval/*	Pause/Approve/Reject/Resume	mittel	zusätzlicher Kontrollpunkt
Audit/Trace	core/audit/*	Trace+Explainability	mittel	best-effort, nicht Security-Grenze
MCP v2 Interface	interfaces/mcp/*	Thin stdio Tool Surface	mittel	kein Bypass des Core
AdminBot Adapter	adapters/adminbot/*	read-only Bridge zu AdminBot	hoch	keine generischen Actions
API Gateway	api_gateway/main.py	HTTP Entry, Control Plane	mittel	optional scopes+keys
Services (compose)	services/*/main.py	Dispatcher/Registry/…	mittel	auth middleware vorhanden
Empfohlenes Development Setup

    Python venv + requirements.txt
    optional Poetry (wenn das Team Poetry bevorzugt)
    Node 18+ für die UI
    Lint/Quality: ruff, black, mypy (Konfiguration im pyproject.toml)

Beispiel:

bash

python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install ruff black mypy pytest pytest-cov

Testing und CI
Lokal

bash

# schnell: Foundations-Tests
python -m pytest -o python_files='test_*.py' \
  tests/decision tests/execution tests/adapters tests/core tests/services

# typchecks/lint (wenn installiert)
ruff check .
black --check .
mypy .

CI (Vorschlag, falls noch nicht vorhanden)

Empfohlen ist eine GitHub Actions Pipeline, die:

    pip install -r requirements.txt
    pytest + Coverage
    ruff + black --check
    optional: docker build und docker compose config Validierung

    Maintainer TODO: Workflow-Datei unter .github/workflows/ci.yml ergänzen und Badge aktivieren.

Contribution Guide

Beiträge sind willkommen. Bitte beachte:

    Erstelle Issues für größere Änderungen/Architekturentscheidungen.
    Nutze Feature-Branches und Pull Requests.
    Vor PR: Tests + Lint lokal ausführen.
    Sicherheitsrelevante Änderungen müssen die AdminBot- und Core-Invarianten respektieren.

Empfohlene Community-Health-Dateien (falls nicht vorhanden):

    CONTRIBUTING.md
    CODE_OF_CONDUCT.md
    SECURITY.md
    CITATION.cff

Lizenz

Lizenz laut pyproject.toml: MIT.

    Maintainer TODO: LICENSE Datei im Repo-Root hinzufügen, damit GitHub die Lizenz zuverlässig erkennt.

Changelog Template

Dieses Projekt sollte ein CHANGELOG.md nach „Keep a Changelog“ führen und SemVer verwenden.

markdown

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [Unreleased]

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Security
- ...

FAQ

Warum taucht „Agent-NN“ noch auf?
Weil technische Slugs (agentnn, agent-nn) absichtlich vorerst erhalten bleiben, um keine Import-/Publish-/Deploy-Regressions auszulösen.

Ist AdminBot Teil der ABrain-Architektur?
AdminBot ist eine externe Sicherheitsgrenze. ABrain nutzt nur einen strikt read-only Adapter im Default-Scope.

Wie funktioniert Approval/HITL?
Wenn Governance „Approval Required“ entscheidet, pausiert der Core den Plan und liefert approval_id. Danach approve/reject und deterministisches Resume.

Wo sehe ich Traces/Explainability?
Über Control-Plane-Endpunkte (/control-plane/traces/...) oder MCP (abrain.get_trace, abrain.explain).

Welche Plattform wird unterstützt?
Python ist grundsätzlich plattformübergreifend; AdminBot v2 ist als Linux-Daemon ausgelegt. Für produktive AdminBot-Integration ist Linux empfohlen.
Referenzen und zentrale Dateien im Repo

    Core: services/core.py, core/execution/dispatcher.py, core/tools/*
    MCP v2: interfaces/mcp/*, docs/guides/MCP_USAGE.md
    AdminBot Adapter: adapters/adminbot/*, docs/integrations/adminbot/*
    Compose: docker-compose.yml, .env.example, Dockerfile
    API Gateway: api_gateway/main.py
    Dev/Arch Doku: docs/architecture/*, docs/setup/DEVELOPMENT_SETUP.md

Chat-Protokolle

    TODO: Bitte die zwei Chat-URLs eintragen, die im Projektkontext referenziert werden sollen.

    Chat 1: <CHAT_URL_1>
    Chat 2: <CHAT_URL_2>

Maintainer Checklist

    LICENSE im Repo-Root ergänzen (MIT laut pyproject)
    CI Workflow hinzufügen (.github/workflows/ci.yml) und Badge aktivieren
    CHANGELOG.md nach Keep a Changelog pflegen und Releases taggen
    Security-Invarianten (AdminBot Adapter + Core Dispatcher/Registry) bei Changes re-validieren
    .dockerignore ergänzen (Build-Kontext klein halten)
    Das Dockerfile Default-CMD (uvicorn api.server:app) gegen aktuellen Stand verifizieren

