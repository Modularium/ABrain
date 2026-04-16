# Phase R — Reimplementation Candidates (Phase 5)

**Date:** 2026-04-12
**Branch:** `codex/phaseR-historical-re-review`

---

## Kategorien

- **A** — Bewusst verwerfen: Falsche Idee oder durch aktuellen Stand besser gelöst.
- **B** — Historisch interessant, aber heute irrelevant: Kein Wert für den aktuellen Entwicklungsstand.
- **C** — Wertvoll, aber nur als Neuimplementierung: Idee gut, alte Implementierung problematisch.
- **D** — Kritisch wertvoll → sollte zeitnah zurückkommen.

---

## Kategorie A — Bewusst verwerfen

| Kandidat | Grund |
|---|---|
| LangChain-basierte Execution | LangChain bringt schwere Deps und veraltete API. Adapter-Pattern ist besser. |
| Stateful Agents mit Memory im Core | Session-State im Agent ist schwer testbar und parallelisierbar. Orchestrator-State ist robuster. |
| PyTorch MetaLearner im Hot Path | Blockiert Latenz, echtes Embedding-Modell nie vorhanden. |
| MLflow im Core (synchron) | Schwere Dep für ein Interface-Layer. Trace-Store ist der richtige Ort. |
| 30+ Shell-Skripte | Maintenance-Albtraum. setup.sh + abrain ist besser. |
| Zwei parallele MCP-Stacks | MCP v2 ist der einzige richtige Stack. |
| Docker-Compose als Betriebsvoraussetzung | Kein Docker nötig. Lokaler Betrieb ist Ziel. |
| Microservice-Architektur (9 Services) | Erzeugt Parallelarchitektur. services/core.py ist besser. |
| Docusaurus + MkDocs parallel | Ein Doku-System ist ausreichend. |
| ECDSA Crypto für Agent-Identitäten | Kein produktiver Anwendungsfall im aktuellen Scope. |
| AgentContract (deklarativ ohne Enforcement) | Wurde durch Policy-Engine + ApprovalStore korrekt ersetzt. |

---

## Kategorie B — Historisch interessant, aber heute irrelevant

| Kandidat | Warum heute irrelevant |
|---|---|
| Federated Learning | ABrain ist single-node. Multi-Node-Federated Learning ist weit außerhalb des aktuellen Scopes. |
| A/B Testing der Routing-Policy | Interessant, aber kein User-Bedarf aktuell. |
| Peer-Rating zwischen Agenten | Kein Bedarf, wenn System eine handhabbare Anzahl Agenten hat. |
| Voting/Konsens-Mechanismus | HITL-Approval deckt diesen Bedarf besser für den aktuellen Scope. |
| Trust-Network als Graph | Relevant nur bei vielen autonomen Agenten mit History. Heute zu früh. |
| Agent-Coalitions (formal mit Leader/Goal) | Plan + Orchestrator deckt diesen Bedarf. Coalition-Metapher ist nicht nötig. |
| GGUF/LocalHF Provider | Relevant wenn lokale Modelle ein Ziel sind. Heute kein Fokus. |
| Docusaurus/MkDocs Website | Gut wenn System stabil und public ist. Heute ist der Fokus noch auf Stabilität. |

---

## Kategorie C — Wertvoll, aber nur als Neuimplementierung

### C1: Developer-CLI-Befehle

**Was war die Idee?**
`sdk/cli/` bot `abrain task run "..."`, `abrain agent list`, `abrain trace list`, `abrain approval list` — vollständige Developer-CLI.

**Warum war sie gut?**
Entwickler konnten ABrain direkt aus dem Terminal bedienen, ohne REST-Calls oder Browser. Debugging wurde drastisch beschleunigt.

**Warum war die alte Implementierung problematisch?**
War für die alte Microservice-Architektur gebaut, referenzierte alte Endpoints, war nicht auf `services/core.py` aufgebaut.

**Wie müsste sie heute gebaut werden?**
- Subcommands im `scripts/abrain` Bash-CLI (oder Python typer-Extension).
- Direkte Aufrufe an `services.core.*` via Python-Import oder HTTP an `api_gateway`.
- Subcommands: `abrain task run "..."`, `abrain agent list`, `abrain trace list [--limit N]`, `abrain approval list`, `abrain plan run "..."`.
- Keine separaten Dependencies — nutzt das bestehende venv.

---

### C2: Publishable Flowise-Plugin

**Was war die Idee?**
`integrations/flowise-legacy-runtime/` als publishbares Flowise-Plugin: Externe Nutzer können ABrain aus dem Flowise Hub installieren und als Node verwenden.

**Warum war sie gut?**
Flowise ist weit verbreitet. Ein Hub-Plugin ist kostenlose Distribution und macht ABrain für Low-Code-Nutzer zugänglich.

**Warum war die alte Implementierung problematisch?**
Referenzierte alte Microservice-Endpoints, kein stabiler Test, kein CI für Plugin-Build.

**Wie müsste sie heute gebaut werden?**
- Schlankes Flowise-Plugin (npm) das nur `POST /control-plane/tasks/run` und `GET /control-plane/overview` wrappt.
- Input: Task-String, ABrain-URL.
- Output: Ergebnis.
- Minimale Flowise-Node-Struktur (1 Node, 2 Outputs).
- Tests via Flowise-Test-Framework.
- CI: npm build + test.

---

### C3: LLM-Provider-Abstraction (lean)

**Was war die Idee?**
`core/llm_providers/` mit einheitlichem `LLMProvider`-Interface und YAML-basierter Konfiguration.

**Warum war sie gut?**
Provider-Switching (OpenAI → Anthropic → Local) ohne Code-Änderung. Für `POST /chat` und zukünftige LLM-Integration wichtig.

**Warum war die alte Implementierung problematisch?**
War an MLflow und `LLMGatewayService` gebunden. Kein formales Interface. `LocalHFProvider` required torch.

**Wie müsste sie heute gebaut werden?**
- Minimale `LLMProvider` Abstract Base Class: `generate(prompt: str) → str`.
- Konkrete Provider: `AnthropicProvider` (anthropic SDK), `OpenAIProvider` (openai SDK).
- Kein `GGUFProvider` / `LocalHFProvider` (zu komplex, kein Bedarf jetzt).
- YAML-Konfiguration (nutzt bestehendes `llm_config.yaml`).
- Integriert in `api_gateway/main.py` Chat-Endpoint.
- Keine Microservice-Ebene.

---

### C4: Auto-generierter API-Swagger-Doku

**Was war die Idee?**
`tools/cli_docgen.py` hatte das Konzept der automatischen Dokumentationsgenerierung. Im API-Kontext: OpenAPI-Schema auto-generiert aus FastAPI.

**Warum war sie gut?**
FastAPI generiert Swagger-Schema automatisch. Ein exposed `/docs` oder ein exportiertes `openapi.json` wäre wertvoller als jede manuell geschriebene API-Doku.

**Warum war die alte Implementierung problematisch?**
`generate_openapi.py` war für alte Service-Endpoints und nicht aktuell.

**Wie müsste sie heute gebaut werden?**
- FastAPI Swagger UI: `/docs` in `api_gateway/main.py` aktivieren (ist standardmäßig vorhanden, aber muss prüfen ob aktuell disabled).
- OpenAPI-JSON via `GET /openapi.json` exportierbar.
- CI-Schritt: openapi.json in `docs/api/openapi.json` schreiben.
- Kein manueller Aufwand.

---

### C5: Routing-Decision-Annotation im Trace

**Was war die Idee?**
`training/data_logger.py` loggete jede Routing-Entscheidung mit allen Kandidaten-Scores, gewähltem Agent und Outcome.

**Warum war sie gut?**
Ermöglicht Debugging: Warum wurde Agent X gewählt? Welche Scores hatten A, B, C?

**Warum war die alte Implementierung problematisch?**
MLflow als Dependency, synchron, blockierend.

**Wie müsste sie heute gebaut werden?**
- `RoutingDecision` in `core/decision/routing_engine.py` ist bereits als Dataclass vorhanden.
- `TraceSpan` in `core/audit/trace_models.py` hat `metadata: dict`.
- Änderung: `routing_engine.route_task()` schreibt `RoutingDecision` (alle Kandidaten + Scores + Gewinner) als `metadata` in den aktuellen `TraceSpan`.
- Keine neue Dependency.
- UI: TracesPage zeigt Routing-Decision-Detail an.

---

## Kategorie D — Kritisch wertvoll → sollte zeitnah zurückkommen

### D1: Trust-Score als adaptive ApprovalPolicy

**Was war die Idee?**
`core/trust_evaluator.py` berechnete: `trust = (success_rate + feedback + token_efficiency + reliability) / 4`. Ein Agent mit hohem Trust benötigt weniger Oversight.

**Warum war sie gut?**
Macht HITL-Approval *adaptiv*: Neue oder unzuverlässige Agenten erhalten mehr Oversight. Bewährte Agenten erhalten mehr Autonomie. Das ist das Kernprinzip eines lernenden Governance-Systems.

**Warum war die alte Implementierung problematisch?**
Trust-Score war berechnet aber *nie mit Routing oder Approval verbunden*. Es war ein Orphan-Konzept.

**Wie müsste sie heute gebaut werden?**
- `TrustScoreCalculator` als neues Modul in `core/decision/` oder `core/governance/`.
- Input: `PerformanceHistory` (bereits vorhanden in `core/decision/performance_history.py`).
- Output: `float` (0.0–1.0) Trust-Score pro Agent.
- Integration: `ApprovalPolicy.requires_approval(descriptor, ctx)` prüft Trust-Score.
  - Trust < 0.5 → Approval required.
  - Trust ≥ 0.8 → No Approval (für konfigurierte Policy).
- Trust-Score wird nach jeder Task-Ausführung aus `PerformanceHistory` neu berechnet.
- Test: Unit-Tests für `TrustScoreCalculator` + `ApprovalPolicy`-Integration.
- Passt in: `core/governance/` oder `core/decision/`.
- Umgeht keine Policy-Layer: Es ist *Teil* der Policy, nicht ein Bypass.
- Erzeugt keine zweite Runtime.

**Prio:** Hoch. Kleine Implementierung, großer systemischer Wert.

---

### D2: System-Health-Tab in der UI

**Was war die Idee?**
Das alte Dashboard zeigte CPU/GPU/Memory/Disk, Active Agents, Task Queue, System Components mit Status und Version — alles auf einem Screen.

**Warum war sie gut?**
Ein Operator muss *sofort sehen können* ob das System gesund ist. Heute gibt es kein äquivalentes Summary-View.

**Warum war die alte Implementierung problematisch?**
Alles Mock-Daten. Monolithische TSX-Datei. Kein State-Management.

**Wie müsste sie heute gebaut werden?**
- Neues `SystemHealthPage.tsx` in `frontend/agent-ui/src/pages/`.
- Nutzt `/control-plane/overview` Endpoint (bereits vorhanden in `api_gateway/main.py`).
- Erweiterung von `/control-plane/overview`: Füge `agents_registered`, `active_policies`, `pending_approvals_count`, `recent_traces_count`, `plan_state` hinzu (alle aus bestehenden Services abrufbar).
- Prometheus-Metriken für CPU/Memory via `GET /metrics` (bereits vorhanden).
- Kein neuer Backend-Code nötig, nur Frontend-Page.
- Kein Legacy-Reaktivierung.

**Prio:** Hoch. Reiner Frontend-Aufwand auf stabiler Backend-Basis.

---

## Zusammenfassung

| Kategorie | Kandidaten |
|---|---|
| **A** (verwerfen) | 11 Kandidaten |
| **B** (historisch, heute irrelevant) | 8 Kandidaten |
| **C** (Neuimplementierung sinnvoll) | 5 Kandidaten: Developer-CLI, Flowise-Plugin, LLM-Provider-Abstraktion, Swagger-Doku, Routing-Trace-Annotation |
| **D** (kritisch, zeitnah) | 2 Kandidaten: Trust-Score ApprovalPolicy, System-Health-UI |
