# Red-Team Review: ABrain Core / AdminBot

Datum: 2026-04-07

## Scope

Gezielt geprueft wurden:

- `services/core.py`
- `core/execution/dispatcher.py`
- `core/tools/*`
- `core/models/*`
- `adapters/adminbot/*`
- angrenzende Nebenpfade unter `agentnn/mcp/*` und `mcp/plugin_agent_service/*`
- zentrale Integrations- und Sicherheitsdoku

## Attack Surface Mapping

### Canonical path

- `services/core.py:38`
- `core/execution/dispatcher.py:36`
- `core/tools/handlers.py:81`
- `core/tools/handlers.py:105`
- `adapters/adminbot/service.py:31`
- `adapters/adminbot/client.py:99`

Eigenschaft:
Fester Tool-Einstieg mit typisierten Inputs, fester Registry, hartem Unknown-Tool-Reject und exakt verdrahtetem AdminBot-Mapping.

### Legacy (disabled) path

- `agentnn/mcp/mcp_server.py:97`
- `agentnn/mcp/mcp_gateway.py:28`
- `mcp/plugin_agent_service/api.py:16`
- `mcp/plugin_agent_service/service.py:24`

Eigenschaft:
Historischer generischer Tool-/Plugin-Pfad ausserhalb des `canonical path`, jetzt `legacy (disabled)`.

### Externally reachable path

- `agentnn/mcp/mcp_server.py:97`
- `agentnn/mcp/mcp_gateway.py:28`
- `mcp/plugin_agent_service/api.py:16`

Eigenschaft:
HTTP-Routen, die vor dem Fix als generische Tool-Proxies oder Plugin-Execution-Flächen missbrauchbar gewesen waeren.

### Locally callable path

- `services/core.py:38`
- `mcp/plugin_agent_service/service.py:24`

Eigenschaft:
Direkte Python-Callsites. Der kanonische Pfad bleibt erlaubt; der Legacy-Pfad wurde deaktiviert.

## Findings

### HIGH — Legacy generic tool proxy bypassed the hardened core

- Kategorie: Dispatcher / Registry Bypass, Legacy Path Abuse, Trust Boundary Drift
- Betroffener Pfad:
  - `agentnn/mcp/mcp_server.py:97`
  - `agentnn/mcp/mcp_gateway.py:28`
  - `mcp/plugin_agent_service/api.py:16`
  - `mcp/plugin_agent_service/service.py:24`
- Reproduktion / Prüfweg:
  1. `agentnn/mcp/mcp_server.py` nahm beliebige Nutzlasten auf `/v1/mcp/tool/use` an.
  2. Der Pfad leitete an `plugin_agent_service:/execute_tool` weiter.
  3. `mcp/plugin_agent_service/service.py` fuehrte dynamisch geladene Plugins fuer beliebige `tool_name`- und Input-Werte aus.
  4. Die Doku bewarb diesen Pfad zusaetzlich mit Beispielen fuer `filesystem`-Nutzung.
- Sicherheitsauswirkung:
  Der feste Dispatcher-/Registry-Pfad konnte umgangen werden. Damit existierte parallel zur gehärteten Tool-Oberfläche wieder ein generischer Tool-Proxy mit freier Payload.
- Minimalfix:
  - `agentnn/mcp/mcp_server.py:97` liefert jetzt `410 Gone`
  - `agentnn/mcp/mcp_gateway.py:28` liefert jetzt ebenfalls `410 Gone`
  - `mcp/plugin_agent_service/api.py:16` liefert `410 Gone`
  - `mcp/plugin_agent_service/service.py:24` fuehrt keine Plugins mehr aus und gibt nur noch einen strukturierten Disable-Fehler zurueck
- Status:
  Sofort gefixt

### LOW — Historical / legacy (not active runtime path) OpenAPI artifact still described the removed route

- Kategorie: Docs-vs-Implementation Security Mismatch
- Betroffener Pfad:
  - `docs/api/openapi/plugin_agent_service.json`
  - `docs/api/_openapi_index.md:11`
- Reproduktion / Prüfweg:
  Die statische OpenAPI-Datei beschreibt weiterhin `/execute_tool`, obwohl der Runtime-Pfad jetzt deaktiviert ist.
- Sicherheitsauswirkung:
  Kein direkter Runtime-Impact, aber moegliche Fehlsteuerung fuer Integratoren, die nur das generierte JSON lesen.
- Minimalfix:
  Der zentrale Index wurde als `historical / legacy (not active runtime path)` markiert (`docs/api/_openapi_index.md:11`).
- Status:
  Follow-up sinnvoll, aber nicht blocker

## No Finding / Not Confirmed

### Action injection into AdminBot

Nicht bestaetigt.

- `core/models/adminbot.py:18`
- `core/models/adminbot.py:34`
- `adapters/adminbot/service.py:31`
- `adapters/adminbot/service.py:57`
- `tests/adapters/test_adminbot_tools.py:145`

Begruendung:
Keine freie `action`-Uebergabe aus Tool-Payloads. Extra-Felder werden verworfen, und die drei AdminBot-Aktionen sind exakt fest verdrahtet.

### Input contract bypass

Nicht bestaetigt.

- `core/models/tooling.py:52`
- `core/models/adminbot.py:21`
- `core/models/adminbot.py:37`
- `core/models/adminbot.py:42`
- `core/execution/dispatcher.py:51`

Begruendung:
`extra="forbid"` ist auf Request- und AdminBot-Input-Modellen gesetzt. Problematische `service_name`-Zeichen werden abgewiesen.

### Identity spoofing against AdminBot

Nicht bestaetigt.

- `adapters/adminbot/service.py:81`
- `adapters/adminbot/service.py:84`
- `adapters/adminbot/service.py:89`
- `core/models/adminbot.py:57`
- `tests/adapters/test_adminbot_tools.py:59`

Begruendung:
`requested_by` wird fuer AdminBot immer neu als `type="agent"` plus feste Adapter-ID gebaut. Aus dem Tool-Request werden nur `run_id` und `correlation_id` uebernommen.

### Error semantics corruption on the canonical AdminBot path

Nicht bestaetigt.

- `adapters/adminbot/client.py:154`
- `adapters/adminbot/client.py:158`
- `adapters/adminbot/client.py:160`
- `adapters/adminbot/client.py:161`
- `adapters/adminbot/client.py:162`
- `core/execution/dispatcher.py:67`
- `tests/adapters/test_adminbot_client.py:37`

Begruendung:
Strukturierte AdminBot-Fehler behalten `error_code`, `message`, `details`, `audit_ref` und `warnings`. Nur Transport- und Protokollfehler werden lokal auf Adapter-Fehlercodes gemappt.

### Dispatcher / registry bypass on the canonical path

Nicht bestaetigt.

- `services/core.py:38`
- `core/execution/dispatcher.py:38`
- `core/execution/dispatcher.py:51`
- `core/tools/handlers.py:105`

Begruendung:
Der gehärtete Core nutzt nur die feste Registry. Unbekannte Tools werden hart abgelehnt, es gibt keine Default-Route.

## Tests and Repros

Ausgefuehrt:

```bash
.venv/bin/python -m pytest -o python_files='test_*.py' \
  tests/adapters \
  tests/core \
  tests/services \
  tests/integration/test_node_export.py \
  tests/integration/test_mcp_server.py \
  tests/integration/test_mcp_gateway.py \
  tests/test_plugin_agent_service.py
```

Ergebnis:

- `30 passed`
- `4 skipped`

Zusaetzlich:

```bash
.venv/bin/python -m py_compile \
  services/core.py \
  core/execution/dispatcher.py \
  core/tools/__init__.py \
  core/tools/registry.py \
  core/tools/handlers.py \
  core/models/tooling.py \
  core/models/identity.py \
  core/models/errors.py \
  core/models/adminbot.py \
  adapters/adminbot/client.py \
  adapters/adminbot/service.py \
  mcp/plugin_agent_service/service.py \
  mcp/plugin_agent_service/api.py \
  agentnn/mcp/mcp_server.py \
  agentnn/mcp/mcp_gateway.py
```

Ergebnis:

- erfolgreich

## Final Assessment

- CRITICAL: 0
- HIGH: 1
- MEDIUM: 0
- LOW: 1

Urteil:

Der gehärtete Core und der AdminBot-Adapter sind im aktuellen Sicherheitsmodell konsistent. Der einzige bestaetigte ernste Befund war ein paralleler generischer Tool-Pfad ausserhalb des `canonical path`. Dieser ist jetzt explizit als `legacy (disabled)` behandelt. AdminBot bleibt weiterhin die Sicherheitsgrenze; ABrain trifft auf dem kanonischen Adapter-Pfad keine eigenen Policy-Entscheidungen.
