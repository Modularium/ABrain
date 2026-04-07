# Plugin System

ABrain supports optional service and tool plugins. Plugins live in the top level
`plugins/` directory and contain a `plugin.py` implementation and a
`manifest.yaml` metadata file.

Wichtig: generische Plugin-Ausfuehrung ist nicht Teil der gehärteten
Sicherheitsarchitektur. Der fruehere Plugin-Agent-Pfad ist `legacy (disabled)`
und fuehrt keine freien Tool-Aufrufe mehr aus. Fuer neue sicherheitsrelevante
Integrationen gilt der `canonical path` ueber `services/core.py` und
`core/tools/*`.

Der verbleibende Plugin-Bestand ist nur noch `historical / legacy (not active
runtime path)` oder Migrationsmaterial, kein gleichwertiger Referenzpfad zur
festen Tool-Schicht.

Historische CLI-Beispiele:

```bash
agentnn plugins list
```

For details on writing plugins refer to [docs/development/plugins.md](development/plugins.md).
