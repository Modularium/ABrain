import importlib

import pytest

from interfaces.mcp.server import MCPV2Server

pytestmark = pytest.mark.unit


def _initialize(server: MCPV2Server) -> dict:
    return server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest-client", "version": "1.0"},
            },
        }
    )


def test_run_task_policy_deny_surfaces_error_without_crash(monkeypatch):
    core = importlib.import_module("services.core")
    monkeypatch.setattr(
        core,
        "run_task",
        lambda task: {
            "status": "denied",
            "execution": {"success": False, "error": {"error_code": "policy_denied"}},
            "decision": {"selected_agent_id": "codex-agent"},
            "approval": None,
            "governance": {"effect": "deny", "matched_rules": ["deny-rule"]},
            "warnings": ["policy_denied"],
            "trace": {"trace_id": "trace-denied"},
        },
    )
    monkeypatch.setattr(core, "get_explainability", lambda trace_id: {"explainability": []})

    server = MCPV2Server()
    _initialize(server)
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "abrain.run_task",
                "arguments": {
                    "task_type": "code_generate",
                    "description": "Generate code",
                    "input_data": {},
                    "preferences": {},
                },
            },
        }
    )

    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["status"] == "error"
    assert response["result"]["structuredContent"]["governance"]["effect"] == "deny"
