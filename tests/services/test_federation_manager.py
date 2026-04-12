import pytest
from unittest.mock import patch

from services.federation_manager.service import FederationManagerService

pytestmark = pytest.mark.unit
from core.model_context import ModelContext


class DummyResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_round_robin_dispatch(monkeypatch):
    svc = FederationManagerService()
    svc.register_node("n1", "http://node1")
    svc.register_node("n2", "http://node2")

    def fake_post(url, json=None, timeout=None):
        return DummyResp(json)

    with patch("httpx.Client.post", side_effect=fake_post):
        ctx = ModelContext(task="t")
        r1 = svc.dispatch(None, ctx)
        r2 = svc.dispatch(None, ctx)

    assert r1.task == "t"
    assert r2.task == "t"
    assert svc.nodes["n1"].tasks_sent == 1
    assert svc.nodes["n2"].tasks_sent == 1
