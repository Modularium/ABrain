# ABrain Rename Plan

## Ziel

Der öffentliche Projektname wird kontrolliert von `ABrain` auf `ABrain` umgestellt, ohne den gehärteten Core oder den sicheren AdminBot-Adapter zu verändern.

## Rename-Matrix

| Alte Bezeichnung | Neue Bezeichnung | Betroffene Datei-/Pfadgruppen | Änderungstyp | Hinweise |
|---|---|---|---|---|
| `ABrain` | `ABrain` | `README.md`, zentrale `docs/`, API-/UI-Texte, Review-Dokumente | Textanpassung | Haupt-Rename für Außendarstellung |
| `abrain` in sichtbaren Projekttexten | `abrain` oder `ABrain` je nach Kontext | Badge-/Doku-Texte, UI-Titel, sichtbare Hinweise | Textanpassung | Nur dort, wo kein technischer Slug gebrochen wird |
| `ABrain API Server` | `ABrain API Server` | `server/main.py` | Textanpassung | FastAPI-Titel und sichtbare Serverbeschreibung |
| `ABrain MCP Server` | `ABrain MCP Server` | `legacy runtime/mcp/mcp_server.py` | Textanpassung | Sichtbarer API-Titel, Paketpfad bleibt |
| `ABrain Monitoring API` | `ABrain Monitoring API` | `monitoring/monitoring/api/server.py` | Textanpassung | Sichtbarer Monitoring-API-Titel |
| `ABrain UI` | `ABrain UI` | `frontend/agent-ui/index.html`, `frontend/agent-ui/README.md`, Frontend-Texte | Textanpassung | Nur sichtbare UI-Benennung |
| `ABrain` in AdminBot-Doku | `ABrain` | `docs/integrations/adminbot/*` | Textanpassung | Sicherheitsvertrag bleibt unverändert |
| `ABrain` in Review-/Architekturdoku | `ABrain` | `docs/reviews/*`, `docs/architecture/*` | Textanpassung | Historische Pfade bleiben dort erhalten, wo nötig |
| Projektüberblick / Setup nur implizit vorhanden | neue ehrliche ABrain-Doku | `docs/setup/DEVELOPMENT_SETUP.md`, `docs/architecture/PROJECT_OVERVIEW.md` | neue Doku | Ergänzt statt spekulativer Umbenennung alter Texte |
| fehlende allgemeine Kern-CI | neue kleine Kern-CI | `.github/workflows/core-ci.yml` | neue CI-Datei | ergänzt bestehende AdminBot-Security-Gates |

## Bewusst nicht in diesem Schritt umbenannt

- Python-Paketname `legacy runtime`
- Modul- und Importpfade wie `legacy runtime.*`, `agent_nn`, `nn_models.agent_nn_v2`
- Helm-Chart- und Deployment-Slugs wie `abrain`
- GHCR-Imagepfade mit `abrain`
- Docusaurus-`baseUrl`, `projectName` und `repo_url`-basierte externe Veröffentlichungs-Slugs
- bestehende Repo-/Clone-URLs `EcoSphereNetwork/ABrain`

## Begründung für bewusst offene Punkte

Diese Identifiers sind an Paketierung, Imports, Deployment-Artefakte oder externe Repo-Slugs gebunden. Eine teilweise Umbenennung innerhalb dieses Schritts würde leicht zu Import-, Publish- oder Deploy-Regressionen führen. Sie bleiben daher als eigener, expliziter Follow-up-Block dokumentiert.

## Manuelle Nacharbeiten außerhalb des Repos

- GitHub-Repo-Umbenennung `ABrain` -> `ABrain`
- Anpassung externer Badges, Releases, Pages-URLs und Repo-Slugs
- optionaler späterer Paket-/Importpfad-Rename, falls separat geplant
