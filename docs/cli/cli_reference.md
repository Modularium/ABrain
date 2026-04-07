# CLI Reference

The ABrain Command Line Interface (CLI) provides a convenient way to interact with the system.

## Installation

Install the CLI using pip:
```bash
pip install smolit-llm-nn
```

## Authentication

Before using the CLI, you need to authenticate:

```bash
smolit login
```

This will prompt for your username and password. The authentication token will be stored in `~/.smolit/token`.

## Task Management

### Submit Task

Submit a task for execution:

```bash
smolit task "Task description" [--domain DOMAIN] [--priority PRIORITY]
```

Options:
- `--domain`: Optional domain hint for task routing
- `--priority`: Task priority (1-10, default: 1)

Example:
```bash
smolit task "Analyze market trends for tech stocks" --domain finance --priority 3
```

The command will display:
1. Task execution progress
2. Task result in JSON format
3. Performance metrics table

## Agent Management

### List Agents

List all available agents:

```bash
smolit agents
```

This displays a table with:
- Agent name
- Domain
- Capabilities

### Create Agent

Create a new agent:

```bash
smolit create-agent NAME DOMAIN CAPABILITIES CONFIG_FILE
```

Arguments:
- `NAME`: Agent name
- `DOMAIN`: Agent domain
- `CAPABILITIES`: Space-separated list of capabilities
- `CONFIG_FILE`: Path to JSON configuration file

Example:
```bash
smolit create-agent finance_agent finance "market_analysis risk_assessment" config.json
```

Configuration file format:
```json
{
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000,
    "knowledge_base": {
        "sources": ["finance_docs", "market_data"],
        "update_interval": 3600
    }
}
```

## Monitoring

### Show Metrics

Display system metrics:

```bash
smolit metrics
```

This shows a table with:
- CPU usage
- Memory usage
- Active agents
- Task queue size
- Average response time

## A/B Testing

### Create Test

Create a new A/B test:

```bash
smolit create-test CONFIG_FILE
```

Configuration file format:
```json
{
    "name": "prompt_optimization",
    "variants": [
        {
            "name": "baseline",
            "config": {
                "prompt_template": "Original prompt..."
            }
        },
        {
            "name": "experimental",
            "config": {
                "prompt_template": "New prompt..."
            }
        }
    ],
    "metrics": ["response_quality", "execution_time"],
    "duration_days": 7
}
```

### Show Test Results

Display A/B test results:

```bash
smolit test-results TEST_ID
```

This shows:
1. Test status
2. Variant performance
3. Statistical analysis
4. Winner determination

## Configuration

The CLI can be configured using:
1. Environment variables
2. Configuration file (`~/.smolit/config.json`)

Environment variables:
- `SMOLIT_API_URL`: API server URL
- `SMOLIT_TOKEN_FILE`: Token file path

Configuration file format:
```json
{
    "api_url": "http://localhost:8000",
    "token_file": "~/.smolit/token",
    "default_priority": 1,
    "output_format": "rich"
}
```

## Output Formatting

The CLI uses rich text formatting for better readability:
- Tables for structured data
- Syntax highlighting for JSON
- Progress bars for long operations
- Color-coded status messages

Example output:
```
╭──────────── Task Result ────────────╮
│ {                                   │
│   "analysis": {                     │
│     "sentiment": "positive",        │
│     "confidence": 0.92              │
│   }                                 │
│ }                                   │
╰───────────────────────────────────╯

┌─────────────┬─────────┐
│ Metric      │   Value │
├─────────────┼─────────┤
│ Latency     │   0.245 │
│ Tokens      │     127 │
│ Cost        │   0.002 │
└─────────────┴─────────┘
```

## Error Handling

The CLI provides clear error messages with:
- Error type
- Detailed description
- Suggested resolution

Example:
```
Error: Failed to create agent
Cause: Invalid configuration format
Resolution: Ensure config.json follows the required schema
```

## Batch Operations

For batch operations, use the `--batch` flag with a JSON file:

```bash
smolit task --batch tasks.json
```

Batch file format:
```json
{
    "tasks": [
        {
            "description": "Task 1",
            "domain": "finance",
            "priority": 2
        },
        {
            "description": "Task 2",
            "domain": "tech",
            "priority": 1
        }
    ]
}
```

## agent_nn_cli.py
The simplified CLI allows asking an agent directly:

```bash
python cli/agent_nn_cli.py ask --agent dev --input "Erkläre TCP/IP"
```

Use `--interactive` to stay in a chat session. Other commands include
`tools`, `sessions`, `log` and `feedback`.
