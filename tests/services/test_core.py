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
        description = ctx.task_context.description
        return {"task": getattr(description, "text", description)}


class DummyOptimizer:
    async def evaluate_agent(self, aid):
        return {"aid": aid}


class DummyModelManager:
    async def load_model(self, name, typ, source, config, version=None):
        return {"name": name, "source": source}


class DummyArgs:
    pass


@pytest.fixture
def core(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "sdk.client",
        types.SimpleNamespace(AgentClient=lambda: DummyClient()),
    )
    monkeypatch.setitem(
        sys.modules,
        "agentnn.deployment.agent_registry",
        types.SimpleNamespace(AgentRegistry=DummyRegistry),
    )
    monkeypatch.setitem(
        sys.modules,
        "managers.agent_optimizer",
        types.SimpleNamespace(AgentOptimizer=lambda: DummyOptimizer()),
    )
    monkeypatch.setitem(
        sys.modules,
        "managers.model_manager",
        types.SimpleNamespace(ModelManager=lambda: DummyModelManager()),
    )
    monkeypatch.setitem(
        sys.modules,
        "training.train",
        types.SimpleNamespace(train=lambda x: 1),
    )
    monkeypatch.setitem(
        sys.modules,
        "core.model_context",
        types.SimpleNamespace(
            ModelContext=SimpleNamespace,
            TaskContext=SimpleNamespace,
        ),
    )
    sys.modules.pop("services.core", None)
    return importlib.import_module("services.core")


def test_create_agent(core):
    result = core.create_agent({"id": "demo"}, endpoint="http://x")
    assert result == {"ok": "demo", "endpoint": "http://x"}


def test_dispatch_task(core):
    ctx = SimpleNamespace(task_context=SimpleNamespace(description="hi", task_type="chat"))
    result = core.dispatch_task(ctx)
    assert result["task"] == "hi"


def test_evaluate_agent(core):
    result = core.evaluate_agent("a1")
    assert result["aid"] == "a1"


def test_load_model(core):
    result = core.load_model("m", "t", "s", {})
    assert result["name"] == "m"


def test_train_model(core, monkeypatch):
    called = {}

    def dummy(args):
        called["ok"] = True
        return 1

    monkeypatch.setattr(sys.modules["training.train"], "train", dummy)
    result = core.train_model(DummyArgs())
    assert called.get("ok")
    assert result == 1
