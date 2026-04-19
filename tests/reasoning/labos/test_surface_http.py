"""HTTP surface tests — `POST /control-plane/reasoning/labos/<mode>`.

Pin that the control-plane endpoints delegate verbatim to
`services.core.run_labos_reasoning` and translate invalid contexts to
HTTP 400.  No parallel reasoning logic in the gateway.
"""

from __future__ import annotations

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
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.request(method, path, **kwargs)


_MODES = (
    "reactor_daily_overview",
    "incident_review",
    "maintenance_suggestions",
    "schedule_runtime_review",
    "cross_domain_overview",
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


class TestHttpRouting:
    def test_all_five_modes_are_registered(self):
        gateway = _gateway_module()
        payload = anyio.run(_request, gateway.app, "GET", "/openapi.json").json()
        paths = payload["paths"]
        for mode in _MODES:
            assert f"/control-plane/reasoning/labos/{mode}" in paths
            op = paths[f"/control-plane/reasoning/labos/{mode}"]["post"]
            assert "Reasoning" in op.get("tags", [])

    @pytest.mark.parametrize("mode", _MODES)
    def test_endpoint_delegates_to_service(self, monkeypatch, mode):
        gateway = _gateway_module()
        captured: dict = {}

        def fake(mode_arg, context_arg):
            captured["mode"] = mode_arg
            captured["context"] = context_arg
            return _ok_payload(mode_arg)

        monkeypatch.setattr("services.core.run_labos_reasoning", fake)

        ctx = {"reactors": [{"reactor_id": "R1", "status": "warning"}]}
        response = anyio.run(
            partial(
                _request,
                gateway.app,
                "POST",
                f"/control-plane/reasoning/labos/{mode}",
                json={"context": ctx},
            )
        )

        assert response.status_code == 200
        assert captured == {"mode": mode, "context": ctx}
        assert response.json()["reasoning_mode"] == f"labos_{mode}"

    def test_invalid_context_surfaces_as_400(self, monkeypatch):
        gateway = _gateway_module()
        monkeypatch.setattr(
            "services.core.run_labos_reasoning",
            lambda mode, ctx: {
                "error": "invalid_context",
                "detail": [{"loc": "incidents", "msg": "bad"}],
            },
        )
        response = anyio.run(
            partial(
                _request,
                gateway.app,
                "POST",
                "/control-plane/reasoning/labos/incident_review",
                json={"context": {"incidents": [{"bogus": 1}]}},
            )
        )
        assert response.status_code == 400

    def test_request_body_extra_keys_rejected(self):
        gateway = _gateway_module()
        response = anyio.run(
            partial(
                _request,
                gateway.app,
                "POST",
                "/control-plane/reasoning/labos/reactor_daily_overview",
                json={"context": {}, "unknown": 1},
            )
        )
        # Pydantic model_config(extra="forbid") → 422
        assert response.status_code == 422


class TestHttpRealService:
    def test_reactor_daily_overview_against_real_service(self):
        gateway = _gateway_module()
        response = anyio.run(
            partial(
                _request,
                gateway.app,
                "POST",
                "/control-plane/reasoning/labos/reactor_daily_overview",
                json={
                    "context": {
                        "reactors": [
                            {"reactor_id": "R1", "status": "warning"}
                        ]
                    }
                },
            )
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["reasoning_mode"] == "labos_reactor_daily_overview"
        # All Response Shape V2 keys present.
        for key in (
            "summary", "highlights", "prioritized_entities",
            "recommended_actions", "recommended_checks",
            "approval_required_actions", "blocked_or_deferred_actions",
            "used_context_sections", "trace_metadata",
        ):
            assert key in payload
