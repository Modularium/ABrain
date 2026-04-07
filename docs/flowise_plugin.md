# Flowise Plugin Bundle

Dieses Dokument beschreibt, wie alle Agent‑NN Nodes als fertiges Flowise‑Plugin bereitgestellt werden.
Ein Manifest `flowise-plugin.json` listet die enthaltenen Komponenten auf und erleichtert die Installation. Seit Version 1.0.4 enthält es zusätzlich ein Build-Datum und eine kompatible Flowise-Version.

## Manifest erzeugen

```bash
python tools/generate_flowise_plugin.py
```

Das Skript liest die Node‑Dateien aus `integrations/flowise-nodes` und erzeugt ein Manifest mit Name, Version und Node‑Liste.

## Plugin erstellen

```bash
python tools/package_plugin.py --output agentnn_flowise_plugin.zip
```

Damit werden Node‑Definitionen, JavaScript-Dateien und das Manifest zu einem Zip‑Archiv gebündelt.

## Versionierung und Updates

Das Manifest enthält die Felder `version`, `buildDate` und `compatibleFlowiseVersion`. Beim Erzeugen wird automatisch der neueste Git‑Tag verwendet, falls vorhanden, andernfalls der Inhalt der Datei `VERSION`.
`flowise_deploy.py` legt im Zielordner eine Datei `plugin_version.txt` ab und verhindert Downgrades.

```bash
python flowise_deploy.py --dest ~/.flowise/nodes/agent-nn
```

Vorhandene Installationen werden nur überschrieben, wenn die neue Version höher ist. Optional kann ein Reload von Flowise ausgelöst werden.

## Installation

1. Lade das Archiv im Flowise‑Plugin-Manager hoch oder kopiere es in das Plugin-Verzeichnis.
2. Starte Flowise neu. Die Nodes erscheinen anschließend unter der Kategorie **ABrain**.

> TODO: Screenshot "flowise_example.png" ergänzen
