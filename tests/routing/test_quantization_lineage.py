"""Phase 4 – Quantisierungs-/Distillationspfad: declaration-layer tests.

Covers the minimal primitive landed from the Phase-4 inventory:

- ``QuantizationProfile`` + ``QuantizationMethod``
- ``DistillationLineage`` + ``DistillationMethod``
- ``ModelDescriptor.quantization`` / ``.distillation`` additive fields
- ``ModelRegistry`` advisory warning for LOCAL tier without lineage
- Backwards-compat regression: LOCAL descriptors without lineage still
  validate and register (the advisory is non-fatal).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

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


def _local_desc(
    model_id: str = "llama-3-8b-local",
    *,
    quantization: QuantizationProfile | None = None,
    distillation: DistillationLineage | None = None,
    latency: int | None = 800,
) -> ModelDescriptor:
    return ModelDescriptor.model_validate(
        {
            "model_id": model_id,
            "display_name": model_id,
            "provider": ModelProvider.LOCAL,
            "purposes": [ModelPurpose.LOCAL_ASSIST],
            "tier": ModelTier.LOCAL,
            "p95_latency_ms": latency,
            "quantization": quantization,
            "distillation": distillation,
        }
    )


def _hosted_desc(**overrides) -> ModelDescriptor:
    payload = {
        "model_id": "claude-opus-4-7",
        "display_name": "Claude Opus 4.7",
        "provider": ModelProvider.ANTHROPIC,
        "purposes": [ModelPurpose.PLANNING],
        "tier": ModelTier.LARGE,
        "cost_per_1k_tokens": 0.02,
        "p95_latency_ms": 1800,
    }
    payload.update(overrides)
    return ModelDescriptor.model_validate(payload)


# ---------------------------------------------------------------------------
# QuantizationProfile
# ---------------------------------------------------------------------------


class TestQuantizationProfile:
    def test_minimal_valid_profile(self):
        p = QuantizationProfile(method=QuantizationMethod.INT4, bits=4)
        assert p.method == QuantizationMethod.INT4
        assert p.bits == 4
        assert p.baseline_model_id is None
        assert p.quality_delta_vs_baseline is None

    def test_accepts_every_method(self):
        for method in QuantizationMethod:
            QuantizationProfile(method=method, bits=8)

    def test_bits_below_range_rejected(self):
        with pytest.raises(ValidationError):
            QuantizationProfile(method=QuantizationMethod.INT4, bits=1)

    def test_bits_above_range_rejected(self):
        with pytest.raises(ValidationError):
            QuantizationProfile(method=QuantizationMethod.FP16, bits=17)

    def test_quality_delta_clamped_to_unit_interval(self):
        with pytest.raises(ValidationError):
            QuantizationProfile(
                method=QuantizationMethod.INT4, bits=4, quality_delta_vs_baseline=1.5
            )
        with pytest.raises(ValidationError):
            QuantizationProfile(
                method=QuantizationMethod.INT4, bits=4, quality_delta_vs_baseline=-1.5
            )

    def test_baseline_stripped_and_empty_rejected(self):
        p = QuantizationProfile(
            method=QuantizationMethod.INT4, bits=4, baseline_model_id="  llama-3-8b  "
        )
        assert p.baseline_model_id == "llama-3-8b"
        with pytest.raises(ValidationError):
            QuantizationProfile(
                method=QuantizationMethod.INT4, bits=4, baseline_model_id="   "
            )

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            QuantizationProfile.model_validate(
                {"method": "int4", "bits": 4, "rogue": True}
            )


# ---------------------------------------------------------------------------
# DistillationLineage
# ---------------------------------------------------------------------------


class TestDistillationLineage:
    def test_minimal_valid_lineage(self):
        d = DistillationLineage(
            teacher_model_id="claude-opus-4-7", method=DistillationMethod.KD
        )
        assert d.teacher_model_id == "claude-opus-4-7"
        assert d.method == DistillationMethod.KD

    def test_accepts_every_method(self):
        for method in DistillationMethod:
            DistillationLineage(teacher_model_id="t", method=method)

    def test_teacher_stripped_and_empty_rejected(self):
        d = DistillationLineage(
            teacher_model_id="  gpt-4o  ", method=DistillationMethod.KD
        )
        assert d.teacher_model_id == "gpt-4o"
        with pytest.raises(ValidationError):
            DistillationLineage(teacher_model_id="   ", method=DistillationMethod.KD)

    def test_quality_delta_clamped(self):
        with pytest.raises(ValidationError):
            DistillationLineage(
                teacher_model_id="t",
                method=DistillationMethod.KD,
                quality_delta_vs_teacher=2.0,
            )

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            DistillationLineage.model_validate(
                {"teacher_model_id": "t", "method": "kd", "rogue": True}
            )


# ---------------------------------------------------------------------------
# ModelDescriptor lineage fields
# ---------------------------------------------------------------------------


class TestModelDescriptorLineage:
    def test_local_descriptor_with_quantization(self):
        profile = QuantizationProfile(method=QuantizationMethod.GGUF_Q4_K_M, bits=4)
        d = _local_desc(quantization=profile)
        assert d.quantization == profile
        assert d.distillation is None

    def test_local_descriptor_with_distillation(self):
        lineage = DistillationLineage(
            teacher_model_id="claude-opus-4-7", method=DistillationMethod.KD
        )
        d = _local_desc(distillation=lineage)
        assert d.distillation == lineage
        assert d.quantization is None

    def test_local_descriptor_with_both(self):
        profile = QuantizationProfile(method=QuantizationMethod.INT8, bits=8)
        lineage = DistillationLineage(
            teacher_model_id="gpt-4o", method=DistillationMethod.SELF_DISTILL
        )
        d = _local_desc(quantization=profile, distillation=lineage)
        assert d.quantization.bits == 8
        assert d.distillation.teacher_model_id == "gpt-4o"

    def test_local_descriptor_without_lineage_still_valid(self):
        # Backwards-compat: existing LOCAL descriptors on main must keep
        # validating cleanly.  The advisory lives on the registry, not
        # the model.
        d = _local_desc()
        assert d.quantization is None
        assert d.distillation is None

    def test_hosted_descriptor_rejects_quantization(self):
        profile = QuantizationProfile(method=QuantizationMethod.INT4, bits=4)
        with pytest.raises(ValidationError, match="quantization may only be declared on LOCAL"):
            _hosted_desc(quantization=profile)

    def test_hosted_descriptor_rejects_distillation(self):
        lineage = DistillationLineage(
            teacher_model_id="claude-opus-4-7", method=DistillationMethod.KD
        )
        with pytest.raises(ValidationError, match="distillation may only be declared on LOCAL"):
            _hosted_desc(distillation=lineage)

    def test_descriptor_rejects_unknown_extra_field(self):
        with pytest.raises(ValidationError):
            ModelDescriptor.model_validate(
                {
                    "model_id": "x",
                    "display_name": "x",
                    "provider": "local",
                    "purposes": ["local_assist"],
                    "tier": "local",
                    "rogue": True,
                }
            )


# ---------------------------------------------------------------------------
# ModelRegistry advisory
# ---------------------------------------------------------------------------


class TestRegistryLineageAdvisory:
    def test_local_without_lineage_emits_lineage_advisory(self):
        reg = ModelRegistry()
        warnings = reg.register(_local_desc())
        assert any("provenance" in w.lower() for w in warnings)

    def test_local_with_quantization_suppresses_advisory(self):
        reg = ModelRegistry()
        profile = QuantizationProfile(method=QuantizationMethod.INT4, bits=4)
        warnings = reg.register(_local_desc(quantization=profile))
        assert not any("provenance" in w.lower() for w in warnings)

    def test_local_with_distillation_suppresses_advisory(self):
        reg = ModelRegistry()
        lineage = DistillationLineage(
            teacher_model_id="claude-opus-4-7", method=DistillationMethod.KD
        )
        warnings = reg.register(_local_desc(distillation=lineage))
        assert not any("provenance" in w.lower() for w in warnings)

    def test_hosted_never_emits_lineage_advisory(self):
        reg = ModelRegistry()
        warnings = reg.register(_hosted_desc())
        assert not any("provenance" in w.lower() for w in warnings)

    def test_lineage_advisory_is_additive_to_latency_advisory(self):
        reg = ModelRegistry()
        warnings = reg.register(_local_desc(latency=None))
        assert any("latency" in w.lower() for w in warnings)
        assert any("provenance" in w.lower() for w in warnings)
        assert len(warnings) == 2

    def test_registration_still_succeeds_with_lineage_advisory(self):
        reg = ModelRegistry()
        reg.register(_local_desc())
        assert reg.is_registered("llama-3-8b-local")
