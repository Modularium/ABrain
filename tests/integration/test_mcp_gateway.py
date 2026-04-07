import importlib.util
import pathlib
import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient


spec = importlib.util.spec_from_file_location(
    "mcp_gateway", pathlib.Path("agentnn/mcp/mcp_gateway.py")
)
mcp_gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp_gateway)  # type: ignore


def test_gateway_rejects_legacy_tool_proxy():
    app = mcp_gateway.create_gateway()
    client = TestClient(app)

    response = client.post(
        "/v1/mcp/tool/use",
        json={"tool_name": "filesystem", "input": {"action": "read"}},
    )

    assert response.status_code == 410
    assert response.json()["detail"]["error_code"] == "legacy_tool_proxy_disabled"
