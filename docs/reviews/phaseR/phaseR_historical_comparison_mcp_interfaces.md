# Phase R — Domain 6: MCP / Interfaces / APIs
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Welche Features existierten?**

`legacy-runtime/mcp/`:
- `mcp_server.py` (213 Zeilen) — Voller MCP-Server mit WebSocket-Support, Tool-Registration, Message-Handling.
- `mcp_client.py` (37 Zeilen) — MCP-Client für HTTP/WebSocket-Verbindungen.
- `mcp_gateway.py` (70 Zeilen) — Gateway zwischen externen Clients und internen Agenten.
- `mcp_ws.py` (40 Zeilen) — WebSocket-Server (separate Verbindung für Real-Time-Events).
- `context_adapter.py` (18 Zeilen) — Wandelt MCP-Messages in ModelContext um.

`mcp/` (Microservice-Package):
- 8 Sub-Services: agent_registry, llm_gateway, plugin_agent_service, routing_agent, session_manager, task_dispatcher, vector_store, worker_dev, worker_loh, worker_openhands.
- Jeder Service hatte eigene FastAPI-App, Routes, Schema, Dockerfile.

`interfaces/mcp_v1/`:
- Disabled MCP v1 Server (guarded by env var `MCP_V1_ENABLED`).
- Wurde immer mit `ImportError` abgebrochen.

`api/`:
- Alter API-Client, Endpoints, Models, Smolitux-Integration.

`legacy-runtime/integrations/langchain_mcp_adapter.py` (56 Zeilen):
- LangChain-zu-MCP-Adapter für LangChain-Tool-Aufrufe.

`tools/` (root):
- `generate_flowise_nodes.py` (134 Zeilen) — Generiert Flowise Custom Nodes aus Agent-Definitionen.
- `generate_flowise_plugin.py` (78 Zeilen) — Generiert Flowise Plugin-Package.
- `validate_plugin_manifest.py` (59 Zeilen) — Validiert Flowise Plugin-Manifests.

**Wie war die Architektur?**
- *Zwei MCP-Implementierungen* gleichzeitig: `legacy-runtime/mcp/` (aktiv) und MCP v1 in `mcp/` (disabled).
- *8 MCP-Microservices* mit eigenem Routing, Schema, Dockerfile.
- WebSocket für Real-Time-Events (kein REST-Polling).
- LangChain-Integration im MCP-Pfad.
- Flowise-Plugin-Generatoren als separate Tools.

**Welche Probleme gab es?**
- Zwei parallele MCP-Implementierungen → unklar welche "die echte" war.
- Microservice-MCP-Package war nie produktiv (immer disabled).
- LangChain-Dependency im MCP-Pfad.
- WebSocket für Real-Time war gut, aber kein persistenter State hinter dem WS.
- Flowise-Generatoren: Generierter Code war nie stabil getestet.

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

`interfaces/mcp/` (MCP v2):
- `server.py` — `StdioMCPServer`: Canonical MCP v2 via stdio. Tool-Registry, Request-Handling, `run_stdio_server()`.
- `tool_registry.py` — `MCPToolRegistry`: Registriert MCP-Tools mit Schema.
- `handlers/run_task.py` — Tool: `run_task`.
- `handlers/run_plan.py` — Tool: `run_plan`.
- `handlers/approval.py` — Tools: `approve_step`, `reject_step`, `list_pending_approvals`.
- `handlers/trace.py` — Tools: `get_trace`, `get_explainability`.

`api_gateway/main.py` — Canonical REST API:
- `POST /control-plane/tasks/run`
- `POST /control-plane/plans/run`
- `POST /control-plane/approvals/{id}/approve` / `reject`
- `GET /control-plane/overview`, `/traces`, `/approvals`, `/governance`, `/plans`
- Legacy-Bridge: `/chat`, `/sessions`, `/embed`

`adapters/adminbot/client.py` — Hardened HTTP-Client für AdminBot v2.

**Wie ist es strukturiert?**
- Eine einzige MCP-Implementierung: MCP v2 via stdio.
- Eine einzige REST-API: `api_gateway/main.py`.
- Kein WebSocket.
- Kein LangChain.
- Tool-Schema ist formal definiert (JSON Schema).

**Was wurde bewusst entfernt?**
- MCP v1 (disabled und gelöscht).
- WebSocket-Server (`mcp_ws.py`).
- LangChain-MCP-Adapter.
- Flowise-Generatoren.
- Microservice-MCP-Package.

---

### Bewertung

**Was war früher schlechter?**
- Zwei parallele MCP-Stacks → Konfusion.
- WebSocket ohne persistenten State.
- LangChain in einem Interface-Layer.
- Flowise-Generatoren ohne Stabilitätsgarantie.

**Was ist heute besser?**
- Einziger MCP-Stack: v2 via stdio.
- Klare Tool-Schemata mit JSON Schema.
- REST-API deckt alle Control-Plane-Endpoints ab.
- Kein LangChain.

**Wo gab es frühere Stärken?**
- `mcp_ws.py` — WebSocket für Real-Time-Events: Heute gibt es *kein* Real-Time-Notification-System. Wenn ein Approval-Request kommt, muss der Client `/control-plane/approvals` pollen. Ein WS würde das eleganter lösen.
- `mcp_client.py` — Ein SDK-Client für externe Systeme, die mit ABrain kommunizieren wollten. Heute gibt es keinen öffentlichen Python-SDK-Client.
- Flowise-Generatoren: Automatische Generierung von Integration-Code aus Agent-Definitionen war ein nützliches Developer-Tool, auch wenn die Implementation instabil war.

---

### Gap-Analyse

**Was fehlt heute?**
- Kein Real-Time-Notification-Kanal (WebSocket oder SSE): Clients müssen pollen.
- Kein öffentlicher Python-SDK-Client für externe Systeme.
- Kein automatischer Flowise-Node-Generator aus der aktuellen Adapter-Registry.

**Welche Ideen sind verloren gegangen?**
- WebSocket-basiertes Event-Streaming (Approval-Events, Task-Completion, Trace-Updates).
- Automatische Client-SDK-Generierung aus dem Tool-Registry.

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| MCP v1 / Microservice-MCP | A — bewusst verworfen |
| LangChain-MCP-Adapter | A — bewusst verworfen |
| WebSocket Real-Time Events | C — fehlt heute, nützlich für UI/Approval-Notifications |
| Python SDK Client | C — fehlt, würde Developer-Experience verbessern |
| Flowise-Node-Generator aus Adapter-Registry | C — nützlich, neue Implementierung nötig |
| MCP v2 via stdio | A — kanonisch, korrekt |
