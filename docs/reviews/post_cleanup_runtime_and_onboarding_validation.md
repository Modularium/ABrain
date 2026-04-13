# Post-Cleanup Runtime And Onboarding Validation

**Datum:** 2026-04-12
**Branch waehrend der Validierung:** `codex/phaseO-canonicalization-cleanup`
**Referenzstand:** aktueller gepushter Main-Stand

## 1. README-/Setup-/Onboarding-Bewertung

- `README.md`: nach Korrektur weitgehend konsistent mit dem realen Main
- `CONTRIBUTING.md`: nach Korrektur wieder nutzbar
- `scripts/README.md`: nach Korrektur wieder passend zum realen `scripts/`
- Fehlend bleiben `docs/architecture/PROJECT_OVERVIEW.md` und
  `docs/frontend_bridge.md`

Gesamtbewertung: **brauchbar mit kleinen Restluecken**, nicht mehr irrefuehrend
in den kanonischen Einstiegspfaden.

## 2. Gefundene Inkonsistenzen

### Dokumentation / Onboarding

- README bewarb nicht existente Docker- und CLI-Pfade.
- CONTRIBUTING zeigte auf geloeschte Dokumente und Skripte.
- `scripts/README.md` beschrieb nur geloeschte Alt-Skripte.
- MCP-Doku behauptete an mehreren Stellen noch, `interfaces/mcp_v1/*` sei Teil
  des aktuellen Repos.

### Runtime / Startpfade

- `api_gateway.main` importiert in der vorhandenen `.venv` nicht, weil mehrere
  deklarierte Runtime-Abhaengigkeiten fehlen, zuerst reproduzierbar `slowapi`.
- Der aktuell vorhandene `.venv/bin/abrain-mcp` zeigt noch auf
  `interfaces.mcp_v1.server` und ist damit ein **staler lokaler Entry** aus
  einer aelteren Installation, nicht der aktuelle Repo-Code.
- `scripts/setup.sh` verlangt 15 Helper-Dateien unter `scripts/lib` und
  `scripts/helpers`; keine davon ist im aktuellen Repo vorhanden.

### CI

- `core-ci.yml` kompilierte zwei geloeschte Dateien und war damit nicht mehr
  repo-real.

## 3. Gemachte kleine Korrekturen

- README-Quickstart, MCP-Start, UI-Build und CLI-Beispiele auf reale Pfade
  umgestellt
- CONTRIBUTING auf reale Setup- und Testpfade korrigiert
- `scripts/README.md` auf die heute vorhandenen Skripte reduziert
- MCP-Doku klar zwischen aktivem v2-Pfad und archivierter v1-Dokumentation
  getrennt
- `docs/architecture/CANONICAL_REPO_STRUCTURE.md` an reale API-Routen und
  aktive Skripte angepasst
- `.github/workflows/core-ci.yml` von zwei toten `py_compile`-Pfaden bereinigt

## 4. Ergebnis des `setup.sh`-Checks

**Einordnung: C — Legacy/obsolet und perspektivisch stillzulegen oder zu entfernen**

Begruendung:

- `scripts/setup.sh` ist nicht mehr selbstaendig benutzbar.
- Das Skript erwartet 15 Hilfsdateien, die im aktuellen Repo fehlen:
  `scripts/lib/log_utils.sh`, `scripts/lib/spinner_utils.sh`,
  `scripts/helpers/common.sh`, `scripts/helpers/env.sh`,
  `scripts/helpers/docker.sh`, `scripts/helpers/frontend.sh`,
  `scripts/lib/env_check.sh`, `scripts/lib/docker_utils.sh`,
  `scripts/lib/frontend_build.sh`, `scripts/lib/install_utils.sh`,
  `scripts/lib/menu_utils.sh`, `scripts/lib/args_parser.sh`,
  `scripts/lib/config_utils.sh`, `scripts/lib/preset_utils.sh`,
  `scripts/lib/status_utils.sh`
- Es gibt aktuell keinen Beleg dafuer, dass diese Hilfsstruktur noch Teil des
  kanonischen Main sein soll.

Positiv:

- Das Skript bricht jetzt kontrolliert mit einer verstaendlichen Fehlermeldung
  ab und laeuft nicht mehr in rohe `source`-Fehler.

## 5. Ergebnis der CI-/Build-/Startpfad-Pruefung

### Gruen verifiziert

- `.venv/bin/python -V`
- kanonische Pytest-Suite:
  `161 passed, 1 skipped`
- `python -m py_compile api_gateway/main.py interfaces/mcp/server.py services/core.py scripts/abrain_mcp.py`
- `python -m interfaces.mcp.server` mit `initialize` und `tools/list`
- `scripts/abrain --version`
- `scripts/abrain help`
- `scripts/abrain --version`
- `frontend/agent-ui: npm ci`
- `frontend/agent-ui: npm run type-check`
- `frontend/agent-ui: npm run build`
- `frontend/agent-ui: npm run lint`
- `core-ci.yml` nach Korrektur: keine toten Dateipfade mehr im `py_compile`-Block

### Rot / nicht voll verifizierbar

- `from api_gateway.main import app` scheitert in der vorhandenen `.venv` mit
  `ModuleNotFoundError: No module named 'slowapi'`
- `pip install -e . --no-deps` war in dieser Offline-Sandbox nicht voll
  verifizierbar, weil `pip` fuer `poetry-core>=1.7.0` ins Netz wollte
- der vorhandene `.venv/bin/abrain-mcp` ist lokal stale und zeigt noch auf
  `interfaces.mcp_v1.server`; das ist ein Umgebungs-/Installationszustand, nicht
  der aktuelle Repo-Code

## 6. Ist der bereinigte Main jetzt real benutzbar und onboarding-faehig?

**Ja, eingeschraenkt benutzbar.**

Was heute real funktioniert:

- Core-Runtime und kanonische Testbasis
- MCP-v2 direkt aus dem Repo-Checkout
- Frontend-Build, Typecheck und Lint
- Bash-CLI fuer Diagnose und lokale Einstiege

Was noch nicht als turnkey-Onboarding taugt:

- `scripts/setup.sh`
- ein frischer, sicher verifizierter `abrain-mcp`-Console-Entry in dieser
  Offline-Umgebung
- API-Gateway-Import ohne vorher vollstaendige Dependency-Installation

## 7. Kleine Restschulden

- Fehlende Uebersichtsdokumente `docs/architecture/PROJECT_OVERVIEW.md` und
  `docs/frontend_bridge.md`
- `scripts/setup.sh` ist im Repo nur noch historisch mitgefuehrt
- lokaler `abrain-mcp`-Console-Entry kann nach alten Installationen stale sein
- `api_gateway.main` ist dokumentiert, aber in einer unvollstaendigen `.venv`
  nicht direkt importierbar

## 8. Empfehlung

**Naechste Produktphase kann sinnvoll gestartet werden, aber ein kleiner
Follow-up ist empfehlenswert.**

Empfohlener kurzer Follow-up:

1. `scripts/setup.sh` formell stilllegen oder aus der kanonischen Bedienfuehrung
   herausnehmen
2. ein kleines, ehrliches `PROJECT_OVERVIEW.md` als zentrale Einstiegsdatei
   nachziehen
3. dokumentieren, wie `abrain-mcp` nach einem frischen Package-Install sicher
   regeneriert wird

## Durchgefuehrte Verifikation

```bash
.venv/bin/python -V
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/state tests/mcp tests/approval tests/orchestration \
  tests/execution tests/decision tests/adapters tests/core \
  tests/services tests/integration/test_node_export.py
.venv/bin/python -m py_compile api_gateway/main.py interfaces/mcp/server.py services/core.py scripts/abrain_mcp.py
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"codex"}}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' | .venv/bin/python -m interfaces.mcp.server
./scripts/abrain --version
./scripts/abrain help
./scripts/abrain --version
./scripts/abrain setup
./scripts/setup.sh --help
cd frontend/agent-ui && npm ci
cd frontend/agent-ui && npm run type-check
cd frontend/agent-ui && npm run build
cd frontend/agent-ui && npm run lint
```
