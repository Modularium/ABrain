# Plugin System

ABrain supports optional service and tool plugins. Plugins live in the top level
`plugins/` directory and contain a `plugin.py` implementation and a
`manifest.yaml` metadata file.

Use the CLI to list and execute plugins:

```bash
agentnn plugins list
agentnn plugins run filesystem --input '{"action": "read", "path": "test.txt"}'
```

For details on writing plugins refer to [docs/development/plugins.md](development/plugins.md).
