"""Phase 4 – RoutingAuditor lineage-attribute tests.

Follow-up to the declaration-layer primitive
(`phase_quantization_descriptor_fields_review.md`).  Extends
``RoutingAuditor`` to emit the declared quantization and distillation
lineage from the selected ``ModelDescriptor`` as span attributes.  Pure
observation — no routing-policy change.

Covered:
- All six new keys are always emitted (None when absent) so the span
  schema stays stable.
- LOCAL descriptor with quantization populates the three quant keys.
- LOCAL descriptor with distillation populates the three distill keys.
- Hosted descriptor (no lineage possible) keeps all six as None.
- Descriptor=None keeps all six as None (existing behaviour preserved).
- Failure span keeps all six as None too.
"""

from __future__ import annotations

import pytest

from core.audit.trace_store import TraceStore
from core.routing.auditor import RoutingAuditor
from core.routing.dispatcher import (
    ModelRoutingRequest,
    ModelRoutingResult,
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

pytestmark = pytest.mark.unit


LINEAGE_KEYS = [
    "routing.result.quantization.method",
    "routing.result.quantization.bits",
    "routing.result.quantization.quality_delta_vs_baseline",
    "routing.result.distillation.teacher_model_id",
    "routing.result.distillation.method",
    "routing.result.distillation.quality_delta_vs_teacher",
]


def _store(tmp_path) -> TraceStore:
    return TraceStore(tmp_path / "test_routing_audit_lineage.sqlite3")


def _trace_id(store: TraceStore) -> str:
    return store.create_trace("test-lineage").trace_id


def _request() -> ModelRoutingRequest:
    return ModelRoutingRequest(
        purpose=ModelPurpose.LOCAL_ASSIST,
        task_id="t-lineage",
        prefer_local=True,
    )


def _result_local() -> ModelRoutingResult:
    return ModelRoutingResult(
        model_id="llama-3-8b-local-q4",
        provider=ModelProvider.LOCAL,
        tier=ModelTier.LOCAL,
        purposes=[ModelPurpose.LOCAL_ASSIST],
        fallback_used=False,
        fallback_reason=None,
        selected_reason="Best local match",
        task_id="t-lineage",
    )


def _result_hosted() -> ModelRoutingResult:
    return ModelRoutingResult(
        model_id="claude-haiku-4-5",
        provider=ModelProvider.ANTHROPIC,
        tier=ModelTier.SMALL,
        purposes=[ModelPurpose.LOCAL_ASSIST],
        fallback_used=True,
        fallback_reason="no_local_available",
        selected_reason="Fallback to hosted",
        task_id="t-lineage",
    )


def _local_descriptor(
    *,
    quantization: QuantizationProfile | None = None,
    distillation: DistillationLineage | None = None,
) -> ModelDescriptor:
    return ModelDescriptor.model_validate(
        {
            "model_id": "llama-3-8b-local-q4",
            "display_name": "Llama 3 8B local Q4",
            "provider": ModelProvider.LOCAL,
            "purposes": [ModelPurpose.LOCAL_ASSIST],
            "tier": ModelTier.LOCAL,
            "p95_latency_ms": 800,
            "quantization": quantization,
            "distillation": distillation,
        }
    )


def _hosted_descriptor() -> ModelDescriptor:
    return ModelDescriptor.model_validate(
        {
            "model_id": "claude-haiku-4-5",
            "display_name": "Claude Haiku 4.5",
            "provider": ModelProvider.ANTHROPIC,
            "purposes": [ModelPurpose.LOCAL_ASSIST],
            "tier": ModelTier.SMALL,
            "cost_per_1k_tokens": 0.001,
            "p95_latency_ms": 500,
        }
    )


# ---------------------------------------------------------------------------
# Schema stability — all six keys always present
# ---------------------------------------------------------------------------


class TestLineageSchemaStability:
    def test_all_keys_present_without_descriptor(self, tmp_path):
        store = _store(tmp_path)
        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local()
        )
        for key in LINEAGE_KEYS:
            assert key in span.attributes
            assert span.attributes[key] is None

    def test_all_keys_present_for_hosted_descriptor(self, tmp_path):
        store = _store(tmp_path)
        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store),
            _request(),
            _result_hosted(),
            descriptor=_hosted_descriptor(),
        )
        for key in LINEAGE_KEYS:
            assert key in span.attributes
            assert span.attributes[key] is None

    def test_all_keys_present_on_failure_span(self, tmp_path):
        store = _store(tmp_path)
        request = _request()
        span = RoutingAuditor(store).record_routing_failure(
            _trace_id(store),
            request,
            NoModelAvailableError("no candidates", request),
        )
        for key in LINEAGE_KEYS:
            assert key in span.attributes
            assert span.attributes[key] is None


# ---------------------------------------------------------------------------
# Quantization attributes
# ---------------------------------------------------------------------------


class TestQuantizationAttributes:
    def test_quantization_populates_three_keys(self, tmp_path):
        store = _store(tmp_path)
        quant = QuantizationProfile(
            method=QuantizationMethod.GGUF_Q4_K_M,
            bits=4,
            baseline_model_id="llama-3-8b",
            quality_delta_vs_baseline=-0.03,
            evaluated_on="abrain-routing-eval-v3",
        )
        descriptor = _local_descriptor(quantization=quant)

        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        assert span.attributes["routing.result.quantization.method"] == "gguf_q4_k_m"
        assert span.attributes["routing.result.quantization.bits"] == 4
        assert span.attributes["routing.result.quantization.quality_delta_vs_baseline"] == -0.03

    def test_quantization_without_delta_is_none(self, tmp_path):
        store = _store(tmp_path)
        quant = QuantizationProfile(method=QuantizationMethod.INT4, bits=4)
        descriptor = _local_descriptor(quantization=quant)

        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        assert span.attributes["routing.result.quantization.method"] == "int4"
        assert span.attributes["routing.result.quantization.bits"] == 4
        assert span.attributes["routing.result.quantization.quality_delta_vs_baseline"] is None

    def test_quantization_absent_keeps_keys_none(self, tmp_path):
        store = _store(tmp_path)
        descriptor = _local_descriptor()  # no quant

        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        assert span.attributes["routing.result.quantization.method"] is None
        assert span.attributes["routing.result.quantization.bits"] is None
        assert span.attributes["routing.result.quantization.quality_delta_vs_baseline"] is None


# ---------------------------------------------------------------------------
# Distillation attributes
# ---------------------------------------------------------------------------


class TestDistillationAttributes:
    def test_distillation_populates_three_keys(self, tmp_path):
        store = _store(tmp_path)
        distill = DistillationLineage(
            teacher_model_id="claude-opus-4-7",
            method=DistillationMethod.KD,
            quality_delta_vs_teacher=-0.12,
            evaluated_on="abrain-routing-eval-v3",
        )
        descriptor = _local_descriptor(distillation=distill)

        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        assert span.attributes["routing.result.distillation.teacher_model_id"] == "claude-opus-4-7"
        assert span.attributes["routing.result.distillation.method"] == "kd"
        assert span.attributes["routing.result.distillation.quality_delta_vs_teacher"] == -0.12

    def test_distillation_without_delta_is_none(self, tmp_path):
        store = _store(tmp_path)
        distill = DistillationLineage(
            teacher_model_id="gpt-4o",
            method=DistillationMethod.SELF_DISTILL,
        )
        descriptor = _local_descriptor(distillation=distill)

        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        assert span.attributes["routing.result.distillation.teacher_model_id"] == "gpt-4o"
        assert span.attributes["routing.result.distillation.method"] == "self_distill"
        assert span.attributes["routing.result.distillation.quality_delta_vs_teacher"] is None

    def test_both_lineages_together(self, tmp_path):
        store = _store(tmp_path)
        quant = QuantizationProfile(method=QuantizationMethod.AWQ, bits=4)
        distill = DistillationLineage(
            teacher_model_id="claude-opus-4-7", method=DistillationMethod.FITNETS
        )
        descriptor = _local_descriptor(quantization=quant, distillation=distill)

        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        assert span.attributes["routing.result.quantization.method"] == "awq"
        assert span.attributes["routing.result.distillation.method"] == "fitnets"


# ---------------------------------------------------------------------------
# Existing result attributes stay intact — lineage is purely additive
# ---------------------------------------------------------------------------


class TestExistingAttributesPreserved:
    def test_cost_latency_still_emitted_alongside_lineage(self, tmp_path):
        store = _store(tmp_path)
        quant = QuantizationProfile(method=QuantizationMethod.INT4, bits=4)
        descriptor = _local_descriptor(quantization=quant)

        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        # LOCAL tier has no cost by invariant; latency is declared.
        assert span.attributes["routing.result.cost_per_1k_tokens"] is None
        assert span.attributes["routing.result.p95_latency_ms"] == 800
        # And lineage is populated.
        assert span.attributes["routing.result.quantization.method"] == "int4"

    def test_model_id_tier_provider_unchanged(self, tmp_path):
        store = _store(tmp_path)
        descriptor = _local_descriptor(
            quantization=QuantizationProfile(
                method=QuantizationMethod.GPTQ, bits=4
            )
        )
        span = RoutingAuditor(store).record_dispatch(
            _trace_id(store), _request(), _result_local(), descriptor=descriptor
        )
        assert span.attributes["routing.result.model_id"] == "llama-3-8b-local-q4"
        assert span.attributes["routing.result.tier"] == "local"
        assert span.attributes["routing.result.provider"] == "local"
