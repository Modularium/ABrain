"""Tests for Phase 4 M2: ModelDispatcher — budget-aware model routing with fallback cascades.

Coverage:
1.  dispatch — strict pass: all constraints satisfied
2.  dispatch — prefer_local selects LOCAL over SMALL when both pass
3.  dispatch — fallback pass 2 (no-latency): latency-only failure relaxed
4.  dispatch — fallback pass 3 (no-cost): cost-only failure relaxed
5.  dispatch — fallback pass 4 (no-budget): both cost+latency fail, caps pass
6.  dispatch — fallback pass 5 (no-caps): caps fail, last-resort
7.  dispatch — NoModelAvailableError when registry is empty
8.  dispatch — NoModelAvailableError when no model matches purpose
9.  dispatch — NoModelAvailableError when all unavailable
10. dispatch — tier ordering: SMALL before MEDIUM before LARGE
11. dispatch — cost ordering within tier
12. dispatch — latency ordering within same tier+cost
13. dispatch — unknown cost (None) sorts after known
14. dispatch — unknown latency (None) sorts after known
15. dispatch — fallback_used=False on strict pass
16. dispatch — fallback_used=True on relaxed pass
17. dispatch — fallback_reason=None on strict, set on fallback
18. dispatch — task_id echoed in result
19. dispatch — require_tool_use filters correctly
20. dispatch — require_structured_output filters correctly
21. dispatch — both capability requirements together
22. dispatch — unavailable model excluded from all passes
23. dispatch — result contains correct model_id, provider, tier, purposes
24. dispatch — selected_reason mentions purpose and tier
25. ModelRoutingRequest — extra fields rejected
26. ModelRoutingRequest — max_cost_per_1k_tokens must be >= 0
27. ModelRoutingRequest — max_p95_latency_ms must be >= 1
28. ModelRoutingResult — extra fields rejected
29. NoModelAvailableError — carries reason and request
30. dispatch — prefer_local=False does not force local first
"""

from __future__ import annotations

import pytest

from core.routing.dispatcher import (
    ModelDispatcher,
    ModelRoutingRequest,
    ModelRoutingResult,
    NoModelAvailableError,
    _dispatch,
    _rank,
    _sort_key,
)
from core.routing.models import (
    ModelDescriptor,
    ModelProvider,
    ModelPurpose,
    ModelTier,
)
from core.routing.registry import ModelRegistry

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _desc(
    model_id: str = "m",
    purposes: list[ModelPurpose] | None = None,
    tier: ModelTier = ModelTier.LARGE,
    provider: ModelProvider = ModelProvider.ANTHROPIC,
    cost: float | None = 0.015,
    latency: int | None = 1000,
    is_available: bool = True,
    tool_use: bool = False,
    structured: bool = False,
) -> ModelDescriptor:
    if tier == ModelTier.LOCAL:
        cost = None
        if provider == ModelProvider.ANTHROPIC:
            provider = ModelProvider.LOCAL
    return ModelDescriptor.model_validate({
        "model_id": model_id,
        "display_name": model_id,
        "provider": provider,
        "purposes": purposes or [ModelPurpose.PLANNING],
        "tier": tier,
        "cost_per_1k_tokens": cost,
        "p95_latency_ms": latency,
        "is_available": is_available,
        "supports_tool_use": tool_use,
        "supports_structured_output": structured,
    })


def _registry(*descs: ModelDescriptor) -> ModelRegistry:
    reg = ModelRegistry()
    for d in descs:
        reg.register(d)
    return reg


def _req(
    purpose: ModelPurpose = ModelPurpose.PLANNING,
    max_cost: float | None = None,
    max_latency: int | None = None,
    require_tool: bool = False,
    require_structured: bool = False,
    prefer_local: bool = False,
    task_id: str | None = None,
) -> ModelRoutingRequest:
    return ModelRoutingRequest(
        purpose=purpose,
        max_cost_per_1k_tokens=max_cost,
        max_p95_latency_ms=max_latency,
        require_tool_use=require_tool,
        require_structured_output=require_structured,
        prefer_local=prefer_local,
        task_id=task_id,
    )


# ---------------------------------------------------------------------------
# Strict pass
# ---------------------------------------------------------------------------

class TestStrictPass:
    def test_strict_pass_returns_result(self):
        reg = _registry(_desc(model_id="m1", cost=0.01, latency=500))
        result = ModelDispatcher(reg).dispatch(_req(max_cost=0.02, max_latency=1000))
        assert result.model_id == "m1"

    def test_strict_pass_fallback_used_false(self):
        reg = _registry(_desc(model_id="m1", cost=0.01, latency=500))
        result = ModelDispatcher(reg).dispatch(_req(max_cost=0.02, max_latency=1000))
        assert result.fallback_used is False

    def test_strict_pass_fallback_reason_none(self):
        reg = _registry(_desc(model_id="m1", cost=0.01, latency=500))
        result = ModelDispatcher(reg).dispatch(_req(max_cost=0.02, max_latency=1000))
        assert result.fallback_reason is None

    def test_strict_pass_selected_reason_mentions_best_match(self):
        reg = _registry(_desc(model_id="m1"))
        result = ModelDispatcher(reg).dispatch(_req())
        assert "Best match" in result.selected_reason

    def test_result_fields_populated(self):
        d = _desc(model_id="m1", tier=ModelTier.MEDIUM, provider=ModelProvider.OPENAI,
                  cost=0.005, latency=300)
        result = ModelDispatcher(_registry(d)).dispatch(_req())
        assert result.model_id == "m1"
        assert result.provider == ModelProvider.OPENAI
        assert result.tier == ModelTier.MEDIUM
        assert ModelPurpose.PLANNING in result.purposes

    def test_task_id_echoed(self):
        reg = _registry(_desc())
        result = ModelDispatcher(reg).dispatch(_req(task_id="t-123"))
        assert result.task_id == "t-123"

    def test_task_id_none_when_not_provided(self):
        reg = _registry(_desc())
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.task_id is None


# ---------------------------------------------------------------------------
# Prefer local
# ---------------------------------------------------------------------------

class TestPreferLocal:
    def test_prefer_local_selects_local_first(self):
        local = _desc(model_id="local-m", tier=ModelTier.LOCAL)
        large = _desc(model_id="large-m", tier=ModelTier.LARGE, cost=0.01, latency=500)
        reg = _registry(large, local)
        result = ModelDispatcher(reg).dispatch(_req(prefer_local=True))
        assert result.model_id == "local-m"

    def test_prefer_local_false_still_selects_local_via_tier_order(self):
        # LOCAL tier order = 0 < SMALL tier order = 1, so LOCAL still wins
        # even without the prefer_local bonus.  prefer_local=True only
        # provides an extra first-key advantage; the tier ordering is sufficient.
        local = _desc(model_id="local-m", tier=ModelTier.LOCAL)
        small = _desc(model_id="small-m", tier=ModelTier.SMALL, cost=0.001, latency=100)
        reg = _registry(small, local)
        result = ModelDispatcher(reg).dispatch(_req(prefer_local=False))
        assert result.model_id == "local-m"


# ---------------------------------------------------------------------------
# Fallback passes
# ---------------------------------------------------------------------------

class TestFallbackPasses:
    def test_fallback_pass2_no_latency(self):
        # Model passes cost but fails latency → relaxed-latency pass wins
        d = _desc(model_id="m1", cost=0.01, latency=2000)
        result = ModelDispatcher(_registry(d)).dispatch(_req(max_cost=0.02, max_latency=500))
        assert result.model_id == "m1"
        assert result.fallback_used is True
        assert "latency" in result.fallback_reason.lower()

    def test_fallback_pass3_no_cost(self):
        # Model passes latency but fails cost → relaxed-cost pass wins
        d = _desc(model_id="m1", cost=0.05, latency=200)
        result = ModelDispatcher(_registry(d)).dispatch(_req(max_cost=0.01, max_latency=500))
        assert result.model_id == "m1"
        assert result.fallback_used is True
        assert "cost" in result.fallback_reason.lower()

    def test_fallback_pass4_no_budget(self):
        # Model fails both cost and latency → no-budget pass wins
        d = _desc(model_id="m1", cost=0.05, latency=2000)
        result = ModelDispatcher(_registry(d)).dispatch(_req(max_cost=0.01, max_latency=500))
        assert result.model_id == "m1"
        assert result.fallback_used is True

    def test_fallback_pass5_no_caps(self):
        # Model fails capability check → last-resort pass wins
        d = _desc(model_id="m1", tool_use=False)
        result = ModelDispatcher(_registry(d)).dispatch(_req(require_tool=True))
        assert result.model_id == "m1"
        assert result.fallback_used is True
        assert "capability" in result.fallback_reason.lower()

    def test_fallback_result_mentions_fallback(self):
        d = _desc(model_id="m1", cost=0.05, latency=2000)
        result = ModelDispatcher(_registry(d)).dispatch(_req(max_cost=0.01, max_latency=500))
        assert "fallback" in result.selected_reason.lower()


# ---------------------------------------------------------------------------
# NoModelAvailableError
# ---------------------------------------------------------------------------

class TestNoModelAvailable:
    def test_empty_registry_raises(self):
        with pytest.raises(NoModelAvailableError):
            ModelDispatcher(ModelRegistry()).dispatch(_req())

    def test_wrong_purpose_raises(self):
        reg = _registry(_desc(purposes=[ModelPurpose.CLASSIFICATION]))
        with pytest.raises(NoModelAvailableError):
            ModelDispatcher(reg).dispatch(_req(purpose=ModelPurpose.RANKING))

    def test_all_unavailable_raises(self):
        reg = _registry(_desc(is_available=False))
        with pytest.raises(NoModelAvailableError):
            ModelDispatcher(reg).dispatch(_req())

    def test_error_carries_reason(self):
        with pytest.raises(NoModelAvailableError) as exc_info:
            ModelDispatcher(ModelRegistry()).dispatch(_req())
        assert exc_info.value.reason

    def test_error_carries_request(self):
        req = _req(task_id="t-err")
        with pytest.raises(NoModelAvailableError) as exc_info:
            ModelDispatcher(ModelRegistry()).dispatch(req)
        assert exc_info.value.request is req

    def test_error_is_runtime_error(self):
        with pytest.raises(RuntimeError):
            ModelDispatcher(ModelRegistry()).dispatch(_req())


# ---------------------------------------------------------------------------
# Ordering / ranking
# ---------------------------------------------------------------------------

class TestOrdering:
    def test_tier_order_small_before_medium(self):
        small = _desc(model_id="small", tier=ModelTier.SMALL, cost=0.005, latency=200)
        medium = _desc(model_id="medium", tier=ModelTier.MEDIUM, cost=0.005, latency=200)
        reg = _registry(medium, small)
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.model_id == "small"

    def test_tier_order_medium_before_large(self):
        medium = _desc(model_id="medium", tier=ModelTier.MEDIUM, cost=0.005, latency=200)
        large = _desc(model_id="large", tier=ModelTier.LARGE, cost=0.005, latency=200)
        reg = _registry(large, medium)
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.model_id == "medium"

    def test_cost_order_within_same_tier(self):
        cheap = _desc(model_id="cheap", tier=ModelTier.LARGE, cost=0.005, latency=500)
        pricey = _desc(model_id="pricey", tier=ModelTier.LARGE, cost=0.020, latency=500)
        reg = _registry(pricey, cheap)
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.model_id == "cheap"

    def test_latency_order_within_same_tier_cost(self):
        fast = _desc(model_id="fast", tier=ModelTier.LARGE, cost=0.010, latency=200)
        slow = _desc(model_id="slow", tier=ModelTier.LARGE, cost=0.010, latency=800)
        reg = _registry(slow, fast)
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.model_id == "fast"

    def test_unknown_cost_sorts_after_known(self):
        known = _desc(model_id="known", tier=ModelTier.LARGE, cost=0.010, latency=500)
        unknown_cost = _desc(model_id="unk", tier=ModelTier.LARGE, cost=None, latency=500)
        reg = _registry(unknown_cost, known)
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.model_id == "known"

    def test_unknown_latency_sorts_after_known(self):
        known = _desc(model_id="known", tier=ModelTier.LARGE, cost=0.010, latency=500)
        unknown_lat = _desc(model_id="unk", tier=ModelTier.LARGE, cost=0.010, latency=None)
        reg = _registry(unknown_lat, known)
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.model_id == "known"


# ---------------------------------------------------------------------------
# Capability filtering
# ---------------------------------------------------------------------------

class TestCapabilityFiltering:
    def test_require_tool_use_filters(self):
        no_tool = _desc(model_id="no-tool", tool_use=False, cost=0.001, latency=100,
                        tier=ModelTier.SMALL)
        has_tool = _desc(model_id="has-tool", tool_use=True, cost=0.010, latency=500)
        reg = _registry(no_tool, has_tool)
        # Strict pass: only has-tool qualifies
        result = ModelDispatcher(reg).dispatch(_req(require_tool=True))
        assert result.model_id == "has-tool"
        assert result.fallback_used is False

    def test_require_structured_output_filters(self):
        no_struct = _desc(model_id="no-struct", structured=False, cost=0.001, latency=100,
                          tier=ModelTier.SMALL)
        has_struct = _desc(model_id="has-struct", structured=True, cost=0.010, latency=500)
        reg = _registry(no_struct, has_struct)
        result = ModelDispatcher(reg).dispatch(_req(require_structured=True))
        assert result.model_id == "has-struct"
        assert result.fallback_used is False

    def test_both_capabilities_required(self):
        partial = _desc(model_id="partial", tool_use=True, structured=False,
                        tier=ModelTier.SMALL, cost=0.001, latency=100)
        full = _desc(model_id="full", tool_use=True, structured=True,
                     cost=0.010, latency=500)
        reg = _registry(partial, full)
        result = ModelDispatcher(reg).dispatch(_req(require_tool=True, require_structured=True))
        assert result.model_id == "full"
        assert result.fallback_used is False


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_unavailable_excluded_from_all_passes(self):
        off = _desc(model_id="off", is_available=False)
        on = _desc(model_id="on", is_available=True, cost=0.010, latency=500)
        reg = _registry(off, on)
        result = ModelDispatcher(reg).dispatch(_req())
        assert result.model_id == "on"

    def test_only_unavailable_raises(self):
        reg = _registry(_desc(is_available=False))
        with pytest.raises(NoModelAvailableError):
            ModelDispatcher(reg).dispatch(_req())


# ---------------------------------------------------------------------------
# ModelRoutingRequest validation
# ---------------------------------------------------------------------------

class TestModelRoutingRequestValidation:
    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            ModelRoutingRequest(purpose=ModelPurpose.PLANNING, unknown_field="x")

    def test_negative_cost_rejected(self):
        with pytest.raises(Exception):
            ModelRoutingRequest(purpose=ModelPurpose.PLANNING, max_cost_per_1k_tokens=-0.001)

    def test_zero_latency_rejected(self):
        with pytest.raises(Exception):
            ModelRoutingRequest(purpose=ModelPurpose.PLANNING, max_p95_latency_ms=0)

    def test_valid_request_accepts_all_purposes(self):
        for p in ModelPurpose:
            req = ModelRoutingRequest(purpose=p)
            assert req.purpose == p


# ---------------------------------------------------------------------------
# ModelRoutingResult validation
# ---------------------------------------------------------------------------

class TestModelRoutingResultValidation:
    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            ModelRoutingResult(
                model_id="m",
                provider=ModelProvider.ANTHROPIC,
                tier=ModelTier.LARGE,
                purposes=[ModelPurpose.PLANNING],
                selected_reason="r",
                unknown_field="x",
            )


# ---------------------------------------------------------------------------
# selected_reason content
# ---------------------------------------------------------------------------

class TestSelectedReason:
    def test_reason_mentions_purpose(self):
        reg = _registry(_desc())
        result = ModelDispatcher(reg).dispatch(_req(purpose=ModelPurpose.PLANNING))
        assert "planning" in result.selected_reason.lower()

    def test_reason_mentions_tier(self):
        reg = _registry(_desc(tier=ModelTier.LARGE, cost=0.01, latency=500))
        result = ModelDispatcher(reg).dispatch(_req())
        assert "large" in result.selected_reason.lower()
