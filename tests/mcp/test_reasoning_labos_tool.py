"""MCP surface tests — `abrain.reason_labos_*` tools.

Pin that the MCP handlers delegate verbatim to
`services.core.run_labos_reasoning` and translate error envelopes to
`isError=true`.  No reasoning logic in the MCP layer.
"""

from __future__ import annotations

import pytest

from interfaces.mcp.server import MCPV2Server
from interfaces.mcp.tool_registry import TOOLS

pytestmark = pytest.mark.unit


_MODES = (
    "reactor_daily_overview",
    "incident_review",
    "maintenance_suggestions",
    "schedule_runtime_review",
    "cross_domain_overview",
    "module_daily_overview",
    "module_incident_review",
    "module_coordination_review",
    "module_capability_risk_review",
    "robotops_cross_domain_overview",
)


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


def _ok_payload(mode: str) -> dict:
    return {
        "reasoning_mode": f"labos_{mode}",
        "summary": "ok",
        "highlights": [],
        "prioritized_entities": [],
        "recommended_actions": [],
        "recommended_checks": [],
        "approval_required_actions": [],
        "blocked_or_deferred_actions": [],
        "used_context_sections": [],
        "trace_metadata": {},
    }


class TestToolRegistration:
    def test_all_five_reason_labos_tools_registered(self):
        for mode in _MODES:
            assert f"abrain.reason_labos_{mode}" in TOOLS

    def test_input_schemas_are_strict_objects(self):
        for mode in _MODES:
            schema = TOOLS[f"abrain.reason_labos_{mode}"].input_schema
            assert schema["type"] == "object"
            assert schema["additionalProperties"] is False
            assert "context" in schema["properties"]


class TestToolCall:
    @pytest.mark.parametrize("mode", _MODES)
    def test_tool_delegates_to_service_with_mode(self, monkeypatch, mode):
        captured: dict = {}

        def fake(mode_arg, context_arg):
            captured["mode"] = mode_arg
            captured["context"] = context_arg
            return _ok_payload(mode_arg)

        monkeypatch.setattr("services.core.run_labos_reasoning", fake)

        server = MCPV2Server()
        _initialize(server)
        ctx = {"reactors": [{"reactor_id": "R1", "status": "warning"}]}
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": f"abrain.reason_labos_{mode}",
                    "arguments": {"context": ctx},
                },
            }
        )

        assert response["result"]["isError"] is False
        content = response["result"]["structuredContent"]
        assert content["status"] == "success"
        assert content["reasoning_mode"] == f"labos_{mode}"
        assert captured == {"mode": mode, "context": ctx}

    def test_error_envelope_flips_is_error(self, monkeypatch):
        monkeypatch.setattr(
            "services.core.run_labos_reasoning",
            lambda mode, ctx: {
                "error": "invalid_context",
                "detail": [{"loc": "incidents", "msg": "bad"}],
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
                    "name": "abrain.reason_labos_incident_review",
                    "arguments": {"context": {"incidents": [{"bogus": 1}]}},
                },
            }
        )
        assert response["result"]["isError"] is True
        content = response["result"]["structuredContent"]
        assert content["status"] == "error"
        assert content["error"] == "invalid_context"

    def test_unknown_argument_rejected_as_json_rpc_error(self):
        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.reason_labos_reactor_daily_overview",
                    "arguments": {"context": {}, "extra": 1},
                },
            }
        )
        # JSON-RPC invalid params → -32602
        assert "error" in response
        assert response["error"]["code"] == -32602


class TestRealServiceSmoke:
    def test_end_to_end_against_real_reasoner(self):
        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.reason_labos_reactor_daily_overview",
                    "arguments": {
                        "context": {
                            "reactors": [
                                {"reactor_id": "R1", "status": "warning"}
                            ]
                        }
                    },
                },
            }
        )
        assert response["result"]["isError"] is False
        content = response["result"]["structuredContent"]
        assert content["status"] == "success"
        # All Response Shape V2 keys forwarded verbatim.
        for key in (
            "reasoning_mode", "summary", "highlights", "prioritized_entities",
            "recommended_actions", "recommended_checks",
            "approval_required_actions", "blocked_or_deferred_actions",
            "used_context_sections", "trace_metadata",
        ):
            assert key in content
