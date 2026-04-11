import httpx
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

from agentnn.mcp.mcp_client import MCPClient  # noqa: E402
from core.model_context import ModelContext, TaskContext  # noqa: E402
@pytest.mark.unit
def test_client_exec_rejects_disabled_legacy_runtime():
    mcp = MCPClient("http://testserver")
    request = httpx.Request("POST", "http://testserver/v1/mcp/execute")
    response = httpx.Response(410, request=request)

    class DisabledLegacyClient:
        def post(self, path: str, json: dict):
            assert path == "/v1/mcp/execute"
            return response

    mcp._client = DisabledLegacyClient()  # type: ignore[assignment]

    ctx = ModelContext(task_context=TaskContext(task_type="chat", description="hi"))
    with pytest.raises(httpx.HTTPStatusError):
        mcp.execute(ctx)
