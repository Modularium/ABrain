"""§6.5 Green AI — per-decision energy-aware dispatcher policy tests.

Covers the primitive landed per
``docs/reviews/phase_green_energy_per_decision_inventory.md:§8``:

- ``ModelRoutingRequest.max_energy_joules`` field shape.
- ``_apply_energy`` filter: pass-through on unknown energy (missing p95
  or missing wattage), measured joules gated on tolerance, boundary
  inclusive.
- Per-decision formula: ``joules = p95_latency_ms / 1000 × avg_power_watts``.
- ``no-energy`` pass slots into the cascade between ``no-quality`` and
  ``no-caps``; capability requirements never relax before the energy
  preference.
- Rank term: measured-lower-energy beats measured-higher-energy and
  unknown-energy at equal tier/cost/latency/quality.
- ``fallback_reason="relaxed energy tolerance"`` when the new pass wins.
- ``RoutingAuditor`` emits ``routing.result.estimated_energy_joules`` and
  ``routing.result.energy_profile_source`` on every dispatch span.
- Default request (``max_energy_joules=None``) dispatches identically
  to today on the real ``DEFAULT_MODELS`` catalog.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from core.audit.trace_store import TraceStore
from core.decision.energy_report import EnergyProfile
from core.routing.auditor import RoutingAuditor
from core.routing.catalog import build_default_registry
from core.routing.dispatcher import (
    ModelDispatcher,
    ModelRoutingRequest,
    NoModelAvailableError,
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


def _local(
    model_id: str,
    *,
    watts: float | None = None,
    source: str = "estimated",
    latency: int | None = 100,
    tools: bool = False,
) -> ModelDescriptor:
    profile = (
        EnergyProfile(avg_power_watts=watts, source=source) if watts is not None else None
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
            "supports_tool_use": tools,
            "energy_profile": profile,
        }
    )


def _hosted(
    model_id: str,
    *,
    tier: ModelTier = ModelTier.SMALL,
    cost: float = 0.001,
    latency: int | None = 500,
    watts: float | None = None,
    source: str = "estimated",
    tools: bool = False,
) -> ModelDescriptor:
    profile = (
        EnergyProfile(avg_power_watts=watts, source=source) if watts is not None else None
    )
    return ModelDescriptor.model_validate(
        {
            "model_id": model_id,
            "display_name": model_id,
            "provider": ModelProvider.ANTHROPIC,
            "purposes": [ModelPurpose.LOCAL_ASSIST],
            "tier": tier,
            "cost_per_1k_tokens": cost,
            "p95_latency_ms": latency,
            "is_available": True,
            "supports_tool_use": tools,
            "energy_profile": profile,
        }
    )


def _registry(*descriptors: ModelDescriptor) -> ModelRegistry:
    registry = ModelRegistry()
    for d in descriptors:
        registry.register(d)
    return registry


# ---------------------------------------------------------------------------
# 1. Request validation
# ---------------------------------------------------------------------------


class TestRequestValidation:
    def test_default_is_none(self) -> None:
        request = ModelRoutingRequest(purpose=ModelPurpose.LOCAL_ASSIST)
        assert request.max_energy_joules is None

    def test_accepts_zero(self) -> None:
        request = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=0.0
        )
        assert request.max_energy_joules == 0.0

    def test_accepts_large_value(self) -> None:
        request = ModelRoutingRequest(
            purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=1_000_000.0
        )
        assert request.max_energy_joules == 1_000_000.0

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=-0.1
            )


# ---------------------------------------------------------------------------
# 2. Backward compatibility on real catalog
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_default_catalog_dispatch_unchanged_for_classification(self) -> None:
        registry = build_default_registry()
        baseline = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(purpose=ModelPurpose.CLASSIFICATION)
        )
        with_gate = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.CLASSIFICATION, max_energy_joules=0.0
            )
        )
        assert baseline.model_id == with_gate.model_id
        assert baseline.fallback_used == with_gate.fallback_used

    def test_default_catalog_dispatch_unchanged_for_local_assist(self) -> None:
        registry = build_default_registry()
        baseline = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, prefer_local=True
            )
        )
        with_none_gate = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST,
                prefer_local=True,
                max_energy_joules=None,
            )
        )
        assert baseline.model_id == with_none_gate.model_id


# ---------------------------------------------------------------------------
# 3. Per-decision formula
# ---------------------------------------------------------------------------


class TestFormula:
    def test_joules_computed_from_p95_and_wattage(self) -> None:
        # 200 ms × 50 W = 0.2 s × 50 W = 10 J
        descriptor = _local("local-a", watts=50.0, latency=200)
        registry = _registry(descriptor)
        # Threshold exactly at 10 J passes.
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=10.0
            )
        )
        assert result.model_id == "local-a"
        assert result.fallback_used is False

    def test_joules_over_threshold_filtered(self) -> None:
        # 200 ms × 50 W = 10 J; threshold 5 J → filtered out.
        local = _local("local-a", watts=50.0, latency=200)
        hosted = _hosted("hosted-a", watts=None, latency=100)  # unknown energy → passes
        registry = _registry(local, hosted)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=5.0
            )
        )
        # local filtered; hosted (unknown energy) wins
        assert result.model_id == "hosted-a"
        assert result.fallback_used is False


# ---------------------------------------------------------------------------
# 4. Unknown-signal honesty
# ---------------------------------------------------------------------------


class TestUnknownPasses:
    def test_unknown_wattage_passes_filter(self) -> None:
        candidate = _local("no-watts", watts=None, latency=100)
        registry = _registry(candidate)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=0.0
            )
        )
        assert result.model_id == "no-watts"

    def test_unknown_p95_passes_filter(self) -> None:
        candidate = _local("no-p95", watts=50.0, latency=None)
        registry = _registry(candidate)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=0.0
            )
        )
        assert result.model_id == "no-p95"

    def test_boundary_inclusive(self) -> None:
        # 100 ms × 10 W = 1.0 J; threshold 1.0 J → passes (<=).
        candidate = _local("boundary", watts=10.0, latency=100)
        registry = _registry(candidate)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=1.0
            )
        )
        assert result.model_id == "boundary"


# ---------------------------------------------------------------------------
# 5. Cascade ordering
# ---------------------------------------------------------------------------


class TestCascadeOrdering:
    def test_no_energy_pass_wins_with_correct_reason(self) -> None:
        # Only candidate exceeds the budget; strict…no-quality all empty;
        # no-energy pass should win.
        heavy = _local("heavy", watts=500.0, latency=200)  # 100 J per decision
        registry = _registry(heavy)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=5.0
            )
        )
        assert result.model_id == "heavy"
        assert result.fallback_used is True
        assert result.fallback_reason == "relaxed energy tolerance"

    def test_caps_honoured_on_no_energy_pass(self) -> None:
        # Tool-using heavy candidate plus a light non-tool candidate.
        # With require_tool_use=True, the light one must be filtered out
        # across the first six passes, and heavy should win on no-energy —
        # NOT the light one on no-caps.
        heavy = _local("heavy-tools", watts=500.0, latency=200, tools=True)
        light = _local("light-no-tools", watts=1.0, latency=100, tools=False)
        registry = _registry(heavy, light)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST,
                max_energy_joules=5.0,
                require_tool_use=True,
            )
        )
        assert result.model_id == "heavy-tools"
        assert result.fallback_reason == "relaxed energy tolerance"

    def test_caps_relax_only_in_last_pass(self) -> None:
        # No tool-using candidate at all → every pass until no-caps empty.
        light = _local("light-no-tools", watts=1.0, latency=100, tools=False)
        registry = _registry(light)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST,
                max_energy_joules=5.0,
                require_tool_use=True,
            )
        )
        assert result.model_id == "light-no-tools"
        assert result.fallback_reason == "relaxed capability requirements"

    def test_empty_pool_raises(self) -> None:
        registry = ModelRegistry()
        with pytest.raises(NoModelAvailableError):
            ModelDispatcher(registry).dispatch(
                ModelRoutingRequest(
                    purpose=ModelPurpose.LOCAL_ASSIST, max_energy_joules=10.0
                )
            )


# ---------------------------------------------------------------------------
# 6. Rank term
# ---------------------------------------------------------------------------


class TestRankTerm:
    def test_lower_energy_beats_higher_energy(self) -> None:
        light = _local("light", watts=10.0, latency=100)   # 1 J
        heavy = _local("heavy", watts=100.0, latency=100)  # 10 J
        registry = _registry(heavy, light)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(purpose=ModelPurpose.LOCAL_ASSIST)
        )
        assert result.model_id == "light"

    def test_measured_beats_unknown(self) -> None:
        measured = _local("measured", watts=100.0, latency=100)
        unknown = _local("unknown", watts=None, latency=100)
        registry = _registry(unknown, measured)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(purpose=ModelPurpose.LOCAL_ASSIST)
        )
        assert result.model_id == "measured"

    def test_tier_beats_energy(self) -> None:
        # Without prefer_local, LOCAL still beats SMALL by tier order.
        # But a hosted candidate with LOWER cost AND tier doesn't exist here;
        # the test is: energy term does not override tier ordering.
        local_heavy = _local("local-heavy", watts=500.0, latency=100)
        hosted_light = _hosted(
            "hosted-light", tier=ModelTier.SMALL, cost=0.0005, watts=1.0, latency=50
        )
        registry = _registry(local_heavy, hosted_light)
        result = ModelDispatcher(registry).dispatch(
            ModelRoutingRequest(
                purpose=ModelPurpose.LOCAL_ASSIST, prefer_local=True
            )
        )
        # prefer_local=True → LOCAL tier ranks ahead even with worse energy.
        assert result.model_id == "local-heavy"


# ---------------------------------------------------------------------------
# 7. Auditor attributes
# ---------------------------------------------------------------------------


class TestAuditorAttributes:
    def test_known_energy_emitted(self, tmp_path) -> None:
        store = TraceStore(tmp_path / "t.sqlite3")
        descriptor = _local("with-watts", watts=50.0, latency=200)
        registry = _registry(descriptor)
        request = ModelRoutingRequest(purpose=ModelPurpose.LOCAL_ASSIST)
        result = ModelDispatcher(registry).dispatch(request)

        trace_id = store.create_trace("t").trace_id
        span = RoutingAuditor(store).record_dispatch(
            trace_id, request, result, descriptor=descriptor
        )

        assert span is not None
        # 200 ms × 50 W = 10 J
        assert span.attributes["routing.result.estimated_energy_joules"] == pytest.approx(10.0)
        assert span.attributes["routing.result.energy_profile_source"] == "estimated"

    def test_unknown_energy_emitted_as_null(self, tmp_path) -> None:
        store = TraceStore(tmp_path / "t.sqlite3")
        descriptor = _local("no-watts", watts=None, latency=200)
        registry = _registry(descriptor)
        request = ModelRoutingRequest(purpose=ModelPurpose.LOCAL_ASSIST)
        result = ModelDispatcher(registry).dispatch(request)

        trace_id = store.create_trace("t").trace_id
        span = RoutingAuditor(store).record_dispatch(
            trace_id, request, result, descriptor=descriptor
        )

        assert span is not None
        assert span.attributes["routing.result.estimated_energy_joules"] is None
        assert span.attributes["routing.result.energy_profile_source"] is None

    def test_failure_span_includes_null_energy_keys(self, tmp_path) -> None:
        store = TraceStore(tmp_path / "t.sqlite3")
        registry = ModelRegistry()
        request = ModelRoutingRequest(purpose=ModelPurpose.LOCAL_ASSIST)
        try:
            ModelDispatcher(registry).dispatch(request)
            pytest.fail("expected NoModelAvailableError")
        except NoModelAvailableError as exc:
            trace_id = store.create_trace("t").trace_id
            span = RoutingAuditor(store).record_routing_failure(
                trace_id, request, exc
            )

        assert span is not None
        assert span.attributes["routing.result.estimated_energy_joules"] is None
        assert span.attributes["routing.result.energy_profile_source"] is None
