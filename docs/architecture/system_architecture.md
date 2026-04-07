# System Architecture

The MCP version of ABrain is composed of several cooperating services. The following diagram illustrates the overall flow.

```mermaid
graph TD
    A[User/CLI] --> B[API Gateway]
    B --> C[Task Dispatcher]
    B --> U[User Manager]
    C --> D[Agent Registry]
    C --> E[Session Manager]
    C --> F[Worker Services]
    C --> G[Vector Store]
    C --> H[LLM Gateway]
    F --> G
    F --> H
```

### Components

- **Task Dispatcher**: central orchestrator that selects the right worker for each task.
- **Agent Registry**: database of all available worker services.
- **Session Manager**: stores ongoing conversation context.
- **Worker Services**: execute domain specific actions.
- **Vector Store**: semantic search across documentation and code.
- **LLM Gateway**: unified access to language models.
- **User Manager**: manages user accounts and tokens.
- **API Gateway**: optional entry point with authentication and routing.

This setup replaces the former SupervisorAgent architecture and enables independent scaling of each service.
