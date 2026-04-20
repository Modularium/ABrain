"""Integration tests for ``services.core.decide_strategy`` and the API route."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from core.audit import TraceStore
from core.audit.event_types import DECISION_CREATED


pytestmark = pytest.mark.unit


def test_decide_strategy_persists_decision_in_trace_metadata(tmp_path) -> None:
    core = importlib.import_module("services.core")
    store = TraceStore(tmp_path / "decide_trace.sqlite3")

    result = core.decide_strategy(
        {"task_type": "system_status", "description": "health check"},
        trace_store=store,
    )

    assert result["decision"]["selected_strategy"] == "direct_execution"
    assert result["decision"]["allowed"] is True
    assert result["decision"]["requires_approval"] is False

    trace_id = result["trace"]["trace_id"]
    snapshot = store.get_trace(trace_id)
    assert snapshot is not None
    assert snapshot.trace.status == "completed"
    stored = snapshot.trace.metadata.get("strategy_decision")
    assert stored is not None
    assert stored["selected_strategy"] == "direct_execution"
    assert stored["decision_id"] == result["decision"]["decision_id"]

    event_types = {
        event.event_type
        for span in snapshot.spans
        for event in span.events
    }
    assert DECISION_CREATED in event_types


def test_decide_strategy_does_not_execute_or_create_approvals(monkeypatch, tmp_path) -> None:
    core = importlib.import_module("services.core")
    store = TraceStore(tmp_path / "decide_trace.sqlite3")

    def _forbid(*args, **kwargs):  # pragma: no cover - invoked only on failure
        raise AssertionError("decide_strategy must be observable-only")

    monkeypatch.setattr("services.core.execute_tool", _forbid)

    result = core.decide_strategy(
        {"task_type": "system_status"},
        trace_store=store,
    )

    assert "execution" not in result
    assert "approval" not in result


def test_control_plane_decide_endpoint_returns_strategy_decision(monkeypatch) -> None:
    import api_gateway.main as gateway

    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    client = TestClient(gateway.app)

    response = client.post(
        "/control-plane/decide",
        json={
            "task_type": "system_status",
            "description": "smoke test",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"]["selected_strategy"] == "direct_execution"
    assert body["decision"]["allowed"] is True
    assert body["decision"]["requires_approval"] is False
    assert body["trace"].get("trace_id")
