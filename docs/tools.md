# Builtin Tools and Models

ABrain ships with a small set of builtin tools. They can be managed via the `agentnn tools` commands; the CLI slug remains unchanged for compatibility.

## Listing Tools

```bash
agentnn tools list
```

The output shows plugin based tools and builtin model wrappers.

## Inspecting a Tool

```bash
agentnn tools inspect agent_nn_v2
```

This prints the Python class used for the tool. Builtin models such as `agent_nn_v2` and the multi task reasoner can be referenced from agent configurations.

### Builtin model wrappers

| Name | Description |
|------|-------------|
| `agent_nn` | Basic AgentNN model |
| `agent_nn_v2` | Extended variant with security checks |
| `dynamic_architecture` | Flexible network that adapts layers |
| `multi_task_reasoner` | Multi-task learning demo |
