# Phase R — Architecture Cross-Check (Phase 7)

**Date:** 2026-04-12
**Branch:** `codex/phaseR-historical-re-review`
**Purpose:** Verify all reimplementation candidates against the canonical architecture. Disqualify anything that would violate invariants.

---

## Kanonische Architektur-Invarianten

Aus `docs/architecture/CANONICAL_REPO_STRUCTURE.md`:

1. `services/core.py` ist der **einzige Service-Layer**.
2. `api_gateway/main.py` ist die **einzige REST-API**.
3. `interfaces/mcp/` ist das **einzige MCP-Interface**.
4. `frontend/agent-ui/` ist die **einzige UI**.
5. `Decision → Execution → Approval → Governance → Audit → Orchestration` ist der **kanonische Runtime-Stack**.
6. Kein Task kommt durch ohne Policy-Check.

---

## Cross-Check aller Kandidaten (C und D)

---

### D1: Trust-Score als adaptive ApprovalPolicy

**Würde es Policy umgehen?**
Nein. Der Trust-Score *ist* die Policy: `ApprovalPolicy.requires_approval()` wird durch Trust-Score-Logik *parametrisiert*, nicht umgangen. Ein High-Trust-Agent bekommt Approval-Bypass *weil die Policy es so definiert*, nicht durch Bypass der Policy-Engine.

**Würde es eine zweite Runtime erzeugen?**
Nein. `TrustScoreCalculator` ist ein neues Modul in `core/decision/` oder `core/governance/`. Es nutzt `PerformanceHistory` (bereits vorhanden) und liefert einen Float an `ApprovalPolicy`. Kein neuer Service-Layer.

**Würde es Adapter umgehen?**
Nein. Trust-Score beeinflusst ob Approval nötig ist, nicht wie der Task ausgeführt wird.

**Würde es MCP umgehen?**
Nein. MCP-Handlers nutzen `services/core.py` → `ApprovalPolicy`. Der Trust-Score ist im Policy-Layer.

**Passt es in Decision → Execution → Governance → Approval → Audit → Orchestration?**
Ja: Trust-Score gehört in `core/governance/` oder `core/decision/`. Es wird von `ApprovalPolicy` konsumiert, bevor `core/execution/` aufgerufen wird.

**Verdict: APPROVED — konform mit Architektur**

---

### D2: System-Health-Tab in der UI

**Würde es Policy umgehen?**
Nein. Rein lesend (GET-Requests).

**Würde es eine zweite Runtime erzeugen?**
Nein. Nutzt `/control-plane/overview` (bereits vorhanden in `api_gateway/main.py`).

**Würde es Adapter umgehen?**
Nein. Keine Execution.

**Würde es MCP umgehen?**
Nein. Frontend spricht gegen REST-API.

**Würde es `/control-plane/overview` erweitern müssen?**
Ja — der Endpoint müsste `agents_registered_count`, `pending_approvals_count`, `recent_traces_count`, `active_policy_count` liefern. Das sind alles Daten aus bestehenden Services. Keine neue Architektur-Schicht nötig.

**Passt es in Decision → Execution → Governance → Approval → Audit → Orchestration?**
Ja: Liest nur von bestehenden Schichten. Ändert nichts.

**Verdict: APPROVED — konform mit Architektur**

---

### C1: Developer-CLI-Befehle

**Würde es Policy umgehen?**
Nein, wenn CLI `services/core.py` aufruft. Policy-Enforcement bleibt in `core/governance/`.

**Würde es eine zweite Runtime erzeugen?**
Nein, wenn CLI `services/core.py` direkt importiert oder via HTTP gegen `api_gateway` spricht. Kein zweiter Service.

**Würde es Adapter umgehen?**
Nein. CLI → `services.core.run_task()` → `core/decision/` → `core/execution/adapters/`. Voller Stack.

**Würde es MCP umgehen?**
MCP ist für externe Tool-Integration. CLI ist für lokale Developer-Nutzung. Kein Konflikt.

**Passt es in Decision → Execution → Governance → Approval → Audit → Orchestration?**
Ja: CLI ist nur ein neues *Entry Point* das denselben kanonischen Stack aufruft wie REST und MCP.

**Mögliche Risiken:**
- Wenn CLI direkt in `services/core.py` importiert (kein HTTP), müsste die venv aktiv sein.
- CLI darf keine eigene Konfiguration oder eigene Runtime starten.
- CLI darf keine eigene Policy oder eigenen Approval-Flow haben.

**Verdict: APPROVED mit Einschränkung — muss via `services/core.py` oder HTTP gehen, kein Bypass**

---

### C2: Publishable Flowise-Plugin

**Würde es Policy umgehen?**
Nein. Plugin ruft `POST /control-plane/tasks/run` — voller Stack inklusive Policy.

**Würde es eine zweite Runtime erzeugen?**
Nein. Das Plugin ist ein externes npm-Package das ABrain über REST anspricht. Keine neue Python-Runtime.

**Würde es Adapter umgehen?**
Nein. REST-API → `services/core.py` → voller Stack.

**Würde es MCP umgehen?**
Nein. Plugin nutzt REST-API, nicht MCP.

**Passt es in Decision → Execution → Governance → Approval → Audit → Orchestration?**
Ja: Plugin ist ein externer Client, kein interner Stack-Element.

**Mögliche Risiken:**
- Plugin braucht Authentifizierung gegen `api_gateway` (JWT). Muss konfigurierbar sein.
- Plugin darf keine ABrain-interne Logik duplizieren.

**Verdict: APPROVED — vollständig extern, keine Architektur-Verletzung**

---

### C3: LLM-Provider-Abstraction (lean)

**Würde es Policy umgehen?**
Nein. LLM-Provider ist für den `POST /chat`-Endpoint. Chat-Requests würden ebenfalls durch `services/core.py` geroutet werden.

**Würde es eine zweite Runtime erzeugen?**
Nein, wenn LLM-Provider als Modul in `core/` lebt und von `services/core.py` genutzt wird.

**Würde es Adapter umgehen?**
Heikel: Der Chat-Endpoint könnte LLM direkt aufrufen *ohne* den Execution-Adapter-Layer. Das wäre ein Bypass.

**Kritischer Punkt:** LLM-Provider muss als `BaseAdapter` implementiert werden oder in den Routing/Decision-Flow integriert werden. Ein direkter LLM-Call in `api_gateway/main.py` oder ein neues `llm_gateway` Service wäre ein Architektur-Verstoß.

**Lösung:**
- `LLMProvider` wird als neuer Adapter-Typ in `core/execution/adapters/` implementiert.
- Ein `LLMAdapter` folgt `BaseAdapter`.
- Chat-Requests gehen via `services/core.run_task()` mit `adapter_type=llm`.
- Routing-Engine wählt `LLMAdapter` basierend auf Task.

**Passt es in Decision → Execution → Governance → Approval → Audit → Orchestration?**
Ja, wenn als Adapter implementiert: LLM ist ein weiterer Execution-Adapter.

**Verdict: APPROVED mit Design-Constraint — LLM muss als Adapter implementiert werden, kein direkter Bypass**

---

### C4: Auto-generierter API-Swagger

**Würde es irgendwas verletzen?**
Nein. FastAPI generiert Swagger automatisch. Es ist eine *Exposing*-Änderung, keine Architektur-Änderung.

**Einzige Prüfung:** `api_gateway/main.py` hat `FastAPI(docs_url=None, redoc_url=None)` oder ähnliches?

**Verdict: APPROVED — minimale Änderung, null Risiko**

---

### C5: Routing-Decision-Annotation im Trace

**Würde es Policy umgehen?**
Nein. Rein observierend: Zusätzliche Annotation im bestehenden Trace.

**Würde es eine zweite Runtime erzeugen?**
Nein. `routing_engine.py` schreibt in den aktiven `TraceSpan`. Kein neuer Service.

**Würde es Adapter umgehen?**
Nein. Rein Logging/Tracing.

**Würde es MCP umgehen?**
Nein.

**Passt es in Decision → Execution → Governance → Approval → Audit → Orchestration?**
Ja: Decision-Layer → Audit-Layer. Das ist der kanonische Pfad.

**Verdict: APPROVED — minimale Änderung, maximaler Debugging-Wert**

---

## Summary Cross-Check

| Kandidat | Status | Bedingung |
|---|---|---|
| D1: Trust-Score ApprovalPolicy | APPROVED | Muss in `core/governance/` leben |
| D2: System-Health-UI-Tab | APPROVED | Erweiterung von `/control-plane/overview` nötig |
| C1: Developer-CLI | APPROVED | Muss via `services/core.py` oder HTTP gehen |
| C2: Flowise-Plugin | APPROVED | Externer Client, keine interne Logik |
| C3: LLM-Provider-Abstraction | APPROVED | Muss als Adapter implementiert werden |
| C4: Swagger-Doku | APPROVED | Minimale Änderung |
| C5: Routing-Decision-Trace | APPROVED | Minimale Änderung |

**Kein Kandidat wurde disqualifiziert.** Alle können auf dem kanonischen Kern aufgebaut werden.

---

## Was definitiv NICHT zurückkommt (Phase 8 — kein Legacy-Leak)

| Verbotenes Konzept | Warum verboten |
|---|---|
| `managers/` Directory | Erzeugt Parallelarchitektur |
| `legacy-runtime/` Package | Zweite CLI-Runtime |
| `sdk/` altes SDK | Referenziert alte Endpoints |
| `training/` mit PyTorch/MLflow | Erzeugt schwere Deps im Core |
| `services/llm_gateway/` Microservice | Zweiter Service-Layer |
| `mcp/` Microservice-Package | Zweiter MCP-Stack |
| LangChain im Execution-Pfad | Schwere Dep, falsche Schicht |
| Docker-Compose für lokalen Betrieb | Bricht Invariant: kein Docker-Requirement |
| 30+ Shell-Skripte | Maintenance-Albtraum, Duplikat von setup.sh |
| Microservice-Architektur (9+ Services) | Zweite Runtime |
| Zwei parallele Doku-Systeme | Docusaurus-Cache in Git |
