import importlib

import pytest

from interfaces.mcp.server import MCPV2Server
from interfaces.mcp.tool_registry import TOOLS

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


def test_run_task_tool_returns_success_with_trace_and_explainability(monkeypatch):
    core = importlib.import_module("services.core")
    monkeypatch.setattr(
        core,
        "run_task",
        lambda task: {
            "status": "completed",
            "execution": {"success": True, "output": {"ok": True}},
            "decision": {"selected_agent_id": "adminbot-agent"},
            "approval": None,
            "governance": {"effect": "allow"},
            "warnings": [],
            "trace": {"trace_id": "trace-1"},
        },
    )
    monkeypatch.setattr(
        core,
        "get_explainability",
        lambda trace_id: {
            "explainability": [
                {
                    "selected_agent_id": "adminbot-agent",
                    "approval_required": False,
                    "routing_reason_summary": "selected adminbot-agent",
                    "matched_policy_ids": [],
                }
            ]
        },
    )

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
                    "task_type": "system_status",
                    "description": "Read current status",
                    "input_data": {},
                    "preferences": {},
                },
            },
        }
    )

    assert response["result"]["isError"] is False
    assert response["result"]["structuredContent"]["status"] == "success"
    assert response["result"]["structuredContent"]["trace_id"] == "trace-1"
    assert response["result"]["structuredContent"]["explainability_summary"]["selected_agent"] == "adminbot-agent"


def test_tools_list_contains_only_static_v2_tools():
    server = MCPV2Server()
    _initialize(server)

    response = server.handle_message(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
    )

    assert [tool["name"] for tool in response["result"]["tools"]] == [
        "abrain.run_task",
        "abrain.run_plan",
        "abrain.approve",
        "abrain.reject",
        "abrain.list_pending_approvals",
        "abrain.get_trace",
        "abrain.explain",
        "abrain.list_routing_models",
        "abrain.reason_labos_reactor_daily_overview",
        "abrain.reason_labos_incident_review",
        "abrain.reason_labos_maintenance_suggestions",
        "abrain.reason_labos_schedule_runtime_review",
        "abrain.reason_labos_cross_domain_overview",
    ]


def test_tool_input_schemas_are_strict_objects():
    for tool in TOOLS.values():
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False


def test_run_task_rejects_unknown_arguments():
    server = MCPV2Server()
    _initialize(server)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "abrain.run_task",
                "arguments": {
                    "task_type": "system_status",
                    "description": "Read current status",
                    "input_data": {},
                    "preferences": {},
                    "unexpected": True,
                },
            },
        }
    )

    assert response["error"]["code"] == -32602
    assert response["error"]["message"] == "Invalid arguments for tool: abrain.run_task"
