# Repo Harmonization Review Summary

## Ergebnis

Der Branch wurde vor Commit/Push auf Konsistenz geprüft und bereinigt, ohne den gehärteten Core oder den AdminBot-Adapter zu verändern.

## Behobene Inkonsistenzen

- sichtbare Projektbenennung in zentralen Dokus, UI-/API-Texten und Root-Helfern auf `ABrain`
- Demo-Zugangsdaten in operativen Hilfsskripten an `demo@abrain.local` angepasst
- Canonical-Doku für Setup, Architektur und gehärteten Integrationspfad klargezogen
- historische Release-, Planungs-, UI- und Handbuch-Dokumente explizit als historisch markiert
- Legacy-Plugin-Agent-Service als nicht-canonical gegenüber dem gehärteten Tool-Pfad eingeordnet

## Harmonisiert

- öffentliche Projektbezeichnung: `ABrain`
- sichtbare API-Titel und Frontend-/Monitoring-Branding
- zentrale Setup-, Architektur-, Integrations- und Review-Dokumente
- Flowise-/n8n-Metadaten dort, wo es nur sichtbare Beschriftungen betrifft

## Bewusst verblieben

- Paket-/Import-Slugs wie `legacy runtime`, `agent_nn`
- Deploy-/Helm-/Compose-/Image-Slugs wie `abrain`
- externe Repo-URLs `EcoSphereNetwork/ABrain`
- historische Langform-Handbücher, SVGs und Altbestände, nun aber als historisch eingerahmt

## Sicherheitszustand

Der gehärtete Core bleibt vollständig intakt. Referenzpfad für neue Integrationen bleibt:

- `services/core.py`
- `core/execution/dispatcher.py`
- `core/tools/*`
- `core/models/*`
- `adapters/adminbot/*`

AdminBot-Scope und Dispatcher-/Registry-Härtung wurden nicht aufgeweicht.

## Offene Follow-ups

- vollständige Umbenennung technischer Slugs und Paketpfade
- externe Repo-/Badge-/Pages-Umbenennung
- inhaltliche Modernisierung historischer Langform-Dokumentation
