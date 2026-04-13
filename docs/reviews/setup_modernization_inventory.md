# Setup Modernization Inventory

Datum: 2026-04-12
Branch: `codex/setup-modernization-online-install`

## Geprüfte Dateien

- `scripts/setup.sh`
- `scripts/README.md`
- `README.md`
- `CONTRIBUTING.md`
- `docs/guides/MCP_USAGE.md`
- `docs/mcp/README.md`
- `docs/mcp/MCP_SERVER_USAGE.md`
- `docs/architecture/MCP_V2_INTERFACE.md`
- `pyproject.toml`
- `requirements-light.txt`
- `.env.example`
- `frontend/agent-ui/package.json`
- `api_gateway/main.py`
- `interfaces/mcp/server.py`
- `scripts/abrain`
- `scripts/abrain`
- `scripts/abrain_mcp.py`

## Ist-Zustand vor der Modernisierung

### 1. `scripts/setup.sh` war nicht mehr kanonisch nutzbar

- Das Skript brach sofort auf fehlenden Dateien unter `scripts/lib/*` und `scripts/helpers/*` ab.
- Diese Verzeichnisse sind im bereinigten Main nicht mehr vollstaendig vorhanden und gehoeren nicht mehr zur kanonischen Repo-Struktur.
- Die vorhandene Logik deckte zahlreiche historische Modi wie Docker-, Repair- und Legacy-MCP-Flows ab, die nicht mehr zur heutigen ABrain-Realitaet passen.

### 2. `abrain setup` war dadurch effektiv blockiert

- `scripts/abrain` delegierte zwar an `scripts/setup.sh`, blockierte den Aufruf aber vorab mit einer Runtime-Pruefung auf `scripts/lib` und `scripts/helpers`.
- Ergebnis: Die kanonische Bash-CLI verwies auf ein Setup-Kommando, das im aktuellen Repo-Stand absichtlich nicht mehr lauffaehig war.

### 3. Die realen heutigen Startpfade sind klarer als das alte Setup

Aktuell kanonisch im bereinigten Repo:

- Bash-CLI: `scripts/abrain`
- Legacy-Kompatibilitaet: `scripts/abrain` als duenner Wrapper
- MCP v2: `python -m interfaces.mcp.server`
- MCP Console-Entry nach editable Install: `abrain-mcp`
- REST API: `python -m uvicorn api_gateway.main:app --reload`
- UI: `frontend/agent-ui`
- Python-Umgebung: `.venv`

### 4. Dependency-Realitaet hatte eine konkrete Luecke

- `api_gateway/main.py` importiert `slowapi` und `jose`.
- `requirements-light.txt` enthielt `slowapi`, aber kein `python-jose`.
- Dadurch war der dokumentierte API-Gateway-Import auf einer frischen Installation nicht vollstaendig abgesichert.
- `prometheus-client` war in `pyproject.toml`, aber nicht in `requirements-light.txt` enthalten.
- Ein Import-Scan ueber `core/`, `services/`, `api_gateway/`, `interfaces/`,
  `adapters/` und `tests/` zeigte zusaetzlich, dass viele fruehere Pakete aus
  `requirements-light.txt` im heutigen kanonischen Pfad gar nicht mehr direkt
  importiert werden.
- Dazu gehoerten u. a. `langchain`, `mlflow`, `transformers`, `chromadb`,
  `celery`, `docling`, `torch`-nahe Stacks und weitere schwere Alt-Abhaengigkeiten.

### 5. `.env.example` war noch teilweise von frueheren Repo-Annahmen gepraegt

- Alte Datenbank-/Docker-/MLflow-Beispiele waren noch enthalten.
- Das passte nicht mehr gut zu einem lokalen, linearen Bootstrap fuer den heutigen bereinigten Main.
- Fuer das aktuelle Repo relevanter sind lokale Runtime-Pfade, API-/Auth-Basics, Service-Bridge-URLs und UI-Defaults.

## Was `scripts/setup.sh` heute real leisten soll

Das moderne Setup soll nur den aktuellen kanonischen Bootstrap abdecken:

1. `.venv` anlegen oder wiederverwenden
2. Python-Abhaengigkeiten fuer den aktuellen Runtime-Stand installieren
3. `abrain-mcp` ueber editable Install sauber erzeugen oder auffrischen
4. MCP v2 gegen `interfaces/mcp/server.py` smoke-testen
5. API Gateway gegen `api_gateway.main` smoke-testen
6. `frontend/agent-ui` per `npm ci`, `type-check` und `build` vorbereiten
7. Eine kleine, echte `.env`-Ausgangsbasis bereitstellen, ohne Legacy-Helper-Magie

## Nicht-Ziele

- keine zweite CLI
- keine alternative Runtime
- kein Wiederaufbau von `scripts/lib` oder `scripts/helpers`
- keine Rueckkehr zu Legacy-MCP-v1- oder Docker-zentrierten Setup-Annahmen
- kein grosser Repo-Umbau ausserhalb von Setup, CLI-Integration und zugehoeriger Doku
