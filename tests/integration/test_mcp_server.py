import importlib.util
import pathlib
import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

spec = importlib.util.spec_from_file_location(
    "mcp_server", pathlib.Path("agentnn/mcp/mcp_server.py")
)
mcp_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp_server)  # type: ignore


class DummyConnector:
    def __init__(self, *_: object, **__: object) -> None:
        pass

    async def post(self, path: str, json: dict) -> dict:
        return {"echo": path, **json}

    async def get(self, path: str) -> dict:
        return {"path": path, "context": []}

@pytest.mark.unit
def test_execute_roundtrip(monkeypatch):
    monkeypatch.setattr(mcp_server, "ServiceConnector", DummyConnector)
    app = mcp_server.create_app()
    client = TestClient(app)

    ctx = {"task": "demo"}
    resp = client.post("/v1/mcp/execute", json=ctx)
    assert resp.status_code == 200
    data = resp.json()
    assert data["echo"] == "/dispatch"

    resp = client.post("/v1/mcp/context", json=ctx)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = client.get("/v1/mcp/context/123")
    assert resp.status_code == 200
    assert resp.json()["path"] == "/context/123"


@pytest.mark.unit
def test_extended_routes(monkeypatch):
    monkeypatch.setattr(mcp_server, "ServiceConnector", DummyConnector)
    app = mcp_server.create_app()
    client = TestClient(app)

    ctx = {"task": "demo"}
    resp = client.post("/v1/mcp/task/execute", json=ctx)
    assert resp.status_code == 200
    assert resp.json()["echo"] == "/dispatch"

    resp = client.post("/v1/mcp/context/save", json=ctx)
    assert resp.status_code == 200

    resp = client.get("/v1/mcp/context/load/sid1")
    assert resp.status_code == 200

    resp = client.get("/v1/mcp/context/history")
    assert resp.status_code == 200

    resp = client.get("/v1/mcp/context/get/42")
    assert resp.status_code == 200
    assert resp.json()["path"] == "/context/42"

    resp = client.post("/v1/mcp/agent/create", json={"name": "demo"})
    assert resp.status_code == 200
    assert resp.json()["echo"] == "/register"

    resp = client.post(
        "/v1/mcp/tool/use",
        json={"tool_name": "t", "input": {}, "context": {}},
    )
    assert resp.status_code == 410
    assert resp.json()["detail"]["error_code"] == "legacy_tool_proxy_disabled"
