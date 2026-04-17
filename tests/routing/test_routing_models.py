"""Tests for Phase 4 M1: ModelDescriptor and related Pydantic models.

Coverage:
1. ModelDescriptor — happy path, all required fields
2. ModelDescriptor — empty model_id / display_name rejected
3. ModelDescriptor — empty purposes list rejected
4. ModelDescriptor — purposes deduplication
5. ModelDescriptor — LOCAL tier with cost raises
6. ModelDescriptor — LOCAL tier without cost succeeds
7. ModelDescriptor — extra fields rejected
8. ModelDescriptor — all ModelPurpose values accepted
9. ModelDescriptor — all ModelTier values accepted
10. ModelDescriptor — all ModelProvider values accepted
11. ModelDescriptor — optional fields default correctly
"""

from __future__ import annotations

import pytest

from core.routing.models import (
    ModelDescriptor,
    ModelProvider,
    ModelPurpose,
    ModelTier,
)

pytestmark = pytest.mark.unit


def _desc(**kwargs) -> ModelDescriptor:
    defaults = {
        "model_id": "test-model",
        "display_name": "Test Model",
        "provider": ModelProvider.ANTHROPIC,
        "purposes": [ModelPurpose.PLANNING],
        "tier": ModelTier.LARGE,
    }
    defaults.update(kwargs)
    return ModelDescriptor.model_validate(defaults)


class TestModelDescriptorHappyPath:
    def test_minimal_valid_descriptor(self):
        d = _desc()
        assert d.model_id == "test-model"
        assert d.provider == ModelProvider.ANTHROPIC
        assert ModelPurpose.PLANNING in d.purposes

    def test_model_id_is_stripped(self):
        d = _desc(model_id="  my-model  ")
        assert d.model_id == "my-model"

    def test_display_name_is_stripped(self):
        d = _desc(display_name="  My Model  ")
        assert d.display_name == "My Model"

    def test_optional_fields_default_none(self):
        d = _desc()
        assert d.context_window is None
        assert d.cost_per_1k_tokens is None
        assert d.p95_latency_ms is None
        assert d.notes is None

    def test_defaults_supports_tool_use_false(self):
        assert _desc().supports_tool_use is False

    def test_defaults_supports_structured_output_false(self):
        assert _desc().supports_structured_output is False

    def test_defaults_is_available_true(self):
        assert _desc().is_available is True

    def test_full_descriptor_accepted(self):
        d = _desc(
            context_window=200000,
            cost_per_1k_tokens=0.015,
            p95_latency_ms=1200,
            supports_tool_use=True,
            supports_structured_output=True,
            notes="Production flagship model",
        )
        assert d.context_window == 200000
        assert d.cost_per_1k_tokens == 0.015


class TestModelDescriptorValidation:
    def test_empty_model_id_raises(self):
        with pytest.raises(Exception):
            _desc(model_id="")

    def test_whitespace_model_id_raises(self):
        with pytest.raises(Exception):
            _desc(model_id="   ")

    def test_empty_display_name_raises(self):
        with pytest.raises(Exception):
            _desc(display_name="")

    def test_empty_purposes_raises(self):
        with pytest.raises(Exception):
            _desc(purposes=[])

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            _desc(unknown_field="x")

    def test_local_tier_with_cost_raises(self):
        with pytest.raises(Exception):
            _desc(tier=ModelTier.LOCAL, cost_per_1k_tokens=0.001)

    def test_local_tier_without_cost_succeeds(self):
        d = _desc(tier=ModelTier.LOCAL, provider=ModelProvider.LOCAL)
        assert d.tier == ModelTier.LOCAL
        assert d.cost_per_1k_tokens is None

    def test_purposes_deduplication(self):
        d = _desc(purposes=[ModelPurpose.PLANNING, ModelPurpose.PLANNING])
        assert d.purposes.count(ModelPurpose.PLANNING) == 1

    def test_multiple_purposes_preserved_in_order(self):
        purposes = [ModelPurpose.PLANNING, ModelPurpose.CLASSIFICATION]
        d = _desc(purposes=purposes)
        assert d.purposes == purposes


class TestEnumCoverage:
    def test_all_purposes_accepted(self):
        for purpose in ModelPurpose:
            d = _desc(purposes=[purpose])
            assert purpose in d.purposes

    def test_all_tiers_accepted_non_local(self):
        for tier in [ModelTier.SMALL, ModelTier.MEDIUM, ModelTier.LARGE]:
            d = _desc(tier=tier, cost_per_1k_tokens=0.01)
            assert d.tier == tier

    def test_all_providers_accepted(self):
        for provider in ModelProvider:
            tier = ModelTier.LOCAL if provider == ModelProvider.LOCAL else ModelTier.MEDIUM
            cost = None if tier == ModelTier.LOCAL else 0.01
            d = _desc(provider=provider, tier=tier, cost_per_1k_tokens=cost)
            assert d.provider == provider
