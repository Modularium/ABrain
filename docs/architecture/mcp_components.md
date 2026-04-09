# MCP Components

Hinweis: Diese Seite beschreibt die historische MCP-Zerlegung. Fuer den aktuellen produktiven Laufzeitpfad ist `services/*` canonical; `mcp/*` ist `legacy (disabled)`.

- **Task-Dispatcher**: central orchestration service. Decides which worker should execute a task.
- **Agent Registry**: stores available worker services, capabilities and health status.
- **Session Manager**: keeps conversation history and temporary state.
- **Vector Store Service**: provides semantic search across documents.
- **LLM Gateway**: exposes a unified API to various LLM backends.
- **User Manager Service**: manages user accounts and tokens.
- **Worker Services**: domain specific executors, e.g. Dev, OpenHands, LOH.
- **API Gateway**: optional entrypoint for external requests with auth and rate limiting.
- **Monitoring/Logging**: collects logs and metrics from all services.

## Service Registration

Historisch wurden Worker ueber `mcp/agents.yaml` und direkte MCP-Routen modelliert. Dieser Pfad ist nicht mehr produktiv. Fuer den aktuellen Stack sind `services/agent_registry` und der gehaertete Core die Referenz.
