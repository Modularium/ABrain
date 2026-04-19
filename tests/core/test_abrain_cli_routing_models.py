"""Phase 4 – `abrain routing models` CLI surface tests.

Read-only operator surface for the canonical model/provider catalog
(`core.routing.catalog.DEFAULT_MODELS`) plus the quantization and
distillation lineage landed in the prior two turns.  No routing-policy
change; service is a pure read of the declared catalog.
"""

from __future__ import annotations

import importlib
import json

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _sample_payload() -> dict:
    return {
        "total": 2,
        "catalog_size": 5,
        "filters": {
            "tier": None,
            "provider": None,
            "purpose": None,
            "available_only": False,
        },
        "tiers": {"local": 1, "small": 1, "medium": 0, "large": 0},
        "providers": {
            "anthropic": 1,
            "openai": 0,
            "google": 0,
            "local": 1,
            "custom": 0,
        },
        "purposes": {
            "planning": 0,
            "classification": 0,
            "ranking": 0,
            "retrieval_assist": 0,
            "local_assist": 2,
            "specialist": 0,
        },
        "models": [
            {
                "model_id": "llama-3-8b-local-q4",
                "display_name": "Llama 3 8B local Q4",
                "provider": "local",
                "tier": "local",
                "purposes": ["local_assist"],
                "context_window": 8192,
                "cost_per_1k_tokens": None,
                "p95_latency_ms": 800,
                "supports_tool_use": False,
                "supports_structured_output": False,
                "is_available": True,
                "quantization": {
                    "method": "gguf_q4_k_m",
                    "bits": 4,
                    "baseline_model_id": "llama-3-8b",
                    "quality_delta_vs_baseline": -0.03,
                    "evaluated_on": "abrain-routing-eval-v3",
                },
                "distillation": None,
            },
            {
                "model_id": "claude-haiku-4-5",
                "display_name": "Claude Haiku 4.5",
                "provider": "anthropic",
                "tier": "small",
                "purposes": ["local_assist"],
                "context_window": 200000,
                "cost_per_1k_tokens": 0.001,
                "p95_latency_ms": 500,
                "supports_tool_use": True,
                "supports_structured_output": True,
                "is_available": True,
                "quantization": None,
                "distillation": None,
            },
        ],
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_catalog_header(self):
        module = _module()
        text = module._render_routing_models(_sample_payload())
        assert "=== Routing Models Catalog ===" in text
        assert "Total (filtered):     2" in text
        assert "Catalog size:         5" in text

    def test_renders_tier_and_provider_summaries(self):
        module = _module()
        text = module._render_routing_models(_sample_payload())
        assert "local=1" in text
        assert "small=1" in text
        assert "anthropic=1" in text
        assert "local=1" in text

    def test_renders_model_rows_with_cost_and_latency(self):
        module = _module()
        text = module._render_routing_models(_sample_payload())
        assert "llama-3-8b-local-q4" in text
        assert "claude-haiku-4-5" in text
        assert "$0.0010/1k" in text
        assert "800ms" in text
        assert "500ms" in text

    def test_renders_quantization_lineage(self):
        module = _module()
        text = module._render_routing_models(_sample_payload())
        assert "quant=gguf_q4_k_m/4b" in text
        assert "Δ=-0.030" in text

    def test_renders_distillation_lineage(self):
        module = _module()
        payload = _sample_payload()
        payload["models"][0]["distillation"] = {
            "teacher_model_id": "claude-opus-4-7",
            "method": "kd",
            "quality_delta_vs_teacher": -0.12,
            "evaluated_on": "abrain-routing-eval-v3",
        }
        text = module._render_routing_models(payload)
        assert "distill=kd<=claude-opus-4-7" in text
        assert "Δ=-0.120" in text

    def test_renders_no_filters_marker(self):
        module = _module()
        text = module._render_routing_models(_sample_payload())
        assert "Active filters:       (none)" in text

    def test_renders_active_filters(self):
        module = _module()
        payload = _sample_payload()
        payload["filters"] = {
            "tier": "local",
            "provider": None,
            "purpose": None,
            "available_only": True,
        }
        text = module._render_routing_models(payload)
        assert "tier=local" in text
        assert "available_only=True" in text

    def test_renders_empty_models(self):
        module = _module()
        payload = _sample_payload()
        payload["models"] = []
        payload["total"] = 0
        text = module._render_routing_models(payload)
        assert "Models (0):" in text
        assert "(none)" in text

    def test_renders_unavailable_marker(self):
        module = _module()
        payload = _sample_payload()
        payload["models"][0]["is_available"] = False
        text = module._render_routing_models(payload)
        assert "[OFF " in text

    def test_renders_error_payload(self):
        module = _module()
        text = module._render_routing_models(
            {"error": "invalid_tier", "detail": "Unknown tier 'xxl'"}
        )
        assert "Routing models unavailable: invalid_tier" in text
        assert "Unknown tier 'xxl'" in text

    def test_renders_cap_with_tail_marker(self):
        module = _module()
        payload = _sample_payload()
        payload["models"] = [
            {
                "model_id": f"m-{i}",
                "display_name": f"m-{i}",
                "provider": "anthropic",
                "tier": "small",
                "purposes": ["planning"],
                "context_window": None,
                "cost_per_1k_tokens": 0.001,
                "p95_latency_ms": 100,
                "supports_tool_use": False,
                "supports_structured_output": False,
                "is_available": True,
                "quantization": None,
                "distillation": None,
            }
            for i in range(45)
        ]
        text = module._render_routing_models(payload)
        assert "... (5 more)" in text


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_defaults_delegate_unfiltered(self, monkeypatch, capsys):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _sample_payload()

        monkeypatch.setattr("services.core.get_routing_models", fake)

        exit_code = module.main(["routing", "models"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "tier": None,
            "provider": None,
            "purpose": None,
            "available_only": False,
        }
        assert "Routing Models Catalog" in output

    def test_forwards_filters(self, monkeypatch):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_routing_models",
            lambda **kw: captured.update(kw) or _sample_payload(),
        )

        module.main(
            [
                "routing",
                "models",
                "--tier",
                "local",
                "--provider",
                "local",
                "--purpose",
                "local_assist",
                "--available-only",
                "--json",
            ]
        )
        assert captured["tier"] == "local"
        assert captured["provider"] == "local"
        assert captured["purpose"] == "local_assist"
        assert captured["available_only"] is True

    def test_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_routing_models",
            lambda **_: _sample_payload(),
        )
        exit_code = module.main(["routing", "models", "--json"])
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["total"] == 2
        assert parsed["models"][0]["model_id"] == "llama-3-8b-local-q4"


# ---------------------------------------------------------------------------
# Service integration (real DEFAULT_MODELS catalog)
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_returns_full_catalog_by_default(self):
        import services.core as core_module
        from core.routing.catalog import DEFAULT_MODELS

        report = core_module.get_routing_models()
        assert "error" not in report
        assert report["total"] == len(DEFAULT_MODELS)
        assert report["catalog_size"] == len(DEFAULT_MODELS)
        assert report["filters"] == {
            "tier": None,
            "provider": None,
            "purpose": None,
            "available_only": False,
        }

    def test_service_filters_by_tier(self):
        import services.core as core_module

        report = core_module.get_routing_models(tier="local")
        assert "error" not in report
        for model in report["models"]:
            assert model["tier"] == "local"

    def test_service_filters_by_provider(self):
        import services.core as core_module

        report = core_module.get_routing_models(provider="anthropic")
        for model in report["models"]:
            assert model["provider"] == "anthropic"

    def test_service_filters_by_purpose(self):
        import services.core as core_module

        report = core_module.get_routing_models(purpose="planning")
        for model in report["models"]:
            assert "planning" in model["purposes"]

    def test_service_filter_tier_is_case_insensitive(self):
        import services.core as core_module

        report = core_module.get_routing_models(tier="LOCAL")
        assert "error" not in report
        assert report["filters"]["tier"] == "local"

    def test_service_rejects_invalid_tier(self):
        import services.core as core_module

        report = core_module.get_routing_models(tier="xxl")
        assert report["error"] == "invalid_tier"
        assert "xxl" in report["detail"]

    def test_service_rejects_invalid_provider(self):
        import services.core as core_module

        report = core_module.get_routing_models(provider="unknown")
        assert report["error"] == "invalid_provider"

    def test_service_rejects_invalid_purpose(self):
        import services.core as core_module

        report = core_module.get_routing_models(purpose="unknown")
        assert report["error"] == "invalid_purpose"

    def test_service_available_only_filter(self):
        import services.core as core_module

        report = core_module.get_routing_models(available_only=True)
        for model in report["models"]:
            assert model["is_available"] is True

    def test_service_payload_shape_matches_descriptor(self):
        import services.core as core_module

        report = core_module.get_routing_models()
        assert report["models"], "catalog should not be empty"
        model = report["models"][0]
        # Both lineage keys are always present (None when absent) —
        # mirrors the auditor's stable-schema convention.
        assert "quantization" in model
        assert "distillation" in model
        assert "cost_per_1k_tokens" in model
        assert "p95_latency_ms" in model
        assert "supports_tool_use" in model
