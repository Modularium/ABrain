"""MCP v2 — ``abrain.list_routing_models`` tool surface tests.

Mirrors the read-only routing-catalog surface landed for the CLI
(Turn 7 / Turn 16) and the HTTP gateway (Turn 17).  The MCP handler
is a thin delegate of :func:`services.core.get_routing_models`; the
tests here verify tool registration, delegation, filter forwarding
and the error envelope translation that flips ``isError`` on the
MCP response.
"""

from __future__ import annotations

import importlib
import json

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


def _sample_payload() -> dict:
    return {
        "total": 2,
        "catalog_size": 5,
        "filters": {
            "tier": None,
            "provider": None,
            "purpose": None,
            "available_only": False,
        },
        "tiers": {"local": 1, "small": 1, "medium": 0, "large": 0},
        "providers": {
            "anthropic": 1,
            "openai": 0,
            "google": 0,
            "local": 1,
            "custom": 0,
        },
        "purposes": {
            "planning": 0,
            "classification": 0,
            "ranking": 0,
            "retrieval_assist": 0,
            "local_assist": 2,
            "specialist": 0,
        },
        "models": [
            {
                "model_id": "llama-3-8b-local-q4",
                "display_name": "Llama 3 8B local Q4",
                "provider": "local",
                "tier": "local",
                "purposes": ["local_assist"],
                "context_window": 8192,
                "cost_per_1k_tokens": None,
                "p95_latency_ms": 800,
                "supports_tool_use": False,
                "supports_structured_output": False,
                "is_available": True,
                "quantization": {
                    "method": "gguf_q4_k_m",
                    "bits": 4,
                    "baseline_model_id": "llama-3-8b",
                    "quality_delta_vs_baseline": -0.03,
                    "evaluated_on": "abrain-routing-eval-v3",
                },
                "distillation": None,
                "energy_profile": {
                    "avg_power_watts": 15.0,
                    "source": "measured",
                },
            },
            {
                "model_id": "claude-haiku-4-5",
                "display_name": "Claude Haiku 4.5",
                "provider": "anthropic",
                "tier": "small",
                "purposes": ["local_assist"],
                "context_window": 200000,
                "cost_per_1k_tokens": 0.001,
                "p95_latency_ms": 500,
                "supports_tool_use": True,
                "supports_structured_output": True,
                "is_available": True,
                "quantization": None,
                "distillation": None,
                "energy_profile": None,
            },
        ],
    }


class TestToolRegistration:
    def test_tool_is_listed(self):
        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        tools = {tool["name"] for tool in response["result"]["tools"]}
        assert "abrain.list_routing_models" in tools

    def test_input_schema_documents_filters(self):
        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        tool = next(
            t for t in response["result"]["tools"]
            if t["name"] == "abrain.list_routing_models"
        )
        properties = tool["inputSchema"]["properties"]
        assert set(properties.keys()) == {
            "tier",
            "provider",
            "purpose",
            "available_only",
        }
        # Strict tool schema: no extra arguments permitted.
        assert tool["inputSchema"].get("additionalProperties") is False


class TestToolCall:
    def test_delegates_to_canonical_service(self, monkeypatch):
        core = importlib.import_module("services.core")
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _sample_payload()

        monkeypatch.setattr(core, "get_routing_models", fake)

        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.list_routing_models",
                    "arguments": {},
                },
            }
        )

        structured = response["result"]["structuredContent"]
        assert response["result"]["isError"] is False
        assert structured["status"] == "success"
        assert structured["total"] == 2
        assert structured["catalog_size"] == 5
        # Lineage + energy keys flow through verbatim.
        first = structured["models"][0]
        assert first["quantization"]["method"] == "gguf_q4_k_m"
        assert first["energy_profile"] == {
            "avg_power_watts": 15.0,
            "source": "measured",
        }
        assert structured["models"][1]["energy_profile"] is None
        # Default filters mirror the canonical reader defaults.
        assert captured == {
            "tier": None,
            "provider": None,
            "purpose": None,
            "available_only": False,
        }

    def test_forwards_filters(self, monkeypatch):
        core = importlib.import_module("services.core")
        captured: dict = {}
        monkeypatch.setattr(
            core,
            "get_routing_models",
            lambda **kw: captured.update(kw) or _sample_payload(),
        )

        server = MCPV2Server()
        _initialize(server)
        server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.list_routing_models",
                    "arguments": {
                        "tier": "local",
                        "provider": "local",
                        "purpose": "local_assist",
                        "available_only": True,
                    },
                },
            }
        )
        assert captured == {
            "tier": "local",
            "provider": "local",
            "purpose": "local_assist",
            "available_only": True,
        }

    def test_empty_string_filters_normalize_to_none(self, monkeypatch):
        """Empty-string filter args are treated as unset.

        Callers that forward optional params without branching on
        presence shouldn't hit the service-side enum validator for a
        trailing ``tier=""``.
        """
        core = importlib.import_module("services.core")
        captured: dict = {}
        monkeypatch.setattr(
            core,
            "get_routing_models",
            lambda **kw: captured.update(kw) or _sample_payload(),
        )

        server = MCPV2Server()
        _initialize(server)
        server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.list_routing_models",
                    "arguments": {"tier": "   ", "provider": ""},
                },
            }
        )
        assert captured["tier"] is None
        assert captured["provider"] is None

    def test_service_error_envelope_flips_is_error(self, monkeypatch):
        core = importlib.import_module("services.core")
        monkeypatch.setattr(
            core,
            "get_routing_models",
            lambda **_: {
                "error": "invalid_tier",
                "detail": "Unknown tier 'xxl'. Valid: local, small, medium, large",
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
                    "name": "abrain.list_routing_models",
                    "arguments": {"tier": "xxl"},
                },
            }
        )
        structured = response["result"]["structuredContent"]
        assert response["result"]["isError"] is True
        assert structured["status"] == "error"
        assert structured["error"] == "invalid_tier"
        assert "xxl" in structured["detail"]

    def test_rejects_unknown_arguments(self):
        """Strict input schema — extra kwargs fail as JSON-RPC -32602."""
        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.list_routing_models",
                    "arguments": {"unknown_filter": "local"},
                },
            }
        )
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_text_content_mirrors_structured_payload(self, monkeypatch):
        """Server-side contract: `content[0].text` is a JSON dump of structuredContent."""
        core = importlib.import_module("services.core")
        monkeypatch.setattr(core, "get_routing_models", lambda **_: _sample_payload())

        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.list_routing_models",
                    "arguments": {},
                },
            }
        )
        text_payload = json.loads(response["result"]["content"][0]["text"])
        assert text_payload == response["result"]["structuredContent"]


class TestRealCatalogSmoke:
    def test_end_to_end_against_default_models(self):
        """End-to-end smoke against the real DEFAULT_MODELS catalog.

        Guards the MCP → services.core → DEFAULT_MODELS wiring without
        mocks.  A future schema drift (e.g. required key on
        ModelDescriptor) surfaces here, not only in CLI/HTTP tests.
        """
        server = MCPV2Server()
        _initialize(server)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "abrain.list_routing_models",
                    "arguments": {},
                },
            }
        )
        structured = response["result"]["structuredContent"]
        assert response["result"]["isError"] is False
        assert structured["status"] == "success"
        assert structured["catalog_size"] >= 1
        for model in structured["models"]:
            assert "quantization" in model
            assert "distillation" in model
            assert "energy_profile" in model
        # Honesty rule — catalog ships with no baked-in wattage.
        assert all(m["energy_profile"] is None for m in structured["models"])
