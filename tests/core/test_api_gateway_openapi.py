import importlib
import sys
from functools import partial

import anyio
import httpx
import pytest

pytestmark = pytest.mark.unit


def _gateway_module():
    sys.modules.pop("api_gateway.main", None)
    return importlib.import_module("api_gateway.main")


async def _request(app, method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def test_docs_endpoints_are_available():
    gateway = _gateway_module()
    docs_response = anyio.run(_request, gateway.app, "GET", "/docs")
    redoc_response = anyio.run(_request, gateway.app, "GET", "/redoc")
    openapi_response = anyio.run(_request, gateway.app, "GET", "/openapi.json")

    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text
    assert redoc_response.status_code == 200
    assert "ReDoc" in redoc_response.text
    assert openapi_response.status_code == 200


def test_openapi_exposes_only_canonical_control_plane_surface():
    gateway = _gateway_module()
    payload = anyio.run(_request, gateway.app, "GET", "/openapi.json").json()
    paths = payload["paths"]

    assert payload["info"]["title"] == "ABrain Developer API"
    assert "/control-plane/overview" in paths
    assert "/control-plane/agents" in paths
    assert "/control-plane/traces" in paths
    assert "/control-plane/traces/{trace_id}" in paths
    assert "/control-plane/traces/{trace_id}/explainability" in paths
    assert "/control-plane/governance" in paths
    assert "/control-plane/approvals" in paths
    assert "/control-plane/approvals/{approval_id}/approve" in paths
    assert "/control-plane/approvals/{approval_id}/reject" in paths
    assert "/control-plane/plans" in paths
    assert "/control-plane/tasks/run" in paths
    assert "/control-plane/plans/run" in paths
    assert "/control-plane/routing/models" in paths

    assert "/chat" not in paths
    assert "/chat/feedback" not in paths
    assert "/sessions" not in paths
    assert "/agents" not in paths
    assert "/llm/generate" not in paths
    assert "/embed" not in paths
    assert "/metrics" not in paths

    tags = {tag["name"] for tag in payload["tags"]}
    assert {"Control Plane", "Agents", "Traces", "Approvals", "Plans", "Tasks", "Routing"} <= tags


def test_openapi_documents_control_plane_request_and_response_models():
    gateway = _gateway_module()
    payload = anyio.run(_request, gateway.app, "GET", "/openapi.json").json()
    task_run = payload["paths"]["/control-plane/tasks/run"]["post"]
    overview = payload["paths"]["/control-plane/overview"]["get"]

    request_schema = task_run["requestBody"]["content"]["application/json"]["schema"]
    response_schema = task_run["responses"]["200"]["content"]["application/json"]["schema"]
    overview_schema = overview["responses"]["200"]["content"]["application/json"]["schema"]

    assert request_schema["$ref"].endswith("/ControlPlaneRunRequest")
    assert response_schema["$ref"].endswith("/TaskRunResponse")
    assert overview_schema["$ref"].endswith("/ControlPlaneOverviewResponse")


def test_control_plane_overview_http_route_uses_canonical_core(monkeypatch):
    gateway = _gateway_module()

    monkeypatch.setattr(
        "services.core.get_control_plane_overview",
        lambda **kwargs: {
            "summary": {
                "agent_count": 1,
                "pending_approvals": 0,
                "recent_traces": 1,
                "recent_plans": 1,
                "recent_governance_events": 1,
            },
            "system": {
                "name": "ABrain Control Plane",
                "layers": [{"name": "MCP v2", "status": "available"}],
                "governance": {"engine": "PolicyEngine", "registry": "PolicyRegistry", "policy_path": None},
                "warnings": [],
            },
            # S7: health summary field required by ControlPlaneOverviewResponse
            "health": {
                "overall": "healthy",
                "degraded_agent_count": 0,
                "offline_agent_count": 0,
                "paused_plan_count": 0,
                "failed_plan_count": 0,
                "pending_approval_count": 0,
                "has_warnings": False,
                "attention_items": [],
            },
            "agents": [
                {
                    "agent_id": "agent-1",
                    "display_name": "Agent One",
                    "capabilities": ["system.status"],
                    "source_type": "adminbot",
                    "execution_kind": "system_executor",
                    "availability": "online",
                    "trust_level": "trusted",
                    "metadata": {},
                }
            ],
            "pending_approvals": [],
            "recent_traces": [
                {
                    "trace_id": "trace-1",
                    "workflow_name": "run_task",
                    "task_id": "task-1",
                    "started_at": "2026-04-13T10:00:00Z",
                    "ended_at": "2026-04-13T10:00:01Z",
                    "status": "completed",
                    "metadata": {},
                }
            ],
            "recent_plans": [],
            "recent_governance": [
                {
                    "trace_id": "trace-1",
                    "effect": "allow",
                    "matched_policy_ids": [],
                    "approval_required": False,
                }
            ],
        },
    )

    response = anyio.run(_request, gateway.app, "GET", "/control-plane/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["agent_count"] == 1
    assert payload["agents"][0]["agent_id"] == "agent-1"
    assert payload["recent_governance"][0]["effect"] == "allow"


def test_control_plane_task_run_http_route_returns_documented_shape(monkeypatch):
    gateway = _gateway_module()

    monkeypatch.setattr(
        "services.core.run_task",
        lambda payload: {
            "decision": {
                "task_type": payload["task_type"],
                "required_capabilities": ["system.read", "system.status"],
                "ranked_candidates": [],
                "selected_agent_id": "adminbot-agent",
                "selected_score": 0.93,
                "diagnostics": {},
            },
            "execution": {
                "agent_id": "adminbot-agent",
                "success": True,
                "output": {"status": "ok"},
                "raw_output": None,
                "metadata": {},
                "warnings": [],
                "error": None,
                "duration_ms": 12,
                "cost": None,
                "token_count": None,
            },
            "created_agent": None,
            "feedback": None,
            "warnings": [],
            "governance": {
                "effect": "allow",
                "matched_rules": [],
                "winning_rule_id": None,
                "winning_priority": None,
                "reason": "no_policy_matched",
            },
            "approval": None,
            "plan": None,
            "result": None,
            "trace": {
                "trace_id": "trace-task-1",
                "workflow_name": "run_task",
                "task_id": "task-system-status",
                "started_at": "2026-04-13T10:00:00Z",
                "ended_at": "2026-04-13T10:00:01Z",
                "status": "completed",
                "metadata": {"entrypoint": "run_task"},
            },
        },
    )

    response = anyio.run(
        partial(
            _request,
            gateway.app,
            "POST",
            "/control-plane/tasks/run",
            json={
                "task_type": "system_status",
                "description": "Check system health",
                "input_data": {},
                "options": {"timeout": 5},
            },
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["selected_agent_id"] == "adminbot-agent"
    assert payload["execution"]["success"] is True
    assert payload["trace"]["trace_id"] == "trace-task-1"


# ---------------------------------------------------------------------------
# Routing surface (Turn 17)
# ---------------------------------------------------------------------------


def _sample_routing_payload() -> dict:
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


def test_openapi_documents_routing_models_schema():
    gateway = _gateway_module()
    payload = anyio.run(_request, gateway.app, "GET", "/openapi.json").json()
    operation = payload["paths"]["/control-plane/routing/models"]["get"]

    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"].endswith("/RoutingModelsResponse")

    components = payload["components"]["schemas"]
    assert "RoutingModelsResponse" in components
    assert "RoutingModelEntry" in components
    assert "RoutingEnergyProfileEntry" in components
    assert "RoutingQuantizationEntry" in components
    assert "RoutingDistillationEntry" in components

    parameters = {p["name"] for p in operation.get("parameters", [])}
    assert {"tier", "provider", "purpose", "available_only"} <= parameters


def test_routing_models_http_route_returns_documented_shape(monkeypatch):
    gateway = _gateway_module()
    captured: dict = {}

    def fake_get(**kwargs):
        captured.update(kwargs)
        return _sample_routing_payload()

    monkeypatch.setattr("services.core.get_routing_models", fake_get)

    response = anyio.run(
        _request, gateway.app, "GET", "/control-plane/routing/models"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["catalog_size"] == 5
    assert payload["filters"]["available_only"] is False
    # Lineage + energy keys exposed verbatim from the canonical service.
    first = payload["models"][0]
    assert first["quantization"]["method"] == "gguf_q4_k_m"
    assert first["energy_profile"] == {
        "avg_power_watts": 15.0,
        "source": "measured",
    }
    # `None` energy profile flows through as JSON null — operators can
    # distinguish "no profile" from "zero-watt profile" downstream.
    assert payload["models"][1]["energy_profile"] is None
    # Service was called with default filters (None + available_only=False).
    assert captured == {
        "tier": None,
        "provider": None,
        "purpose": None,
        "available_only": False,
    }


def test_routing_models_http_route_forwards_filters(monkeypatch):
    gateway = _gateway_module()
    captured: dict = {}

    def fake_get(**kwargs):
        captured.update(kwargs)
        return _sample_routing_payload()

    monkeypatch.setattr("services.core.get_routing_models", fake_get)

    response = anyio.run(
        partial(
            _request,
            gateway.app,
            "GET",
            "/control-plane/routing/models",
            params={
                "tier": "local",
                "provider": "local",
                "purpose": "local_assist",
                "available_only": "true",
            },
        )
    )

    assert response.status_code == 200
    assert captured == {
        "tier": "local",
        "provider": "local",
        "purpose": "local_assist",
        "available_only": True,
    }


def test_routing_models_http_route_surfaces_invalid_filter_as_400(monkeypatch):
    gateway = _gateway_module()
    monkeypatch.setattr(
        "services.core.get_routing_models",
        lambda **_: {
            "error": "invalid_tier",
            "detail": "Unknown tier 'xxl'. Valid: local, small, medium, large",
        },
    )

    response = anyio.run(
        partial(
            _request,
            gateway.app,
            "GET",
            "/control-plane/routing/models",
            params={"tier": "xxl"},
        )
    )

    assert response.status_code == 400
    assert "xxl" in response.json()["detail"]


def test_routing_models_http_route_returns_real_catalog():
    """End-to-end smoke against the real services/core.get_routing_models path.

    Guards the wiring from api_gateway → services.core → DEFAULT_MODELS
    without stubbing, so a future schema drift (e.g. a new required key
    on ModelDescriptor) surfaces here instead of only in unit tests.
    """
    gateway = _gateway_module()
    response = anyio.run(
        _request, gateway.app, "GET", "/control-plane/routing/models"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["catalog_size"] >= 1
    assert payload["total"] == payload["catalog_size"]
    # Every entry must carry the stable-schema lineage + energy keys.
    for model in payload["models"]:
        assert "quantization" in model
        assert "distillation" in model
        assert "energy_profile" in model
    # DEFAULT_MODELS honesty rule: no baked-in energy profile.
    assert all(m["energy_profile"] is None for m in payload["models"])
