"""Tests for Phase 4 M1: ModelRegistry.

Coverage:
1. register — happy path, idempotent, conflict detection
2. register — advisory warnings: missing cost, missing latency
3. deregister — removes descriptor; raises KeyError for unknown id
4. get — returns descriptor; raises KeyError for unknown id
5. is_registered — True/False logic
6. list_all — insertion order preserved
7. list_available — filters by is_available
8. list_by_purpose — filters correctly, multi-purpose models included
9. list_by_tier — filters correctly
10. list_by_provider — filters correctly
11. __len__ — counts correctly
"""

from __future__ import annotations

import pytest

from core.routing.models import (
    ModelDescriptor,
    ModelProvider,
    ModelPurpose,
    ModelTier,
)
from core.routing.registry import ModelRegistry, RegistrationError

pytestmark = pytest.mark.unit


def _desc(
    model_id: str = "m-test",
    purposes: list[ModelPurpose] | None = None,
    tier: ModelTier = ModelTier.LARGE,
    provider: ModelProvider = ModelProvider.ANTHROPIC,
    cost: float | None = 0.015,
    latency: int | None = 1000,
    is_available: bool = True,
) -> ModelDescriptor:
    if tier == ModelTier.LOCAL:
        cost = None
    kwargs: dict = {
        "model_id": model_id,
        "display_name": model_id,
        "provider": provider,
        "purposes": purposes or [ModelPurpose.PLANNING],
        "tier": tier,
        "cost_per_1k_tokens": cost,
        "p95_latency_ms": latency,
        "is_available": is_available,
    }
    return ModelDescriptor.model_validate(kwargs)


def _registry() -> ModelRegistry:
    return ModelRegistry()


class TestRegisterHappyPath:
    def test_register_returns_list(self):
        reg = _registry()
        result = reg.register(_desc())
        assert isinstance(result, list)

    def test_idempotent_reregistration_returns_empty(self):
        reg = _registry()
        d = _desc()
        reg.register(d)
        assert reg.register(d) == []

    def test_idempotent_does_not_double_count(self):
        reg = _registry()
        d = _desc()
        reg.register(d)
        reg.register(d)
        assert len(reg) == 1

    def test_conflict_raises_registration_error(self):
        reg = _registry()
        reg.register(_desc(model_id="m1"))
        with pytest.raises(RegistrationError):
            reg.register(_desc(model_id="m1", tier=ModelTier.MEDIUM))

    def test_registration_error_mentions_model_id(self):
        reg = _registry()
        reg.register(_desc(model_id="m1"))
        with pytest.raises(RegistrationError, match="m1"):
            reg.register(_desc(model_id="m1", tier=ModelTier.MEDIUM))

    def test_registration_error_is_value_error(self):
        reg = _registry()
        reg.register(_desc(model_id="m1"))
        with pytest.raises(ValueError):
            reg.register(_desc(model_id="m1", tier=ModelTier.MEDIUM))


class TestAdvisoryWarnings:
    def test_no_warnings_for_fully_declared_model(self):
        reg = _registry()
        assert reg.register(_desc(cost=0.01, latency=500)) == []

    def test_missing_cost_warns_for_non_local(self):
        reg = _registry()
        warnings = reg.register(_desc(cost=None, latency=500))
        assert any("cost" in w.lower() for w in warnings)

    def test_local_tier_no_cost_no_cost_warning(self):
        reg = _registry()
        d = _desc(tier=ModelTier.LOCAL, provider=ModelProvider.LOCAL)
        warnings = reg.register(d)
        assert not any("cost" in w.lower() for w in warnings)

    def test_missing_latency_warns(self):
        reg = _registry()
        warnings = reg.register(_desc(latency=None))
        assert any("latency" in w.lower() for w in warnings)

    def test_missing_both_gives_two_warnings(self):
        reg = _registry()
        warnings = reg.register(_desc(cost=None, latency=None))
        assert len(warnings) == 2


class TestDeregister:
    def test_deregister_removes_model(self):
        reg = _registry()
        reg.register(_desc())
        reg.deregister("m-test")
        assert not reg.is_registered("m-test")

    def test_deregister_decrements_len(self):
        reg = _registry()
        reg.register(_desc(model_id="a"))
        reg.register(_desc(model_id="b"))
        reg.deregister("a")
        assert len(reg) == 1

    def test_deregister_unknown_raises_key_error(self):
        reg = _registry()
        with pytest.raises(KeyError):
            reg.deregister("nonexistent")

    def test_deregister_then_reregister(self):
        reg = _registry()
        d = _desc()
        reg.register(d)
        reg.deregister("m-test")
        reg.register(d)
        assert reg.is_registered("m-test")


class TestGet:
    def test_get_returns_descriptor(self):
        reg = _registry()
        d = _desc()
        reg.register(d)
        assert reg.get("m-test") == d

    def test_get_unknown_raises_key_error(self):
        reg = _registry()
        with pytest.raises(KeyError, match="m-test"):
            reg.get("m-test")


class TestIsRegistered:
    def test_true_when_registered(self):
        reg = _registry()
        reg.register(_desc())
        assert reg.is_registered("m-test") is True

    def test_false_when_not_registered(self):
        assert _registry().is_registered("m-test") is False

    def test_false_after_deregister(self):
        reg = _registry()
        reg.register(_desc())
        reg.deregister("m-test")
        assert reg.is_registered("m-test") is False


class TestListAll:
    def test_empty_registry_empty_list(self):
        assert _registry().list_all() == []

    def test_preserves_insertion_order(self):
        reg = _registry()
        ids = ["c", "a", "b"]
        for mid in ids:
            reg.register(_desc(model_id=mid))
        assert [d.model_id for d in reg.list_all()] == ids

    def test_returns_copy_not_internals(self):
        reg = _registry()
        reg.register(_desc())
        assert reg.list_all() is not reg.list_all()


class TestListAvailable:
    def test_filters_unavailable(self):
        reg = _registry()
        reg.register(_desc(model_id="on", is_available=True))
        reg.register(_desc(model_id="off", is_available=False))
        available = [d.model_id for d in reg.list_available()]
        assert "on" in available
        assert "off" not in available

    def test_empty_when_all_unavailable(self):
        reg = _registry()
        reg.register(_desc(is_available=False))
        assert reg.list_available() == []


class TestListByPurpose:
    def test_filters_by_purpose(self):
        reg = _registry()
        reg.register(_desc(model_id="planner", purposes=[ModelPurpose.PLANNING]))
        reg.register(_desc(model_id="classifier", purposes=[ModelPurpose.CLASSIFICATION]))
        planners = reg.list_by_purpose(ModelPurpose.PLANNING)
        assert len(planners) == 1
        assert planners[0].model_id == "planner"

    def test_multi_purpose_model_returned_for_each(self):
        reg = _registry()
        reg.register(_desc(purposes=[ModelPurpose.PLANNING, ModelPurpose.CLASSIFICATION]))
        assert len(reg.list_by_purpose(ModelPurpose.PLANNING)) == 1
        assert len(reg.list_by_purpose(ModelPurpose.CLASSIFICATION)) == 1

    def test_empty_list_for_absent_purpose(self):
        reg = _registry()
        reg.register(_desc(purposes=[ModelPurpose.PLANNING]))
        assert reg.list_by_purpose(ModelPurpose.RANKING) == []


class TestListByTier:
    def test_filters_by_tier(self):
        reg = _registry()
        reg.register(_desc(model_id="large", tier=ModelTier.LARGE))
        reg.register(_desc(model_id="small", tier=ModelTier.SMALL, cost=0.001))
        assert [d.model_id for d in reg.list_by_tier(ModelTier.LARGE)] == ["large"]
        assert [d.model_id for d in reg.list_by_tier(ModelTier.SMALL)] == ["small"]


class TestListByProvider:
    def test_filters_by_provider(self):
        reg = _registry()
        reg.register(_desc(model_id="claude", provider=ModelProvider.ANTHROPIC))
        reg.register(_desc(model_id="gpt", provider=ModelProvider.OPENAI))
        assert [d.model_id for d in reg.list_by_provider(ModelProvider.ANTHROPIC)] == ["claude"]

    def test_empty_for_absent_provider(self):
        reg = _registry()
        reg.register(_desc(provider=ModelProvider.ANTHROPIC))
        assert reg.list_by_provider(ModelProvider.GOOGLE) == []


class TestLen:
    def test_empty_is_zero(self):
        assert len(_registry()) == 0

    def test_increments_on_register(self):
        reg = _registry()
        reg.register(_desc(model_id="a"))
        reg.register(_desc(model_id="b"))
        assert len(reg) == 2

    def test_decrements_on_deregister(self):
        reg = _registry()
        reg.register(_desc())
        reg.deregister("m-test")
        assert len(reg) == 0

    def test_idempotent_register_stable(self):
        reg = _registry()
        d = _desc()
        reg.register(d)
        reg.register(d)
        assert len(reg) == 1
