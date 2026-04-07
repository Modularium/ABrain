# Legacy Repo Consolidation Report

## Ziel

Kontrollierte Konsolidierung des ausgelagerten Alt-Repos
`/home/dev/Agent-NN_backup_pre_refactor_20260407` in den gehärteten Arbeitsstand
`/home/dev/Agent-NN` auf `codex/core-refactor-stabilization`, ohne Sicherheits- oder Architektur-Rückschritt. Der Projektname wird inzwischen als `ABrain` geführt; die Dateisystempfade bleiben historisch unverändert.

## Ausgangszustand

- Führender Zielstand: `/home/dev/Agent-NN`
- Arbeitsbranch: `codex/core-refactor-stabilization`
- Backup-Quelle: `/home/dev/Agent-NN_backup_pre_refactor_20260407`
- `main` und `origin/main` blieben sauber; der Refactor liegt lokal im Arbeitsbaum des Feature-Branches.

Der Backup-Ordner ist ein Git-Repo, aber kein alternativer Commit-Strang:

- aktuelles Repo: `codex/core-refactor-stabilization` auf `3c9d22a8`
- Backup-Repo: `backup/pre-refactor-20260407` auf `3c9d22a8`
- Backup-Arbeitsbaum: keine verfolgten lokalen Änderungen, nur ungetracktes `.codex`

## Forensische Inventur

### Nur im Backup vorhanden

Es wurden keine zusätzlichen sauberen Source-Verzeichnisse mit klarer Merge-Relevanz gefunden.
Die Backup-only-Inhalte sind fast ausschließlich Laufzeit-, Umgebungs- oder lokale Operator-Artefakte:

- `.env`
- `mcp/.env`
- `frontend/agent-ui/.env.local`
- `backend.log`
- `frontend.log`
- `test_backend.log`
- `logs/`
- `data/context.db`
- `embeddings_cache/`
- `export/`
- `models/` (leer)
- `config/environments/` (nur `__pycache__`)

### Nur im aktuellen Repo vorhanden

Die aktuellen Mehrinhalte sind die absichtliche Härtung und Reviewbarkeit:

- `adapters/adminbot/*`
- `core/agents/*`
- `core/execution/*`
- `core/models/*`
- `core/tools/*`
- `docs/architecture/CORE_REFACTOR.md`
- `docs/integrations/adminbot/*`
- `docs/reviews/*`
- `tests/adapters/*`
- `tests/core/*`
- `.github/workflows/adminbot-security-gates.yml`

### In beiden vorhanden, aber inhaltlich abweichend

Die relevanten Abweichungen sind allesamt Teil des neuen gehärteten Stands:

- `api/endpoints.py`
- `server/main.py`
- `services/core.py`
- `services/__init__.py`
- `sdk/cli/commands/agent.py`
- `core/__init__.py`
- `tests/services/test_core.py`
- `.gitignore`
- `codex_progress.log`

## Klassifikation relevanter Funde

| Backup-Pfad | Status | Zielpfad | Kurzbegründung | Risiko-Hinweis |
|---|---|---|---|---|
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/.env` | D | - | Lokale Umgebungsdatei, nicht reviewbar und potenziell sensitiv. | Re-Import würde Secrets und lokale Defaults unkontrolliert zurückholen. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/mcp/.env` | D | - | Lokale Umgebungsdatei für Teilkomponente. | Sensitiver Laufzeitkontext, nicht ins Repo übernehmen. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/frontend/agent-ui/.env.local` | D | - | Lokale Frontend-Umgebungsdatei. | Lokale Endpunkte/Secrets, kein versionswürdiges Artefakt. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/backend.log` | D | - | Laufzeitlog. | Kein Source-Artefakt, potenziell sensitive Inhalte. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/frontend.log` | D | - | Laufzeitlog. | Kein Source-Artefakt. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/test_backend.log` | D | - | Laufzeitlog. | Kein Source-Artefakt. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/logs/` | D | - | Aggregierte Laufzeitlogs. | Kein Merge-Wert, potenziell sensitive Verlaufsdaten. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/data/context.db` | D | - | Lokale Laufzeitdatenbank. | Würde alten Zustand und potenziell inkonsistente Daten zurückholen. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/embeddings_cache/` | D | - | Lokaler Cache ohne versionierbaren Quellwert. | Nicht reproduzierbar, potenziell veraltet. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/export/` | D | - | Verzeichnis ist leer. | Kein Übernahmewert. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/models/` | D | - | Verzeichnis ist leer. | Kein Übernahmewert. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/config/environments/` | D | - | Enthält nur `__pycache__`, keine Quellkonfiguration. | Kein mergebarer Source-Inhalt. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/api/endpoints.py` | D | - | Der aktuelle Stand repariert Sync/Async-Grenzen, UUID/WebSocket-Importe und Runtime-Einstieg. | Backup-Version würde bekannte Laufzeitprobleme und ältere Agent-Pfade zurückbringen. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/server/main.py` | D | - | Der aktuelle Stand nutzt `AgentRuntime` und `maybe_await`. | Backup-Version würde ältere Direktaufrufe und Async-Inkonsistenzen reimportieren. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/services/core.py` | D | - | Der aktuelle Stand ist die führende Dispatcher-/Registry-Einstiegsschicht. | Backup-Version würde direkte Client-Aufrufe statt gehärteter Tool-Ausführung reaktivieren. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/services/__init__.py` | D | - | Aktueller Stand exportiert bewusst `execute_tool` und `list_agents`. | Backup-Version würde die neue sichere Service-Oberfläche teilweise ausblenden. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/sdk/cli/commands/agent.py` | D | - | Der aktuelle Stand routet Listenpfade über die Core-Service-Schicht. | Backup-Version würde einen Legacy-Bypass für `list_agents` zurückbringen. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/core/__init__.py` | D | - | Aktueller Stand exportiert die neue gehärtete Core-Schicht. | Backup-Version würde die Refactor-Struktur unsichtbar machen. |
| `/home/dev/Agent-NN_backup_pre_refactor_20260407/tests/services/test_core.py` | C | - | Historische Testbasis, aber kein verlorenes Feature. Der aktuelle Test wurde bereits an den neuen Tool-Request angepasst. | Nur Referenzwert; kein Rückimport nötig. |

## Übernahmeentscheidung

### A) Direkt übernehmen

Keine Funde.

### B) Manuell mergen

Keine Funde.

### C) Nur dokumentieren

- `/home/dev/Agent-NN_backup_pre_refactor_20260407/tests/services/test_core.py`
  Der Backup-Stand bestätigt nur die frühere direkte Service-Semantik. Für die neue gehärtete Architektur ist er eine Referenz, aber keine Übernahmekandidatur.

### D) Bewusst verwerfen

- alle Backup-only Umgebungs-, Log-, Cache- und Laufzeitdaten
- alle Backup-Versionen der inzwischen gehärteten Einstiegspfade
- leere oder rein generierte Alt-Verzeichnisse ohne Quellwert

## Ergebnis der Konsolidierung

- Es wurden keine Source-Dateien aus dem Backup in das aktuelle Repo übernommen.
- Es wurden keine Alt-Pfade restauriert.
- Die neue Core-/Dispatcher-/Registry-/Adapter-Struktur blieb vollständig führend.
- Die Konsolidierung besteht bewusst aus Verifikation, Klassifikation und dokumentierter Nicht-Übernahme.

## Guardrail-Fazit

Nicht zurückgeholt wurden insbesondere:

- rohe Direktaufrufe statt Dispatcher
- generische Tool- oder Action-Pfade
- freie Payload-Weitergabe
- frühere Async/await-Inkonsistenzen
- Legacy-Bypasses um `services/core.py`
- direkte Einhängung externer Integrationen in alte API-Module

Damit bleibt der sichere Core intakt und das Repo ist fachlich für den nächsten separaten Schritt vorbereitet.
