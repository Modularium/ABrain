# Phase R — Domain 8: CLI / Setup / Dev Experience
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Welche Features existierten?**

~30 Shell-Skripte (root-level und `scripts/`):
- `setup.sh` — Vollständiges Setup (venv, deps, Konfiguration).
- `start_fullstack.sh` — Startet alle Services (Docker oder lokal).
- `repair_env.sh` — Repariert die Entwicklungsumgebung.
- `REPAIR.sh` (359 Zeilen) — Umfangreiches Reparatur-Skript.
- `validate.sh` — Validiert das Setup.
- `status.sh` — Zeigt Status aller Services.
- `test.sh` — Führt Tests aus.
- `deploy.sh` — Deployment-Skript.
- `install_dependencies.sh`, `install_utils.sh` — Dependency-Installation.
- `menu_utils.sh`, `preset_utils.sh` — CLI-Hilfsfunktionen.
- `build_and_start.sh`, `build_and_test.sh` — Build-Hilfsskripte.
- `build_docker.sh`, `build_frontend.sh` — Docker/Frontend-Build.
- `check_env.sh`, `check_integrity.sh` — Umgebungsprüfungen.
- `codex-init.sh` — Codex-Initialisierung.
- `start_mcp.sh`, `start_docker.sh` — Service-Start.
- `deploy_docs.sh`, `deploy_to_registry.sh` — Deployment.

`sdk/cli/` — Python-SDK-CLI:
- `main.py` — CLI-Einstiegspunkt (typer-basiert).
- `commands/` — Einzelne CLI-Befehle (agent, mcp, plugins, tasks, train, etc.).
- `schemas/` — JSON-Schemata für CLI-Eingaben.
- `templates/` — Prompt-Templates für Agenten.
- `utils/` — CLI-Hilfsfunktionen.

`tools/cli_docgen.py` (155 Zeilen) — Auto-generiert CLI-Dokumentation aus Command-Definitionen.

**Wie war die Architektur?**
- *30+ Shell-Skripte ohne einheitliche Struktur.*
- Shell-Skripte hatten Abhängigkeiten untereinander (`menu_utils.sh`, `preset_utils.sh`).
- Python-SDK-CLI (typer) parallel zu Shell-Skripten.
- Kein einheitlicher Einstiegspunkt.
- Setup war komplex: Docker oder lokale Installation, verschiedene Pfade.

**Welche Probleme gab es?**
- 30+ Shell-Skripte = Maintenance-Albtraum.
- Kein Single-Entry-Point: Welches Skript macht was?
- Python-CLI und Shell-Skripte waren nicht synchron.
- `cli_docgen.py` generierte Docs für eine CLI, die nicht mehr aktuell war.
- REPAIR.sh (359 Zeilen) deutet auf ein System hin, das oft kaputt war.
- Docker-Abhängigkeit machte lokale Entwicklung schwer.

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

`scripts/`:
- `abrain` — Canonical Bash CLI. Einheitlicher Einstiegspunkt für alle Operationen.
- `setup.sh` — One-Liner-Bootstrap: `.venv` erstellen, Deps installieren, editable install, API/MCP Smoke-Tests, UI-Build. Alles in einem Skript.
- `abrain_mcp.py` — MCP v2 stdio Einstiegspunkt.
- `__init__.py` — Makes scripts importable.

**Wie ist es strukturiert?**
- Ein einziger `abrain` CLI-Einstiegspunkt.
- Ein einziges Setup-Skript (`setup.sh`).
- Kein Docker-Requirement für lokale Entwicklung.
- `setup.sh` ist selbst-erklärend und -heilend.

**Was wurde bewusst entfernt?**
- Alle 30+ Shell-Skripte.
- Python-SDK-CLI (typer-basiert).
- `cli_docgen.py`.
- REPAIR.sh und alle Reparatur-Skripte.
- Docker-Skripte.

---

### Bewertung

**Was war früher schlechter?**
- 30+ Skripte = unüberschaubar.
- Kein Single Entry Point.
- REPAIR.sh (359 Zeilen) ist ein Zeichen dafür, dass Setup häufig fehlschlug.
- Python-CLI und Shell-Skripte inkonsistent.

**Was ist heute besser?**
- Ein Skript: `setup.sh`.
- Ein CLI: `abrain`.
- Keine Docker-Abhängigkeit.
- Setup ist reproduzierbar und self-contained.

**Wo gab es frühere Stärken?**
- `sdk/cli/` hatte *viele* CLI-Befehle: `agent list`, `agent create`, `mcp connect`, `tasks run`, `train`, `plugins install`. Das war eine *vollständige Developer-CLI* für ABrain. Heute ist `abrain` vor allem ein System-CLI (start/stop/status), keine Developer-CLI.
- `cli_docgen.py` war ein Auto-Dokumentations-Tool für CLI-Befehle. Das Konzept (automatische Doku-Generierung) ist wertvoll.
- `status.sh` zeigte den Status aller Services auf einen Blick. Heute gibt es `abrain status`, aber unklar wie reich die Ausgabe ist.
- Python-CLI (typer) war interaktiver als Bash-CLI.

---

### Gap-Analyse

**Was fehlt heute?**
- Kein Developer-CLI (`abrain agent list`, `abrain task run "..."`, `abrain trace get <id>`).
- Kein `abrain trace` / `abrain approval` / `abrain plan` als CLI-Subkommandos.
- Keine Auto-Doku-Generierung für die CLI.
- Kein `abrain status` der alle Subsysteme einzeln prüft.

**Welche Ideen sind verloren gegangen?**
- `abrain task run "..."` direkt aus dem Terminal (ohne MCP/REST).
- `abrain agent list` — welche Agenten sind registriert.
- `abrain trace list` — letzte Traces.
- `abrain approval list` — offene Approvals.

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| 30+ Shell-Skripte | A — bewusst verworfen |
| REPAIR.sh | A — bewusst verworfen (Setup-Stabilität ist Ziel) |
| Python-SDK-CLI (typer) | C — Developer-CLI-Befehle fehlen heute |
| cli_docgen.py | C — Auto-Doku-Konzept wertvoll |
| Developer CLI-Befehle (task run, agent list, trace) | D — **kritisch fehlend** für Developer-Experience |
| abrain status (rich output) | C — fehlt, wäre nützlich |
