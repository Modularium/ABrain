# Post-Cleanup README / Setup / Onboarding Audit

**Datum:** 2026-04-12
**Scope:** `README.md`, Onboarding-/Setup-Doku, kanonische Skripte, MCP-Doku, CI-Pfade

## Ergebnis auf einen Blick

Der bereinigte Main war in den Kernpfaden bereits deutlich konsistenter als vor
Phase O, hatte aber mehrere Realitaetsbrueche in den Einstiegspfaden fuer neue
Entwickler. Die groessten Probleme lagen nicht im Core, sondern in veralteter
Dokumentation, toten CI-Referenzen und einem inzwischen obsoleten
Bootstrap-Skript.

## Bewertung nach Kategorie

### A — korrekt

| Bereich | Bewertung | Nachweis |
|---|---|---|
| Kanonische Testbasis | korrekt | `tests/state`, `tests/mcp`, `tests/approval`, `tests/orchestration`, `tests/execution`, `tests/decision`, `tests/adapters`, `tests/core`, `tests/services` existieren und liefen gruen |
| UI-Pfad | korrekt | `frontend/agent-ui/` existiert, `npm ci`, `npm run type-check`, `npm run build`, `npm run lint` liefen |
| MCP-v2-Codepfad | korrekt | `interfaces/mcp/server.py`, `interfaces/mcp/tool_registry.py`, `scripts/abrain_mcp.py` existieren |
| Bash-CLI | korrekt | `scripts/abrain` ist kanonisch, `scripts/agentnn` ist nur Wrapper |

### B — leicht veraltet, klein korrigierbar

| Bereich | Befund | Status |
|---|---|---|
| `docs/architecture/CANONICAL_REPO_STRUCTURE.md` | REST-Routen und aktive Skripte waren teilweise nicht mehr deckungsgleich mit `api_gateway/main.py` und `scripts/` | korrigiert |
| `docs/guides/MCP_USAGE.md` | v2-Guide bevorzugte den Console-Entry, obwohl der Repo-Checkout-Pfad `python -m interfaces.mcp.server` direkter und hier verifizierbar ist | korrigiert |
| `docs/mcp/README.md` | beschrieb MCP v1 als deaktiviert statt entfernt und verlinkte auf nicht vorhandene V1-Architekturdatei | korrigiert |
| `.github/workflows/core-ci.yml` | `py_compile` referenzierte zwei geloeschte Dateien | korrigiert |

### C — fachlich falsch / irrefuehrend / blockierend

| Bereich | Befund | Status |
|---|---|---|
| `README.md` | Quickstart und CLI-Beispiele waren nicht mehr repo-real: `agentnn ask`, Docker-Quickstart ohne `docker-compose.yml`, MCP nur als `abrain-mcp` beschrieben | korrigiert |
| `CONTRIBUTING.md` | verwies auf nicht vorhandene Skripte und fehlende Dokumente (`./scripts/install.sh`, `docs/development/contributing.md`, `docs/architecture/PROJECT_OVERVIEW.md`) | korrigiert |
| `scripts/README.md` | beschrieb nur geloeschte Shell- und Modell-Setup-Skripte | korrigiert |
| `docs/architecture/PROJECT_OVERVIEW.md` | Datei fehlt komplett | offen |
| `docs/frontend_bridge.md` | Datei fehlt komplett | offen |
| `scripts/setup.sh` | erwartet 15 Hilfsdateien unter `scripts/lib` und `scripts/helpers`, die im aktuellen Repo fehlen | offen, separat eingeordnet |

## Verifizierte Inkonsistenzen

### README / Einstieg

- `README.md` zeigte `agentnn ask "Check system health"`, obwohl `scripts/abrain`
  kein `ask`-Kommando besitzt.
- `README.md` warb mit `docker compose up --build`, obwohl im Repo aktuell weder
  `docker-compose.yml` noch `docker-compose.yaml` existieren.
- `README.md` nannte `abrain-mcp` direkt, obwohl dieser Console-Entry in einem
  frischen Checkout erst nach Paketinstallation entsteht.

### Setup / Onboarding

- `CONTRIBUTING.md` verwies auf `./scripts/install.sh --ci`, die Datei existiert
  nicht.
- `CONTRIBUTING.md` verwies auf `docs/development/contributing.md` und
  `docs/architecture/PROJECT_OVERVIEW.md`; beide Dateien fehlen.
- `scripts/README.md` beschrieb mehrere nicht mehr vorhandene Skripte wie
  `install_dependencies.sh`, `install_dev_env.sh`, `repair_env.sh`,
  `check_integrity.sh` und `setup_local_models.py`.

### MCP / Runtime-Doku

- `docs/guides/MCP_USAGE.md`, `docs/mcp/README.md` und
  `docs/architecture/MCP_V2_INTERFACE.md` behaupteten teilweise noch, dass
  `interfaces/mcp_v1/*` im Repo vorhanden sei.
- `docs/mcp/README.md` verlinkte auf `docs/mcp/MCP_V1_SERVER.md`, die Datei
  nicht existiert.

### CI / Automation

- `.github/workflows/core-ci.yml` referenzierte in `py_compile` noch
  `core/governance/legacy_contracts.py` und `interfaces/mcp_v1/server.py`; beide
  Pfade existieren auf dem bereinigten Main nicht mehr.

## Dev-Onboarding-Einschaetzung

Nach den Korrekturen ist der Einstieg fuer einen neuen Entwickler deutlich
realistischer:

1. Python-Umgebung via `.venv` und `requirements-light.txt`
2. Tests ueber die kanonische Pytest-Suite
3. MCP-v2 direkt ueber `python -m interfaces.mcp.server`
4. Frontend ueber `frontend/agent-ui`
5. CLI ueber `scripts/abrain`

Offen bleibt, dass `scripts/setup.sh` kein verlaesslicher Einstieg mehr ist und
die fehlenden Uebersichtsdokumente `PROJECT_OVERVIEW.md` und
`docs/frontend_bridge.md` bisher nicht ersetzt wurden.
