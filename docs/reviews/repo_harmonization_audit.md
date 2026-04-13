# Repo Harmonization Audit

## Scope

Dieses Audit prüft den aktuellen Branch auf Benennungsinkonsistenzen, Parallelpfade, Docs-vs-Code-Widersprüche und historisch irreführende Reste. Führender Referenzpfad bleibt der gehärtete Core mit Dispatcher, Registry, typisierten Tool-Inputs und dem sicheren AdminBot-Adapter.

## Naming & Slugs

| Pfad / Bereich | Problemtyp | Einstufung | Maßnahme | Risiko / Begründung |
|---|---|---:|---|---|
| `README.md`, `docs/*`, sichtbare API-/UI-Texte | fachliche Altbenennung | B | repo-weit auf `ABrain` harmonisiert | geringe Gefahr, nur sichtbare Texte |
| `server/main.py`, `legacy runtime/mcp/mcp_server.py`, `monitoring/monitoring/api/server.py` | sichtbare API-Titel | B | auf `ABrain` umgestellt | sicher, keine Importänderung |
| `frontend/agent-ui/*`, `monitoring/*` sichtbare Labels | UI-/Monitoring-Branding | B | auf `ABrain` umgestellt | sicher, keine Strukturänderung |
| `legacy runtime`, `agent_nn`, `abrain` in Paket-, CLI-, Deploy- oder Publish-Slugs | technisch/sluggebunden | F | bewusst belassen | Import-, Packaging- und Deploy-Risiko zu hoch für diesen Schritt |
| GitHub-Repo-URLs `EcoSphereNetwork/ABrain` | extern gebunden | F | bewusst belassen | Repo-/Pages-/Badge-Rename liegt außerhalb des Repos |
| `abrain-adminbot-adapter` | sicherheitsrelevante technische Identität | D | bewusst belassen | stabiler Adapter-Identifier, kein Branding-Problem im Sicherheitskontext |

## Redundanzen / Parallelpfade

| Pfad / Bereich | Problemtyp | Einstufung | Maßnahme | Risiko / Begründung |
|---|---|---:|---|---|
| `services/core.py` vs. ältere direkte oder breite Servicepfade | Referenzpfad unklar | A | Canonical-Pfad in README und Architektur-Doku klar gezogen | reduziert Verwechslungsgefahr ohne Code-Rewrite |
| `mcp/plugin_agent_service/service.py` | dynamische Plugin-Ausführung parallel zum gehärteten Tool-Pfad | C | als Legacy-Pfad markiert, nicht als Referenz | neuer hardened path bleibt unangetastet |
| mehrere Setup-Dokumente (`README.md`, `docs/setup.md`, `docs/setup/DEVELOPMENT_SETUP.md`, `FULLSTACK_README.md`) | parallele Einstiege | C | Canonical-Doku festgelegt, Altpfade als allgemein/operativ markiert | verhindert konkurrierende Wahrheiten |
| mehrere Roadmap-/Planungsdateien (`ROADMAP.md`, `Roadmap.md`, `TODO-*.md`) | historische Planungen wirken aktuell | D | als historische Planung markiert | erhält Referenzwert, ohne aktuellen Status zu überdecken |
| `docs/BenutzerHandbuch/*` vs. heutiger Hardened-Core-Stand | produktartige Alt-Doku | D | als historisch/UX-orientiert markiert | verhindert Gleichrangigkeit mit aktueller Integrationsdoku |

## Docs-vs-Code

| Pfad / Bereich | Problemtyp | Einstufung | Maßnahme | Risiko / Begründung |
|---|---|---:|---|---|
| `README.md` | nebulöser Modernisierungsstatus | A | auf klaren Canonical-Pfad umformuliert | weniger Interpretationsspielraum |
| `docs/api/api_reference.md` | zu absolut für heterogenen API-Bestand | A | als high-level / teilweise historisch gekennzeichnet | reduziert falsche Vertragsannahmen |
| `docs/development/plugins.md` | suggeriert dynamische Plugins als Standardpfad | A | als historisch/geplant markiert und gegen hardened path abgegrenzt | wichtig für Sicherheitskonsistenz |
| `FULLSTACK_README.md`, `test_system.sh`, `status_check.sh` | alte Demo-Mail und Altbranding | A | auf `ABrain`/`demo@abrain.local` korrigiert | beseitigt direkte Bedienungsfehler |
| `RELEASE_NOTES_v1.0.0.md`, `prepare_github_release.sh` | historische Release-Artefakte wirken aktuell | D | als historisch/legacy markiert | vermeidet falsche Release-Annahmen |

## Tote / veraltete Inhalte

| Pfad / Bereich | Problemtyp | Einstufung | Maßnahme | Risiko / Begründung |
|---|---|---:|---|---|
| `docs/ui_migration_audit.md`, `docs/migration_status.md` | veraltete Audit-/Migrationsschnappschüsse | D | explizit als historisch markiert | sinnvoll als Referenz, nicht als Primärdoku |
| `docs/BenutzerHandbuch/*.svg` und langes Handbuch | Altbestand mit alter Produktstory | D | bewusst belassen, über Index/Handbuch als historisch eingerahmt | Massenumbenennung der Assets wäre teuer und nicht sicherheitsrelevant |
| `deploy/k8s/helm/abrain`, Compose-/Helm-/Image-Slugs | technische Deploy-Reste | F | bewusst offener Follow-up | breiter Deploy-/Release-Impact |
| `package.json`, `pyproject.toml`, Integrations-Paketnamen mit `legacy runtime*` | technische Packaging-Slugs | F | bewusst offener Follow-up | Paket-/Import-/Publish-Risiko |

## Sicherheitsrelevante Guardrails

- Führender Integrationspfad bleibt:
  - `services/core.py`
  - `core/execution/dispatcher.py`
  - `core/tools/*`
  - `core/models/*`
  - `adapters/adminbot/*`
  - `docs/integrations/adminbot/*`
- Keine Erweiterung der AdminBot-Tool-Fläche
- Kein `restart_service`, kein generischer Action-Proxy
- Dynamische Plugin- oder Legacy-Pfade werden nicht als gleichwertiger sicherer Pfad dargestellt
- Keine Rückkehr zu direkten Legacy-Aufrufen statt Dispatcher/Registry

## Direkt in diesem Schritt geändert

- sichtbare Benennung auf `ABrain` harmonisiert
- Canonical-Doku klar gezogen
- historische Doku- und Planungsbestände markiert
- operative Root-Helfer und Demo-Zugangsdaten an aktuellen Stand angepasst
- Legacy-Plugin-Pfad als nicht-canonical gekennzeichnet

## Bewusst offen gelassene Follow-ups

- vollständiger Paket-/Importpfad-Rename `legacy runtime` / `agent_nn`
- Deploy-/Helm-/Compose-/GHCR-Slug-Rename `abrain`
- GitHub-Repo-Umbenennung und externe URL-/Badge-Anpassung
- breite inhaltliche Modernisierung aller historischen Langform-Handbücher und SVG-Assets
