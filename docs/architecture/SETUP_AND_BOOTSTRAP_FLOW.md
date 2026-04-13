# Setup And Bootstrap Flow

## Ziel

`scripts/setup.sh` ist der kanonische Bootstrap fuer einen frischen Online-Checkout von ABrain. Das Skript baut keine zweite Runtime und fuehrt keine parallele CLI ein. Es bereitet nur die vorhandenen kanonischen Pfade vor.

Der bevorzugte Einstieg ist:

```bash
./scripts/abrain setup
```

`./scripts/abrain` bleibt die kanonische Bash-CLI. `./scripts/abrain` bleibt nur ein duenner Legacy-Wrapper.

## Kanonische Bootstrap-Schritte

### 1. `env`

Aufgaben:

- `.venv` anlegen oder wiederverwenden
- `pip`, `setuptools` und `wheel` aktualisieren
- `.env` aus `.env.example` erzeugen, falls noch keine lokale Datei existiert

### 2. `deps`

Aufgaben:

- Python-Abhaengigkeiten aus `requirements-light.txt` installieren
- den aktuellen Runtime-Stand fuer Core, API Gateway und MCP vorbereiten

### 3. `cli`

Aufgaben:

- editable Installation des Projekts aktualisieren
- den Console-Entry `abrain-mcp` sauber regenerieren

Wichtig:

- `scripts/abrain` selbst wird weiterhin direkt aus dem Repository aufgerufen
- `abrain-mcp` ist nur der Python-Console-Entry fuer den MCP-v2-Server
- stale Entry-Points werden durch erneutes `setup cli` bzw. den vollen Lauf `setup` bereinigt

### 4. `api`

Aufgaben:

- `api_gateway.main` import-smoke
- Pruefung zentraler Control-Plane-Routen
- Ausgabe des kanonischen Startpfads

Kanonischer Start:

```bash
.venv/bin/python -m uvicorn api_gateway.main:app --reload
```

### 5. `mcp`

Aufgaben:

- MCP-v2-Serverlogik ueber `initialize` und `tools/list` smoke-testen
- keine historische v1- oder Parallel-Runtime

Kanonischer Start:

```bash
.venv/bin/python -m interfaces.mcp.server
```

Alternative nach editable Install:

```bash
.venv/bin/abrain-mcp
```

### 6. `ui`

Aufgaben:

- `frontend/agent-ui` installieren
- `npm run type-check`
- `npm run build`

Kanonischer Dev-Start:

```bash
cd frontend/agent-ui
npm run dev
```

## Empfohlene Abläufe

### Voller Online-Bootstrap

```bash
./scripts/abrain setup
```

### Nur Python- und MCP-Pfad

```bash
./scripts/abrain setup cli
./scripts/abrain setup mcp
```

### Nur Frontend

```bash
./scripts/abrain setup ui
```

## Abgrenzung

Dieses Setup ist bewusst klein und ehrlich:

- keine versteckten Helper-Verzeichnisse
- keine Docker-Orchestrierung als Voraussetzung
- keine historische ABrain-Setup-Architektur
- keine Duplikation von Runtime-Logik

Der Bootstrap richtet nur die heute vorhandenen kanonischen Repo-Pfade aus:

- `scripts/abrain`
- `scripts/setup.sh`
- `interfaces/mcp/server.py`
- `api_gateway/main.py`
- `frontend/agent-ui`
- `.venv`
