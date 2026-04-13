import importlib
import sys

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

pytestmark = pytest.mark.unit


def _gateway_module():
    sys.modules.pop("api_gateway.main", None)
    return importlib.import_module("api_gateway.main")


def test_docs_endpoints_are_available():
    gateway = _gateway_module()
    client = TestClient(gateway.app)

    docs_response = client.get("/docs")
    redoc_response = client.get("/redoc")
    openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text
    assert redoc_response.status_code == 200
    assert "ReDoc" in redoc_response.text
    assert openapi_response.status_code == 200


def test_openapi_exposes_only_canonical_control_plane_surface():
    gateway = _gateway_module()
    client = TestClient(gateway.app)

    payload = client.get("/openapi.json").json()
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

    assert "/chat" not in paths
    assert "/chat/feedback" not in paths
    assert "/sessions" not in paths
    assert "/agents" not in paths
    assert "/llm/generate" not in paths
    assert "/embed" not in paths
    assert "/metrics" not in paths

    tags = {tag["name"] for tag in payload["tags"]}
    assert {"Control Plane", "Agents", "Traces", "Approvals", "Plans", "Tasks"} <= tags


def test_openapi_documents_control_plane_request_and_response_models():
    gateway = _gateway_module()
    client = TestClient(gateway.app)

    payload = client.get("/openapi.json").json()
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
    client = TestClient(gateway.app)

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

    response = client.get("/control-plane/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["agent_count"] == 1
    assert payload["agents"][0]["agent_id"] == "agent-1"
    assert payload["recent_governance"][0]["effect"] == "allow"


def test_control_plane_task_run_http_route_returns_documented_shape(monkeypatch):
    gateway = _gateway_module()
    client = TestClient(gateway.app)

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

    response = client.post(
        "/control-plane/tasks/run",
        json={
            "task_type": "system_status",
            "description": "Check system health",
            "input_data": {},
            "options": {"timeout": 5},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["selected_agent_id"] == "adminbot-agent"
    assert payload["execution"]["success"] is True
    assert payload["trace"]["trace_id"] == "trace-task-1"
