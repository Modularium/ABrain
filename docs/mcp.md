# Model Context Protocol Integration

ABrain exposes a minimal implementation of the **Model Context Protocol (MCP)**
to exchange context information with third party services. The MCP server is
implemented in `agentnn.mcp.mcp_server` and provides the following endpoints:

- `GET /v1/mcp/ping` – health check
- `POST /v1/mcp/execute` – dispatch a `ModelContext` to the internal task
  dispatcher and return the result
- `POST /v1/mcp/task/execute` – alias for `/execute`
- `POST /v1/mcp/agent/create` – register a new worker agent
- `POST /v1/mcp/tool/use` – invoke a plugin tool
- `POST /v1/mcp/context` – store a context in the session manager
- `POST /v1/mcp/context/save` – persist a context entry
- `GET /v1/mcp/context/{session_id}` – retrieve all contexts for a session
- `GET /v1/mcp/context/get/{session_id}` – alias for `/context/{session_id}`
- `GET /v1/mcp/context/load/{session_id}` – load persisted contexts
- `GET /v1/mcp/context/history` – list sessions with stored context

A lightweight client wrapper is available via `agentnn.mcp.MCPClient`.

Configure the MCP integration using `agentnn/config.yml`:

```yaml
mcp:
  enabled: true
  endpoint: "http://localhost:9000"
  mode: "server"
```

When enabled, external tools can interact with Agent‑NN using the official MCP
schemas. See the official specification for further details.

Example request using ``curl``:

```bash
curl -X POST http://localhost:9000/v1/mcp/execute \
     -H "Content-Type: application/json" \
     -d '{"task_context": {"task_type": "chat", "description": "Hello"}}'
```

## Additional Endpoints

The server now exposes further MCP routes to control the system:

- `POST /v1/mcp/agent/register` – register an agent
- `GET /v1/mcp/agent/list` – list all agents
- `GET /v1/mcp/agent/info/{name}` – details for one agent
- `POST /v1/mcp/session/start` – create a session
- `GET /v1/mcp/session/status/{id}` – session status
- `POST /v1/mcp/session/restore/{snapshot}` – restore from snapshot
- `POST /v1/mcp/task/dispatch` – dispatch a task
- `POST /v1/mcp/task/ask` – simplified alias for dispatch
- `POST /v1/mcp/prompt/refine` – refine a prompt
- `GET /v1/mcp/context/map` – context map of stored sessions

Start the server with:

```bash
agentnn mcp serve --host 0.0.0.0 --port 8090
```

### Using external MCP tools

Register remote endpoints and invoke tools directly:

```bash
agentnn mcp register-endpoint demo http://mcp.example.com
agentnn mcp invoke demo.text-analyzer --input '{"text": "hello"}'
agentnn mcp list-tools demo
```

Agents can reference tools via `mcp://` URLs in their configuration.
