import importlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


class DummyRegistry:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def deploy(self, config):
        return {"ok": config.get("id"), "endpoint": self.endpoint}


class DummyClient:
    def dispatch_task(self, ctx):
        return {"task": ctx.task_context.description}


class DummyOptimizer:
    async def evaluate_agent(self, aid):
        return {"aid": aid}


class DummyModelManager:
    async def load_model(self, name, typ, source, config, version=None):
        return {"name": name, "source": source}


class DummyArgs:
    pass


sys.modules.setdefault(
    "sdk.client", types.SimpleNamespace(AgentClient=lambda: DummyClient())
)
sys.modules.setdefault(
    "agentnn.deployment.agent_registry",
    types.SimpleNamespace(AgentRegistry=DummyRegistry),
)
sys.modules.setdefault(
    "managers.agent_optimizer",
    types.SimpleNamespace(AgentOptimizer=lambda: DummyOptimizer()),
)
sys.modules.setdefault(
    "managers.model_manager",
    types.SimpleNamespace(ModelManager=lambda: DummyModelManager()),
)
sys.modules.setdefault("training.train", types.SimpleNamespace(train=lambda x: 1))
sys.modules.setdefault(
    "core.model_context", types.SimpleNamespace(ModelContext=SimpleNamespace)
)

core = importlib.import_module("services.core")


def test_create_agent():
    result = core.create_agent({"id": "demo"}, endpoint="http://x")
    assert result == {"ok": "demo", "endpoint": "http://x"}


def test_dispatch_task():
    ctx = SimpleNamespace(task_context=SimpleNamespace(description="hi", task_type="chat"))
    result = core.dispatch_task(ctx)
    assert result["task"] == "hi"


def test_evaluate_agent():
    result = core.evaluate_agent("a1")
    assert result["aid"] == "a1"


def test_load_model():
    result = core.load_model("m", "t", "s", {})
    assert result["name"] == "m"


def test_train_model(monkeypatch):
    called = {}

    def dummy(args):
        called["ok"] = True
        return 1

    monkeypatch.setattr(sys.modules["training.train"], "train", dummy)
    result = core.train_model(DummyArgs())
    assert called.get("ok")
    assert result == 1
