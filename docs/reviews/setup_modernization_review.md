# Setup Modernization Review

Datum: 2026-04-12
Branch: `codex/setup-modernization-online-install`

## 1. Vorheriger Legacy-Zustand

Vor der Ueberarbeitung war `scripts/setup.sh` im aktuellen ABrain-Repo nicht mehr real nutzbar:

- sofortiger Abbruch ueber fehlende `scripts/lib/*`- und `scripts/helpers/*`-Dateien
- historische Docker-/Legacy-MCP-/Repair-Annahmen statt heutiger Repo-Realitaet
- `scripts/abrain setup ...` war dadurch faktisch blockiert
- `requirements-light.txt` enthielt eine stark veraltete, zu breite Paketliste
- `pyproject.toml` war fuer `pip install -e .` inkonsistent, weil `project.scripts`
  vorhanden war, aber die minimale `project`-Metadatenbasis fehlte
- `core/config.py` war mit frischen Pydantic-v2-Dependencies nicht importierbar,
  weil `model_config` und die alte innere `Config` gleichzeitig verwendet wurden

## 2. Was modernisiert wurde

### `scripts/setup.sh`

Das Skript wurde als kleiner, linearer Bootstrap auf den heutigen kanonischen Repo-Stand gebracht:

- keine Abhaengigkeit mehr auf historische Helper-Verzeichnisse
- klare Subcommands: `env`, `deps`, `cli`, `api`, `mcp`, `ui`, `all`
- lesbare Fehler statt roher `source`-Abbrueche
- `cli` erzeugt bzw. regeneriert `abrain-mcp`
- `api` und `mcp` fuehren echte Smokes aus
- `ui` fuehrt `npm ci`, `npm run type-check` und `npm run build` aus
- wiederholte Laeufe greifen nicht mehr unnoetig ins Netz, solange die Venv schon existiert
- editable Install nutzt `--no-build-isolation`, damit ein bereits installiertes
  `poetry-core` lokal wiederverwendet wird

### CLI-Integration

- `scripts/abrain` delegiert `setup` jetzt direkt an `scripts/setup.sh`
- der fruehere Blocker auf `scripts/lib` und `scripts/helpers` wurde entfernt
- die Hilfe fuer `abrain setup` beschreibt jetzt die echten heutigen Schritte
- `scripts/agentnn` blieb unangetastet als duenner Legacy-Wrapper

### Dependencies und Packaging

- `requirements-light.txt` wurde auf den nachweislich aktiven kanonischen Kern reduziert:
  `fastapi`, `uvicorn`, `httpx`, `pydantic`, `pydantic-settings`, `slowapi`,
  `prometheus-client`, `structlog`, `python-jose[cryptography]`, `pyyaml`, `pytest`
- `pyproject.toml` enthaelt jetzt eine minimale `[project]`-Sektion, damit
  `pip install -e .` konsistent funktioniert
- `pyproject.toml` wurde fuer den API-Gateway-Pfad um `python-jose` ergaenzt

### Konfiguration

- `.env.example` wurde auf reale lokale Runtime-/Gateway-/UI-Defaults umgestellt
- alte Datenbank-, Docker- und MLflow-Annahmen wurden aus der Vorlage entfernt
- das Setup erzeugt bei Bedarf eine lokale `.env` aus dieser Vorlage, ueberschreibt
  aber keine bestehende Datei

### Frischer Runtime-Fix

- `core/config.py` verwendet jetzt eine saubere Pydantic-v2-`SettingsConfigDict`
  statt der ungueltigen Mischung aus `model_config` und innerer `Config`

## 3. Offizielle Install-/Config-/Startpfade

Kanonisch nach dieser Ueberarbeitung:

- Bootstrap: `./scripts/abrain setup all`
- Nur Python/MCP: `./scripts/abrain setup cli`
- API Gateway: `.venv/bin/python -m uvicorn api_gateway.main:app --reload`
- MCP v2: `.venv/bin/python -m interfaces.mcp.server`
- MCP Console-Entry nach editable Install: `.venv/bin/abrain-mcp`
- UI Dev: `cd frontend/agent-ui && npm run dev`

## 4. Reale Verifikation

### Shell und CLI

- `bash -n scripts/setup.sh scripts/abrain scripts/agentnn`
- `shellcheck scripts/setup.sh scripts/abrain scripts/agentnn`
- `./scripts/abrain --version`
- `./scripts/abrain help`
- `./scripts/abrain help setup`
- `./scripts/agentnn --version`
- `./scripts/setup.sh help`
- `ABRAIN_VENV_DIR=/tmp/abrain-setup-smoke-20260412 ./scripts/abrain setup mcp`
- `ABRAIN_VENV_DIR=/tmp/abrain-setup-smoke-20260412 ./scripts/abrain setup api`

### Frischer Online-Bootstrap

Validiert in einer frischen temporären Venv unter `/tmp/abrain-setup-smoke-20260412`:

- initialer Lauf von `ABRAIN_VENV_DIR=/tmp/abrain-setup-smoke-20260412 ./scripts/setup.sh all`
  zur Ermittlung realer Packaging-/Runtime-Bruecken
- danach gezielte Fixes und erneute Verifikation ueber:
  - `ABRAIN_VENV_DIR=/tmp/abrain-setup-smoke-20260412 ./scripts/setup.sh cli`
  - `ABRAIN_VENV_DIR=/tmp/abrain-setup-smoke-20260412 ./scripts/setup.sh api`
  - `ABRAIN_VENV_DIR=/tmp/abrain-setup-smoke-20260412 ./scripts/setup.sh mcp`
  - final erneut `ABRAIN_VENV_DIR=/tmp/abrain-setup-smoke-20260412 ./scripts/setup.sh all`

Ergebnis:

- frische Venv-Erzeugung funktioniert
- minimale Python-Dependencies werden sauber installiert
- editable Install funktioniert
- `abrain-mcp` wird korrekt erzeugt
- MCP-v2-Smoke funktioniert
- API-Gateway-Import funktioniert nach dem Pydantic-v2-Fix
- der komplette End-to-End-Setup-Flow `all` lief am Ende grün durch

### Python / Backend

- `.venv/bin/python -m py_compile core/config.py api_gateway/main.py interfaces/mcp/server.py scripts/abrain_mcp.py`
- `.venv/bin/python -m pytest -o python_files='test_*.py' tests/state tests/mcp tests/approval tests/orchestration tests/execution tests/decision tests/adapters tests/core tests/services tests/integration/test_node_export.py`

Ergebnis:

- `161 passed, 1 skipped`

### Frontend

- `./scripts/setup.sh ui`
- `cd frontend/agent-ui && npm run type-check`
- `cd frontend/agent-ui && npm run build`
- `cd frontend/agent-ui && npm run lint`

Ergebnis:

- `npm ci`, `type-check`, `build` und `lint` liefen grün
- im Sandbox-Modus scheiterte `npm ci` zunaechst an `esbuild`-`EPERM`; ausserhalb
  der Sandbox lief derselbe Schritt sauber durch

## 5. Grenzen und Einordnung

- Das bestehende lokale `.venv` im Arbeitsverzeichnis war vorab nicht als frischer
  Setup-Referenzzustand geeignet; deshalb wurde die echte Online-Verifikation
  bewusst in einer frischen temporären Venv durchgefuehrt.
- Das Setup hat lokal eine `.env` aus `.env.example` erzeugt. Diese Datei bleibt
  unversioniert und ist nicht Teil des Commit-Scopes.
- `requirements-light.txt` ist jetzt auf den kanonischen Kern reduziert. Falls
  spaeter wieder optionale Alt-Integrationen reaktiviert werden, sollten deren
  zusaetzliche Dependencies explizit und getrennt betrachtet werden statt wieder
  in diesen Bootstrap-Pfad zu rutschen.

## 6. Explizite Bestaetigungen

- keine Parallel-Implementierung gebaut
- keine zweite CLI aufgebaut
- keine alten `scripts/lib`- oder `scripts/helpers`-Strukturen wiederbelebt
- `scripts/setup.sh` entspricht jetzt dem realen bereinigten ABrain-Repo deutlich besser
