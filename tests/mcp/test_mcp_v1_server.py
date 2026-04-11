import ast
import io
import json
from pathlib import Path
import tomllib

import pytest

from interfaces.mcp_v1.server import MCPV1Server, run_stdio_server
from scripts import abrain_mcp

pytestmark = pytest.mark.unit


def _initialize(server: MCPV1Server) -> dict:
    return server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "pytest-client", "version": "1.0"},
            },
        }
    )


def test_valid_tool_call_returns_success():
    calls = []

    def fake_execute_tool(name, payload, **kwargs):
        calls.append((name, payload, kwargs))
        return {"tool_name": name, "payload": payload}

    server = MCPV1Server(execute_tool=fake_execute_tool)
    _initialize(server)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "list_agents", "arguments": {}},
        }
    )

    assert response["result"]["isError"] is False
    assert response["result"]["structuredContent"]["tool_name"] == "list_agents"
    assert calls[0][2]["correlation_id"] == "mcp-v1:2"


def test_tools_list_returns_only_allowlisted_tools():
    server = MCPV1Server(execute_tool=lambda *args, **kwargs: {})
    _initialize(server)

    response = server.handle_message(
        {"jsonrpc": "2.0", "id": 20, "method": "tools/list", "params": {}}
    )

    assert [tool["name"] for tool in response["result"]["tools"]] == [
        "list_agents",
        "adminbot_system_status",
        "adminbot_system_health",
        "adminbot_service_status",
    ]


def test_unknown_tool_returns_jsonrpc_error():
    server = MCPV1Server(execute_tool=lambda *args, **kwargs: {})
    _initialize(server)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "dispatch_task", "arguments": {}},
        }
    )

    assert response["error"]["code"] == -32602
    assert response["error"]["message"] == "Unknown tool: dispatch_task"


def test_invalid_schema_returns_jsonrpc_error():
    server = MCPV1Server(execute_tool=lambda *args, **kwargs: {})
    _initialize(server)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "adminbot_service_status", "arguments": {"service_name": ""}},
        }
    )

    assert response["error"]["code"] == -32602
    assert response["error"]["message"] == "Invalid arguments for tool: adminbot_service_status"


def test_adminbot_tool_call_is_forwarded_to_core_execute_tool():
    calls = []

    def fake_execute_tool(name, payload, **kwargs):
        calls.append((name, payload, kwargs))
        return {"ok": True}

    server = MCPV1Server(execute_tool=fake_execute_tool)
    _initialize(server)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "adminbot_system_status",
                "arguments": {},
            },
        }
    )

    assert response["result"]["isError"] is False
    assert calls[0][0] == "adminbot_system_status"
    assert calls[0][1] == {}
    assert calls[0][2]["correlation_id"] == "mcp-v1:5"
    assert calls[0][2]["requested_by"].id == "mcp-v1:pytest-client"


def test_server_module_does_not_import_handlers_registry_or_adminbot_adapter():
    source = Path("interfaces/mcp_v1/server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "core.tools.handlers" not in imports
    assert "core.tools.registry" not in imports
    assert "adapters.adminbot.client" not in imports
    assert "adapters.adminbot.service" not in imports


def test_stdio_jsonrpc_roundtrip():
    input_stream = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "stdio-client", "version": "1.0"},
                        },
                    }
                ),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            ]
        )
        + "\n"
    )
    output_stream = io.StringIO()

    run_stdio_server(input_stream=input_stream, output_stream=output_stream)

    lines = [line for line in output_stream.getvalue().splitlines() if line]
    assert len(lines) == 2
    assert json.loads(lines[0])["result"]["protocolVersion"] == "2025-03-26"
    assert json.loads(lines[1])["result"]["tools"][0]["name"] == "list_agents"


def test_cli_wrapper_calls_stdio_server(monkeypatch):
    called = {}

    def fake_run_stdio_server():
        called["ok"] = True

    monkeypatch.setattr(abrain_mcp, "run_stdio_server", fake_run_stdio_server)
    abrain_mcp.main()

    assert called["ok"] is True


def test_pyproject_exposes_stable_mcp_console_entry():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["abrain-mcp"] == "interfaces.mcp.server:main"
    assert pyproject["project"]["scripts"]["abrain-mcp-v1"] == "interfaces.mcp_v1.server:main"
    assert pyproject["tool"]["poetry"]["scripts"]["abrain-mcp"] == "interfaces.mcp.server:main"
    assert pyproject["tool"]["poetry"]["scripts"]["abrain-mcp-v1"] == "interfaces.mcp_v1.server:main"
