"""Phase 4 — Quality-aware dispatcher policy tests.

Covers the policy primitive landed per
``docs/reviews/phase_quantization_routing_policy_inventory.md:§8``:

- ``ModelRoutingRequest.max_quality_regression`` field shape.
- ``_apply_quality`` filter: pass-through on ``None``-delta, measured delta
  gated on tolerance, boundary inclusive.
- Distillation delta overrides quantization delta when both present.
- ``no-quality`` pass slots into the cascade before ``no-caps``; capability
  requirements never relax before the quality preference.
- Rank term: measured-better-quality beats measured-worse-quality and
  ``None``-delta at equal tier/cost/latency.
- Hosted non-LOCAL candidates always pass the quality filter (schema-level
  invariant: lineage is LOCAL-only).
- ``fallback_reason="relaxed quality tolerance"`` when the new pass wins.
- Default request (``max_quality_regression=None``) dispatches identically
  to today on the real ``DEFAULT_MODELS`` catalog.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.routing.catalog import DEFAULT_MODELS, build_default_registry
from core.routing.dispatcher import (
    ModelDispatcher,
    ModelRoutingRequest,
    NoModelAvailableError,
)
from core.routing.models import (
    DistillationLineage,
    DistillationMethod,
    ModelDescriptor,
    ModelProvider,
    ModelPurpose,
    ModelTier,
    QuantizationMethod,
    QuantizationProfile,
)
from core.routing.registry import ModelRegistry

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _local(
    model_id: str,
    *,
    quant_delta: float | None = None,
    distill_delta: float | None = None,
    latency: int = 100,
) -> ModelDescriptor:
    quantization: QuantizationProfile | None = None
    if quant_delta is not None or distill_delta is None:
        quantization = QuantizationProfile(
            method=QuantizationMethod.GGUF_Q4_K_M,
            bits=4,
            baseline_model_id="some-baseline",
            quality_delta_vs_baseline=quant_delta,
        )
    distillation: DistillationLineage | None = None
    if distill_delta is not None:
        distillation = DistillationLineage(
            teacher_model_id="claude-opus-4-7",
            method=DistillationMethod.KD,
            quality_delta_vs_teacher=distill_delta,
        )
    return ModelDescriptor.model_validate(
        {
            "model_id": model_id,
            "display_name": model_id,
            "provider": ModelProvider.LOCAL,
            "purposes": [ModelPurpose.LOCAL_ASSIST],
            "tier": ModelTier.LOCAL,
            "p95_latency_ms": latency,
            "is_available": True,
            "quantization": quantization,
            "distillation": distillation,
        }
    )


def _hosted(model_id: str, *, tier: ModelTier, cost: float) -> ModelDescriptor:
    return ModelDescriptor.model_validate(
        {
            "model_id": model_id,
            "display_name": model_id,
            "provider": ModelProvider.ANTHROPIC,
            "purposes": [ModelPurpose.LOCAL_ASSIST],
            "tier": tier,
            "cost_per_1k_tokens": cost,
            "p95_latency_ms": 500,
            "is_available": True,
        }
    )


def _registry(*descriptors: ModelDescriptor) -> ModelRegistry:
    reg = ModelRegistry()
    for d in descriptors:
        reg.register(d)
    return reg


# ---------------------------------------------------------------------------
# Request-field validation
# ---------------------------------------------------------------------------


class TestRequestValidation:
    def test_default_is_none(self):
        req = ModelRoutingRequest(purpose=ModelPurpose.LOCAL_ASSIST)
        assert req.max_quality_regression is None

    def test_accepts_zero(self):
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST, max_quality_regression=0.0
        )
        assert req.max_quality_regression == 0.0

    def test_accepts_one(self):
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST, max_quality_regression=1.0
        )
        assert req.max_quality_regression == 1.0

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_quality_regression=-0.01
            )

    def test_rejects_above_one(self):
        with pytest.raises(ValidationError):
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_quality_regression=1.01
            )


# ---------------------------------------------------------------------------
# Backward-compat: None-default preserves prior behaviour
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_default_catalog_dispatch_unchanged_for_classification(self):
        reg = build_default_registry()
        req = ModelRoutingRequest(purpose=ModelPurpose.CLASSIFICATION)
        result = ModelDispatcher(reg).dispatch(req)
        assert result.tier in (ModelTier.LOCAL, ModelTier.SMALL)
        assert result.fallback_used is False

    def test_default_catalog_dispatch_unchanged_for_planning(self):
        reg = build_default_registry()
        req = ModelRoutingRequest(purpose=ModelPurpose.PLANNING)
        result = ModelDispatcher(reg).dispatch(req)
        assert result.tier in (ModelTier.MEDIUM, ModelTier.LARGE)

    def test_default_catalog_local_dispatch_unchanged_with_prefer_local(self):
        reg = build_default_registry(enable_local=True)
        # LOCAL defaults carry quantization but None-delta — prefer_local with
        # max_quality_regression=0.0 must still not filter them out.
        req = ModelRoutingRequest(
            purpose=ModelPurpose.CLASSIFICATION,
            prefer_local=True,
            max_quality_regression=0.0,
        )
        result = ModelDispatcher(reg).dispatch(req)
        # LOCAL defaults are is_available=False so they stay excluded — but no
        # NoModelAvailableError because SMALL/MEDIUM are in the pool.
        assert result.tier in (ModelTier.LOCAL, ModelTier.SMALL)


# ---------------------------------------------------------------------------
# Filter semantics
# ---------------------------------------------------------------------------


class TestQualityFilter:
    def test_measured_regression_below_tolerance_filtered_out(self):
        reg = _registry(
            _local("bad-local", quant_delta=-0.25),
            _hosted("claude-haiku-4-5", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.10,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "claude-haiku-4-5"
        assert result.fallback_used is False

    def test_measured_regression_equal_to_tolerance_passes(self):
        reg = _registry(
            _local("edge-local", quant_delta=-0.10),
            _hosted("claude-haiku-4-5", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.10,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "edge-local"

    def test_none_delta_passes_filter(self):
        reg = _registry(
            _local("unmeasured-local", quant_delta=None),
            _hosted("claude-haiku-4-5", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.05,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "unmeasured-local"

    def test_zero_tolerance_rejects_any_regression(self):
        reg = _registry(
            _local("slightly-bad-local", quant_delta=-0.01),
            _hosted("claude-haiku-4-5", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.0,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "claude-haiku-4-5"

    def test_hosted_non_local_always_passes_filter(self):
        reg = _registry(
            _hosted("claude-haiku-4-5", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            max_quality_regression=0.0,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# Delta source ordering
# ---------------------------------------------------------------------------


class TestDeltaSourceOrdering:
    def test_distillation_overrides_quantization_when_both_present(self):
        # Quantization says -0.03 (would pass), distillation says -0.25 (would fail).
        # Policy must read distillation and reject.
        reg = _registry(
            _local(
                "dual-lineage-local",
                quant_delta=-0.03,
                distill_delta=-0.25,
            ),
            _hosted("claude-haiku-4-5", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.05,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "claude-haiku-4-5"

    def test_quantization_consulted_when_distillation_absent(self):
        reg = _registry(
            _local("quant-only-local", quant_delta=-0.25),
            _hosted("claude-haiku-4-5", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.05,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# Fallback cascade
# ---------------------------------------------------------------------------


class TestCascadeOrdering:
    def test_no_quality_pass_wins_when_all_below_tolerance(self):
        reg = _registry(
            _local("bad-local-1", quant_delta=-0.40),
            _local("bad-local-2", quant_delta=-0.30),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.05,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.fallback_used is True
        assert result.fallback_reason == "relaxed quality tolerance"
        # The less-bad regression should win the rank term at equal tier/latency.
        assert result.model_id == "bad-local-2"

    def test_no_quality_pass_reached_before_no_caps(self):
        # Candidate that has lineage-regression but also supports tool_use.
        # Request needs tool_use.  Quality filter drops it; the "no-quality"
        # pass should accept it — we must never relax tool_use to get here.
        desc = ModelDescriptor.model_validate(
            {
                "model_id": "tooluse-local",
                "display_name": "tooluse-local",
                "provider": ModelProvider.LOCAL,
                "purposes": [ModelPurpose.LOCAL_ASSIST],
                "tier": ModelTier.LOCAL,
                "p95_latency_ms": 100,
                "is_available": True,
                "supports_tool_use": True,
                "quantization": QuantizationProfile(
                    method=QuantizationMethod.GGUF_Q4_K_M,
                    bits=4,
                    baseline_model_id="base",
                    quality_delta_vs_baseline=-0.50,
                ),
            }
        )
        reg = _registry(desc)
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            require_tool_use=True,
            max_quality_regression=0.05,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "tooluse-local"
        assert result.fallback_reason == "relaxed quality tolerance"

    def test_caps_never_relax_before_quality(self):
        # Only candidate has tool_use=False.  Request needs tool_use AND
        # rejects regressions.  The cascade must exhaust quality relaxation
        # before capability relaxation: "relaxed capability requirements"
        # should win, not "relaxed quality tolerance".
        desc = _local("no-tools-local", quant_delta=-0.02)
        reg = _registry(desc)
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            require_tool_use=True,
            max_quality_regression=0.0,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "no-tools-local"
        assert result.fallback_reason == "relaxed capability requirements"

    def test_empty_pool_raises(self):
        reg = ModelRegistry()
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            max_quality_regression=0.05,
        )
        with pytest.raises(NoModelAvailableError):
            ModelDispatcher(reg).dispatch(req)


# ---------------------------------------------------------------------------
# Rank term
# ---------------------------------------------------------------------------


class TestRankTerm:
    def test_better_measured_delta_wins_at_equal_tier(self):
        reg = _registry(
            _local("worse-local", quant_delta=-0.15, latency=100),
            _local("better-local", quant_delta=-0.02, latency=100),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.20,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "better-local"

    def test_measured_delta_wins_over_none_delta_at_equal_tier(self):
        reg = _registry(
            _local("measured-local", quant_delta=-0.02, latency=100),
            _local("unmeasured-local", quant_delta=None, latency=100),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
        )
        result = ModelDispatcher(reg).dispatch(req)
        assert result.model_id == "measured-local"

    def test_rank_term_subordinate_to_tier(self):
        # A high-quality LOCAL (delta=-0.02) vs a LOCAL with bad delta vs a
        # hosted SMALL.  With prefer_local=False, SMALL's lower-tier LOCAL
        # should still win on tier (tier term dominates quality term).
        reg = _registry(
            _local("local-bad", quant_delta=-0.25, latency=100),
            _local("local-good", quant_delta=-0.02, latency=100),
            _hosted("hosted-small", tier=ModelTier.SMALL, cost=0.001),
        )
        req = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST,
            prefer_local=True,
            max_quality_regression=0.05,
        )
        result = ModelDispatcher(reg).dispatch(req)
        # local-bad is filtered out; local-good wins on prefer_local+tier.
        assert result.model_id == "local-good"
