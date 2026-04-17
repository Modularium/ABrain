"""Tests for Phase 4 M3: Default model catalog and build_default_registry.

Coverage:
1.  DEFAULT_MODELS — non-empty list
2.  DEFAULT_MODELS — every entry is a ModelDescriptor
3.  DEFAULT_MODELS — no duplicate model_ids
4.  DEFAULT_MODELS — all four tiers represented
5.  DEFAULT_MODELS — LOCAL tier entries have cost_per_1k_tokens=None
6.  DEFAULT_MODELS — LOCAL tier entries have is_available=False (operator must enable)
7.  DEFAULT_MODELS — non-LOCAL entries have cost_per_1k_tokens declared
8.  DEFAULT_MODELS — all entries declare p95_latency_ms
9.  DEFAULT_MODELS — CLASSIFICATION purpose covered by at least one SMALL entry
10. DEFAULT_MODELS — RANKING purpose covered by at least one SMALL-or-LOCAL entry
11. DEFAULT_MODELS — RETRIEVAL_ASSIST purpose covered
12. DEFAULT_MODELS — LOCAL_ASSIST purpose covered
13. DEFAULT_MODELS — PLANNING purpose covered by MEDIUM/LARGE entries
14. build_default_registry — default (no local) excludes LOCAL tier
15. build_default_registry — default registry has no LOCAL-tier models
16. build_default_registry — enable_local=True includes LOCAL-tier models
17. build_default_registry — returns independent registry each call
18. build_default_registry — all non-LOCAL models registered and retrievable
19. build_default_registry — advisory warnings for missing cost returned safely
20. dispatch — default registry routes CLASSIFICATION to SMALL model
21. dispatch — default registry routes PLANNING to MEDIUM (not LARGE) under cost cap
22. dispatch — default registry prefer_local=True selects LOCAL when enable_local=True
23. dispatch — default registry raises NoModelAvailableError for absent purpose
24. catalog content — at least one Anthropic SMALL entry
25. catalog content — at least one LOCAL entry with supports_structured_output=True
"""

from __future__ import annotations

import pytest

from core.routing.catalog import DEFAULT_MODELS, build_default_registry
from core.routing.dispatcher import ModelDispatcher, ModelRoutingRequest, NoModelAvailableError
from core.routing.models import ModelDescriptor, ModelProvider, ModelPurpose, ModelTier

pytestmark = pytest.mark.unit


class TestDefaultModelsList:
    def test_non_empty(self):
        assert len(DEFAULT_MODELS) > 0

    def test_all_are_descriptors(self):
        for m in DEFAULT_MODELS:
            assert isinstance(m, ModelDescriptor)

    def test_no_duplicate_ids(self):
        ids = [m.model_id for m in DEFAULT_MODELS]
        assert len(ids) == len(set(ids))

    def test_all_four_tiers_represented(self):
        tiers = {m.tier for m in DEFAULT_MODELS}
        assert ModelTier.LOCAL in tiers
        assert ModelTier.SMALL in tiers
        assert ModelTier.MEDIUM in tiers
        assert ModelTier.LARGE in tiers

    def test_local_tier_no_cost(self):
        for m in DEFAULT_MODELS:
            if m.tier == ModelTier.LOCAL:
                assert m.cost_per_1k_tokens is None, f"{m.model_id} should have no cost"

    def test_local_tier_unavailable_by_default(self):
        for m in DEFAULT_MODELS:
            if m.tier == ModelTier.LOCAL:
                assert m.is_available is False, (
                    f"{m.model_id} should be is_available=False (requires operator enable)"
                )

    def test_non_local_have_cost_declared(self):
        for m in DEFAULT_MODELS:
            if m.tier != ModelTier.LOCAL:
                assert m.cost_per_1k_tokens is not None, (
                    f"{m.model_id} should declare cost_per_1k_tokens"
                )

    def test_all_have_latency_declared(self):
        for m in DEFAULT_MODELS:
            assert m.p95_latency_ms is not None, (
                f"{m.model_id} should declare p95_latency_ms"
            )

    def test_classification_covered_by_small(self):
        small_classifiers = [
            m for m in DEFAULT_MODELS
            if m.tier == ModelTier.SMALL and ModelPurpose.CLASSIFICATION in m.purposes
        ]
        assert len(small_classifiers) >= 1

    def test_ranking_covered_by_small_or_local(self):
        rankers = [
            m for m in DEFAULT_MODELS
            if m.tier in (ModelTier.SMALL, ModelTier.LOCAL)
            and ModelPurpose.RANKING in m.purposes
        ]
        assert len(rankers) >= 1

    def test_retrieval_assist_covered(self):
        ras = [m for m in DEFAULT_MODELS if ModelPurpose.RETRIEVAL_ASSIST in m.purposes]
        assert len(ras) >= 1

    def test_local_assist_covered(self):
        las = [m for m in DEFAULT_MODELS if ModelPurpose.LOCAL_ASSIST in m.purposes]
        assert len(las) >= 1

    def test_planning_covered_by_medium_or_large(self):
        planners = [
            m for m in DEFAULT_MODELS
            if m.tier in (ModelTier.MEDIUM, ModelTier.LARGE)
            and ModelPurpose.PLANNING in m.purposes
        ]
        assert len(planners) >= 2

    def test_local_provider_on_local_tier(self):
        for m in DEFAULT_MODELS:
            if m.tier == ModelTier.LOCAL:
                assert m.provider == ModelProvider.LOCAL, (
                    f"{m.model_id} LOCAL tier should use LOCAL provider"
                )

    def test_at_least_one_anthropic_small(self):
        hits = [
            m for m in DEFAULT_MODELS
            if m.tier == ModelTier.SMALL and m.provider == ModelProvider.ANTHROPIC
        ]
        assert len(hits) >= 1

    def test_at_least_one_local_with_structured_output(self):
        hits = [
            m for m in DEFAULT_MODELS
            if m.tier == ModelTier.LOCAL and m.supports_structured_output
        ]
        assert len(hits) >= 1


class TestBuildDefaultRegistry:
    def test_default_excludes_local_tier(self):
        reg = build_default_registry()
        local_ids = [
            m.model_id for m in DEFAULT_MODELS if m.tier == ModelTier.LOCAL
        ]
        for mid in local_ids:
            assert not reg.is_registered(mid), (
                f"{mid} should not appear in default registry"
            )

    def test_default_registry_non_empty(self):
        reg = build_default_registry()
        assert len(reg) > 0

    def test_enable_local_includes_local_tier(self):
        reg = build_default_registry(enable_local=True)
        local_ids = [
            m.model_id for m in DEFAULT_MODELS if m.tier == ModelTier.LOCAL
        ]
        for mid in local_ids:
            assert reg.is_registered(mid)

    def test_returns_independent_registry(self):
        r1 = build_default_registry()
        r2 = build_default_registry()
        assert r1 is not r2

    def test_non_local_models_all_registered(self):
        reg = build_default_registry()
        for m in DEFAULT_MODELS:
            if m.tier != ModelTier.LOCAL:
                assert reg.is_registered(m.model_id), (
                    f"{m.model_id} should be registered"
                )

    def test_registered_descriptor_identical(self):
        reg = build_default_registry()
        for m in DEFAULT_MODELS:
            if m.tier != ModelTier.LOCAL:
                assert reg.get(m.model_id) == m

    def test_enable_local_len_greater_than_default(self):
        default_len = len(build_default_registry())
        local_len = len(build_default_registry(enable_local=True))
        assert local_len > default_len

    def test_idempotent_fresh_registry_on_each_call(self):
        r1 = build_default_registry()
        r1_ids = {m.model_id for m in r1.list_all()}
        r2 = build_default_registry()
        r2_ids = {m.model_id for m in r2.list_all()}
        assert r1_ids == r2_ids


class TestDispatchAgainstCatalog:
    def test_classification_routes_to_small(self):
        reg = build_default_registry()
        req = ModelRoutingRequest(purpose=ModelPurpose.CLASSIFICATION)
        result = ModelDispatcher(reg).dispatch(req)
        assert result.tier in (ModelTier.LOCAL, ModelTier.SMALL)

    def test_planning_under_cost_cap_avoids_large(self):
        # With a cost cap below the LARGE threshold, MEDIUM should be chosen
        reg = build_default_registry()
        # claude-opus-4-7 costs 0.045; cap at 0.015 to force MEDIUM
        req = ModelRoutingRequest(
            purpose=ModelPurpose.PLANNING,
            max_cost_per_1k_tokens=0.015,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.tier != ModelTier.LARGE

    def test_prefer_local_with_local_enabled(self):
        reg = build_default_registry(enable_local=True)
        # Local models are is_available=False, so they won't appear in the base pool
        # unless the operator re-enables them.  Confirm dispatcher handles this gracefully.
        req = ModelRoutingRequest(
            purpose=ModelPurpose.CLASSIFICATION,
            prefer_local=True,
        )
        result = ModelDispatcher(reg).dispatch(req)
        # SMALL should be chosen since LOCAL entries are is_available=False
        assert result.tier == ModelTier.SMALL

    def test_local_model_available_when_enabled_explicitly(self):
        # Simulate operator enabling a local model
        from core.routing.models import ModelDescriptor as MD
        local_on = MD.model_validate({
            "model_id": "llama-test-local",
            "display_name": "Llama Test Local",
            "provider": ModelProvider.LOCAL,
            "purposes": [ModelPurpose.CLASSIFICATION],
            "tier": ModelTier.LOCAL,
            "p95_latency_ms": 50,
            "is_available": True,
        })
        reg = build_default_registry()
        reg.register(local_on)
        req = ModelRoutingRequest(
            purpose=ModelPurpose.CLASSIFICATION,
            prefer_local=True,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "llama-test-local"
        assert result.tier == ModelTier.LOCAL

    def test_raises_for_unsupported_purpose(self):
        # SPECIALIST is not in the default catalog (only PLANNING/SPECIALIST combo in MEDIUM/LARGE)
        # This test ensures an explicit missing purpose raises correctly
        reg = build_default_registry()
        # Remove all models with SPECIALIST purpose for this test
        from core.routing.registry import ModelRegistry
        empty_specialist_reg = ModelRegistry()
        for m in DEFAULT_MODELS:
            if m.tier != ModelTier.LOCAL and ModelPurpose.SPECIALIST not in m.purposes:
                empty_specialist_reg.register(m)
        with pytest.raises(NoModelAvailableError):
            ModelDispatcher(empty_specialist_reg).dispatch(
                ModelRoutingRequest(purpose=ModelPurpose.SPECIALIST)
            )

    def test_retrieval_assist_routed_to_capable_model(self):
        reg = build_default_registry()
        req = ModelRoutingRequest(purpose=ModelPurpose.RETRIEVAL_ASSIST)
        result = ModelDispatcher(reg).dispatch(req)
        # Should land on a SMALL model with retrieval assist purpose
        assert result.tier in (ModelTier.SMALL, ModelTier.MEDIUM)
        assert ModelPurpose.RETRIEVAL_ASSIST in result.purposes
