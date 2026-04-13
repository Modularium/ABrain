# Repo Rename And Release Audit

## Bereinigte Namensreste

Für den aktuellen Release wurden die zentralen, sichtbaren Einstiege konsistent auf `ABrain` gezogen:

- `README.md`
- `docs/index.md`
- `docs/overview.md`
- `docs/architecture/PROJECT_OVERVIEW.md`
- `docs/development/setup.md`
- `docs/development/contributing.md`
- `docs/development/cicd.md`
- Release- und Review-Dokumente

Zusätzlich wurden alte GitHub-Links auf das neue Repository `Modularium/ABrain` umgestellt, wo dies in zentralen Entwicklerdokumenten stabil möglich war.

## Bewusst technisch oder historisch beibehalten

Folgende Identifiers bleiben bewusst erhalten:

- Poetry-Paketname `legacy runtime`
- technische CLI- und Modulpfade mit `legacy runtime`
- Docusaurus-/npm-Namen `abrain-docs`
- Dateisystempfade wie `/home/dev/ABrain`
- Container-, Helm- oder Image-Slugs mit `abrain`
- ältere Nutzer-, Wiki- und Legacy-Dokumente mit historischem `ABrain`-Wortlaut

## Warum diese Reste bleiben

Diese Bezeichner sind an Importpfade, Paketierung, Build-Artefakte, Deployments oder lokale Betriebsrealität gebunden. Ein aggressiver Voll-Rename in diesem Schritt wäre technisch riskanter als der erzielte Nutzen.

## Historische Bereiche

Historische Dokumente und Altpfade bleiben im Repository, konkurrieren aber nicht mehr mit den zentralen Einstiegen. Für den Foundations-Release sind vor allem `README.md`, die Architektur-Dokumente, Setup-/CI-Doku und die Release-Artefakte maßgeblich.
