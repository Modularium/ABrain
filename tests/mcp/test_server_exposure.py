import pytest
import sys
import types

sys.modules.setdefault(
    "mlflow",
    types.SimpleNamespace(
        start_run=lambda *a, **k: None,
        set_tag=lambda *a, **k: None,
        log_param=lambda *a, **k: None,
        log_metric=lambda *a, **k: None,
        set_tracking_uri=lambda *a, **k: None,
        tracking=types.SimpleNamespace(
            MlflowClient=lambda: types.SimpleNamespace(
                list_experiments=lambda: [],
                get_run=lambda run_id: types.SimpleNamespace(
                    info=types.SimpleNamespace(run_id=run_id, status="FINISHED"),
                    data=types.SimpleNamespace(metrics={}, params={}),
                ),
            )
        ),
    ),
)

from agentnn.mcp import mcp_server  # noqa: E402
@pytest.mark.unit
def test_server_routes_expose_legacy_disabled_status():
    app = mcp_server.create_app()
    routes = {route.path for route in app.routes}

    assert "/v1/mcp/ping" in routes
    assert "/v1/mcp/context/map" in routes
    assert "/v1/mcp/agent/list" in routes
