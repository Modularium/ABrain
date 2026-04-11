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


def test_trace_and_explain_tools_return_stored_payloads(monkeypatch):
    core = importlib.import_module("services.core")
    monkeypatch.setattr(
        core,
        "get_trace",
        lambda trace_id: {"trace": {"trace": {"trace_id": trace_id, "status": "completed"}, "spans": []}},
    )
    monkeypatch.setattr(
        core,
        "get_explainability",
        lambda trace_id: {
            "explainability": [
                {
                    "trace_id": trace_id,
                    "selected_agent_id": "claude-reviewer",
                    "approval_required": True,
                    "routing_reason_summary": "selected claude-reviewer",
                    "matched_policy_ids": ["review-rule"],
                }
            ]
        },
    )

    server = MCPV2Server()
    _initialize(server)
    trace_response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "abrain.get_trace",
                "arguments": {"trace_id": "trace-1"},
            },
        }
    )
    explain_response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "abrain.explain",
                "arguments": {"trace_id": "trace-1"},
            },
        }
    )

    assert trace_response["result"]["structuredContent"]["trace"]["trace"]["trace_id"] == "trace-1"
    assert explain_response["result"]["structuredContent"]["explainability_summary"]["selected_agent"] == "claude-reviewer"
    assert explain_response["result"]["structuredContent"]["explainability_summary"]["policy_decision"] == "require_approval"
