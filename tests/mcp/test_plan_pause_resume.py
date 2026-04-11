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


def test_run_plan_pause_and_approve_resume(monkeypatch):
    core = importlib.import_module("services.core")
    monkeypatch.setattr(
        core,
        "run_task_plan",
        lambda task: {
            "plan": {"task_id": "plan-1"},
            "result": {
                "status": "paused",
                "state": {"pending_approval_id": "approval-1"},
                "aggregated_warnings": [],
            },
            "trace": {"trace_id": "trace-plan"},
        },
    )
    monkeypatch.setattr(
        core,
        "approve_plan_step",
        lambda approval_id: {
            "approval": {"approval_id": approval_id},
            "result": {"status": "completed", "aggregated_warnings": []},
            "trace": {"trace_id": "trace-plan"},
        },
    )

    server = MCPV2Server()
    _initialize(server)
    paused = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "abrain.run_plan",
                "arguments": {
                    "task_type": "workflow_automation",
                    "description": "Run the workflow",
                    "input_data": {},
                    "options": {"allow_parallel": True},
                },
            },
        }
    )
    resumed = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "abrain.approve",
                "arguments": {"approval_id": "approval-1"},
            },
        }
    )

    assert paused["result"]["structuredContent"]["status"] == "paused"
    assert paused["result"]["structuredContent"]["plan_result"]["state"]["pending_approval_id"] == "approval-1"
    assert resumed["result"]["structuredContent"]["status"] == "success"
