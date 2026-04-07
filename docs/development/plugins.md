# Service Plugins

> Status: Historisch/geplant. Diese Seite beschreibt den älteren Plugin-Agent-Service und geplante Erweiterungen. Sie ist nicht der Referenzpfad für gehärtete Tool-Ausführung oder AdminBot-Integration.

The MCP architecture will support pluggable service components. Planned plugin types include:

- **Tools** – extend worker capabilities with external APIs
- **Chains** – compose multiple LLM calls
- **Hooks** – intercept messages or add custom logic

These plugins can be loaded by services at startup. Details will be defined in future planning documents.

## Directory Structure

Plugins live under the top level `plugins/` folder. Each plugin resides in its
own sub directory:

```
plugins/
  <tool_name>/
    plugin.py        # implementation
    manifest.yaml    # metadata (name, version, summary)
```

The plugin must expose a class `Plugin` that implements
`ToolPlugin.execute(input: dict, context: dict) -> dict`.
Services use `PluginManager` to discover available tools at runtime.

Für sicherheitsrelevante Integrationen gilt stattdessen:

- feste Tool-Registry in `core/tools/registry.py`
- getypte Inputs in `core/models/*`
- Dispatcher-Ausführung in `core/execution/dispatcher.py`
- keine freie Action- oder Payload-Weitergabe an AdminBot
