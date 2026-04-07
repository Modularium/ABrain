# Plugin System

ABrain supports optional service and tool plugins. Plugins live in the top level
`plugins/` directory and contain a `plugin.py` implementation and a
`manifest.yaml` metadata file.

Wichtig: generische Plugin-Ausfuehrung ist nicht Teil der gehärteten
Sicherheitsarchitektur. Der historische Plugin-Agent-Pfad fuehrt keine freien
Tool-Aufrufe mehr aus. Fuer neue sicherheitsrelevante Integrationen gilt der
feste Core-Pfad ueber `services/core.py` und `core/tools/*`.

Der Legacy-Bestand kann weiterhin dokumentiert oder migriert werden. Er ist aber
kein gleichwertiger Referenzpfad zur festen Tool-Schicht.

Historische CLI-Beispiele:

```bash
agentnn plugins list
```

For details on writing plugins refer to [docs/development/plugins.md](development/plugins.md).
