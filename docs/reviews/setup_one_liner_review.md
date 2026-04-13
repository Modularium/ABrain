# Setup One-Liner Review

Datum: 2026-04-12
Branch: `codex/setup-one-liner-bootstrap`

## 1. Vorheriger Zustand

Vor dieser Runde war der technische Bootstrap bereits modernisiert, aber noch
nicht konsequent als echter One-Liner praesentiert:

- `./scripts/abrain setup` funktionierte faktisch bereits als Voll-Setup
- die kanonische Dokumentation zeigte aber noch an mehreren Stellen `./scripts/abrain setup all`
- die Abschlussausgabe war brauchbar, aber nicht explizit auf einen klaren
  Ready-State fuer CLI, MCP, API und UI ausgerichtet
- die Bash-CLI selbst wurde im Setup nicht ausdruecklich als bereit verifiziert
- der MCP-Console-Entry wurde erzeugt, aber im Setup nicht explizit gegen den
  v2-Entry-Point abgesichert

## 2. Neuer One-Liner Flow

Der kanonische Einstieg ist jetzt:

```bash
./scripts/abrain setup
```

Der direkte Skriptpfad bleibt technisch gleichwertig:

```bash
bash scripts/setup.sh
```

Beide Pfade fuehren in denselben linearen Bootstrap:

1. Systemgrundlage pruefen
2. `.venv` anlegen oder wiederverwenden
3. `pip`, `setuptools`, `wheel` aktualisieren
4. Python-Dependencies installieren
5. editable Install und `abrain-mcp` erneuern
6. CLI-Smoke
7. API-Gateway-Import-Smoke
8. MCP-v2-`initialize`/`tools/list`-Smoke plus Entry-Point-Pruefung
9. Frontend `npm ci`, `type-check`, `build`
10. klare Ready-State-Ausgabe

## 3. Was jetzt funktioniert

### Kanonischer One-Liner

- `./scripts/abrain setup` lief nach `rm -rf .venv` grün durch
- dabei wurden `.venv`, Python-Dependencies, editable Install, `abrain-mcp`,
  API-Smoke, MCP-Smoke und UI-Build in einem Lauf erfolgreich abgearbeitet

### Direkter Skriptpfad

- `bash scripts/setup.sh help` wurde erfolgreich geprueft
- `bash scripts/setup.sh mcp` lief grün und bestaetigte den direkten Einstieg

### Erfolgsausgabe

Der One-Liner endet jetzt mit einem klaren Ready-State:

- `[OK] CLI bereit`
- `[OK] MCP bereit`
- `[OK] API bereit`
- `[OK] UI gebaut`

und den dazugehoerigen Startpfaden.

## 4. Reale Verifikation

Ausgefuehrt wurden mindestens:

- `rm -rf .venv`
- `./scripts/abrain setup`
- `bash -n scripts/setup.sh scripts/abrain scripts/abrain`
- `shellcheck scripts/setup.sh scripts/abrain scripts/abrain`
- `./scripts/abrain help setup`
- `./scripts/abrain --version`
- `./scripts/abrain --version`
- `bash scripts/setup.sh help`
- `bash scripts/setup.sh mcp`
- `.venv/bin/python -m py_compile core/config.py api_gateway/main.py interfaces/mcp/server.py scripts/abrain_mcp.py`
- `.venv/bin/python -m pytest -o python_files='test_*.py' tests/state tests/mcp tests/approval tests/orchestration tests/execution tests/decision tests/adapters tests/core tests/services tests/integration/test_node_export.py`
- `cd frontend/agent-ui && npm run type-check`
- `cd frontend/agent-ui && npm run build`
- `cd frontend/agent-ui && npm run lint`

Ergebnis:

- One-Liner-Setup grün
- `py_compile` grün
- MCP-Smoke grün
- CLI-Smokes grün
- Frontend-Build grün
- Pytest: `161 passed, 1 skipped`

## 5. Bekannte Grenzen

- `npm ci` meldet weiterhin bestehende Upstream-`npm audit`-Vulnerabilities und
  eine Browserslist-Aktualisierungsempfehlung; diese verhindern den Build nicht
  und wurden in dieser Runde nicht separat bearbeitet.
- Die lokale `.env` wird nur erzeugt, wenn sie fehlt; vorhandene lokale
  Entwicklerkonfiguration wird bewusst nicht ueberschrieben.

## 6. Explizite Bestaetigung

- keine Parallel-Implementierung gebaut
- keine zweite Runtime eingefuehrt
- keine alten `scripts/lib`- oder `scripts/helpers`-Strukturen wiederbelebt
- kein Legacy-ABrain-Setup rekonstruiert
- der Setup-Pfad entspricht dem aktuellen kanonischen ABrain-Repo deutlich besser
