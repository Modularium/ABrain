# ABrain Rename Review Summary

## Ziel

Kontrollierter Rename der öffentlichen Projektbezeichnung von `Agent-NN` zu `ABrain`, ohne den gehärteten Core, die Dispatcher-/Registry-Schicht oder den sicheren AdminBot-Adapter aufzuweichen.

## Umbenannt

- zentrale Außendarstellung in `README.md`
- neue Projekt- und Setup-Doku in `docs/architecture/PROJECT_OVERVIEW.md` und `docs/setup/DEVELOPMENT_SETUP.md`
- zentrale Dokumentations-Einstiege und Übersichtsseiten unter `docs/`
- sichtbare API-Titel in `server/main.py`, `agentnn/mcp/mcp_server.py` und `monitoring/monitoring/api/server.py`
- sichtbare Frontend-Texte und Titel in `frontend/agent-ui/*`
- sichtbare Monitoring-Texte und Dashboard-Beschriftungen in `monitoring/*`
- zentrale SDK-/API-/Service-Docstrings und Hilfetexte, soweit sie projektprägend oder sichtbar sind

## Bewusst nicht vollständig umbenannt

- Python-Paketname `agentnn`
- Modul- und Importpfade wie `agent_nn`, `nn_models.agent_nn_v2`
- Repo-, Clone- und Publish-URLs unter `EcoSphereNetwork/Agent-NN`
- Docusaurus- und GitHub-Pages-Slugs wie `baseUrl` oder `projectName`
- Helm-, Docker-, Compose- und andere Deployment-Slugs mit `agent-nn`
- historische oder sekundäre Langform-Dokumente, SVGs und Altbestände, z. B. unter `docs/BenutzerHandbuch/`

## Ergänzte Dokumentation

- `docs/reviews/abrain_rename_plan.md`
- `docs/architecture/PROJECT_OVERVIEW.md`
- `docs/setup/DEVELOPMENT_SETUP.md`

Diese Dokumente beschreiben den aktuellen ABrain-Stand ehrlich, inklusive Grenzen des Rename-Schritts und weiterhin vorhandener technischer Slugs.

## CI-Erweiterungen

- bestehende `adminbot-security-gates` bleiben unverändert bestehen
- neue allgemeine Kern-CI in `.github/workflows/core-ci.yml`
- die neue CI prüft gezielte Core-/Adapter-/Service-Tests sowie `py_compile` der gehärteten Kernmodule

## Bewusst verbleibende Agent-NN-Referenzen

- technische Slugs in Paketnamen, Imports, lokalen Dateisystempfaden und Deployments
- externe Repo-/Lizenz-/Release-Links
- historische Review- und Konsolidierungsdokumente, wenn Pfadangaben oder Migrationskontext erhalten bleiben müssen
- längere historische Handbücher, SVGs und Alt-Dokumente außerhalb des zentralen ABrain-Einstiegspfads

## Ergebnis

Das Repository kann jetzt in seiner zentralen Außendarstellung konsistent als `ABrain` geführt werden. Der gehärtete Core, die Dispatcher-/Registry-Struktur und der AdminBot-Adapter bleiben unverändert führend. Offene technische Slugs und historische Alt-Dokumente sind als separate Follow-ups klar abgrenzbar.
