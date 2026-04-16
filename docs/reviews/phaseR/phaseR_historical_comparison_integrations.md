# Phase R — Domain 10: Integrations
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Welche Features existierten?**

`integrations/flowise-legacy-runtime/` — Flowise-Plugin:
- Custom Flowise-Plugin, das ABrain als Node in Flowise einbindet.
- Eigene `package.json`, Build-Konfiguration.
- Veröffentlichbar auf Flowise Hub.

`integrations/flowise-nodes/` — Flowise Custom Nodes:
- Separate Custom-Nodes für Flowise, die ABrain-Funktionen exponieren.
- Build-System für Flowise-Node-Package.

`integrations/n8n-legacy-runtime/` — n8n-Integration:
- n8n-Node der ABrain-Tasks triggern kann.
- Eigene n8n-Node-Struktur.

`agents/openhands/` — OpenHands-Agenten:
- `base_openhands_agent.py` (310 Zeilen) — Basis-OpenHands-Agent mit Docker-Container-Management.
- `compose_agent.py` (304 Zeilen) — OpenHands Agent via Docker Compose.
- `docker_agent.py` (271 Zeilen) — OpenHands Agent via Docker.

`legacy-runtime/integrations/langchain_mcp_adapter.py` (56 Zeilen):
- LangChain-zu-MCP-Adapter.

`tools/generate_flowise_nodes.py` (134 Zeilen) / `generate_flowise_plugin.py` (78 Zeilen):
- Code-Generatoren für Flowise-Integrations.

**Wie war die Architektur?**
- Flowise-Integration als *eigenständiges npm-Package* (separate Build-Pipeline).
- n8n-Integration als *eigenständiger n8n-Node* (separate Struktur).
- OpenHands-Agenten direkt im `agents/`-Verzeichnis (tight coupling).
- LangChain-Adapter als dünner Wrapper.
- Code-Generatoren als separate Tools.

**Welche Probleme gab es?**
- Flowise-Plugin war nie stabil deployed: Code-Generatoren erzeugten Code, der nicht getestet war.
- n8n-Integration referenzierte alte API-Endpoints.
- OpenHands-Agenten benötigten Docker → Setup-Komplexität.
- LangChain-Adapter war ein Wrapper um einen Wrapper: LangChain → MCP → ABrain.
- Kein gemeinsames Adapter-Interface: Jede Integration war unterschiedlich strukturiert.

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

`adapters/adminbot/` — AdminBot v2 Adapter (Production):
- `client.py` — Hardened HTTP-Client mit Rate-Limiting, Retry, Security-Headers.
- `service.py` — AdminBot-Service-Layer.

`adapters/flowise/` — Flowise Adapter (Import/Export):
- `importer.py` — Importiert Flowise-Flows als ABrain-Agent-Definitionen.
- `exporter.py` — Exportiert ABrain-Agenten als Flowise-Flows.
- `models.py` — Flowise-Datenmodelle.

`core/execution/adapters/` — 6 Execution-Adapters:
- `adminbot_adapter.py` — AdminBot-Execution.
- `openhands_adapter.py` — OpenHands-Execution.
- `claude_code_adapter.py` — Claude Code-Execution.
- `codex_adapter.py` — Codex-Execution.
- `n8n_adapter.py` — n8n-Execution.
- `flowise_adapter.py` — Flowise-Execution.

**Wie ist es strukturiert?**
- Gemeinsames `BaseAdapter` Interface für alle Execution-Adapters.
- `AdapterRegistry` für dynamische Adapter-Auswahl.
- AdminBot ist die einzige *produktive* Integration (vollständig getestet).
- Flowise hat Import/Export (bidirektional).

---

### Bewertung

**Was war früher schlechter?**
- Kein gemeinsames Adapter-Interface.
- Flowise-Integration als npm-Package: schwer zu maintainen.
- OpenHands-Agenten Docker-abhängig.
- n8n-Integration nie produktiv.
- Code-Generatoren erzeugten untesteten Code.

**Was ist heute besser?**
- Einheitliches `BaseAdapter` Interface.
- `AdapterRegistry` für dynamische Adapter-Auswahl.
- AdminBot ist vollständig getestet und produktiv.
- Flowise-Import/Export ist bidirektional.

**Wo gab es frühere Stärken?**
- `integrations/flowise-legacy-runtime/` war ein **publishable Flowise Plugin**: Externe Benutzer hätten ABrain direkt aus dem Flowise Hub installieren können. Das ist ein wichtiger Distribution-Kanal für Flowise-Nutzer.
- `integrations/n8n-legacy-runtime/` ermöglichte **n8n-Workflow-Trigger**: n8n-Nutzer hätten ABrain-Tasks direkt aus n8n-Workflows auslösen können (bidirektional: n8n → ABrain → Ergebnis zurück nach n8n).
- Die Code-Generatoren (`generate_flowise_nodes.py`) hatten die **richtige Idee**: Aus dem Agent-Registry automatisch Integration-Code generieren. Die Implementierung war instabil, aber das Konzept ist wertvoll.

---

### Gap-Analyse

**Was fehlt heute?**
- Kein **publishbares Flowise-Plugin** (nur Import/Export, kein Hub-publishable Package).
- Kein **n8n-Node** (nur Execution-Adapter, kein n8n-Hub-publishable Node).
- Keine **automatische Integration-Code-Generierung** aus der Adapter-Registry.
- AdminBot ist produktiv, aber alle anderen Adapters sind *nicht getestet in Produktion* (nur Integration-Tests mit Mocks).

**Welche Ideen sind verloren gegangen?**
- Flowise Hub Publikation (Distribution-Kanal).
- n8n Hub Publikation (Distribution-Kanal).
- Auto-generierte Integration-Clients.

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| Flowise als npm-Package (separater Build) | B — interessant aber zu komplex für aktuellen Stand |
| n8n-Node (separater Build) | B — interessant aber zu komplex für aktuellen Stand |
| Publishable Flowise Hub Plugin | C — wertvoll für Adoption, aber neue Implementierung nötig |
| Publishable n8n Hub Node | C — wertvoll für Adoption, neue Implementierung nötig |
| Auto-generierte Integration-Clients | C — Konzept wertvoll, neue Implementierung nötig |
| LangChain-MCP-Adapter | A — bewusst verworfen |
| OpenHands Docker-Agent | A — bewusst verworfen (durch openhands_adapter ersetzt) |
