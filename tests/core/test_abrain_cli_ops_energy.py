"""§6.5 – `abrain ops energy` CLI surface tests."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _payload() -> dict:
    return {
        "generated_at": "2026-04-19T00:00:00+00:00",
        "sort_key": "total_energy_joules",
        "descending": True,
        "min_executions": 0,
        "entries": [
            {
                "agent_id": "agent-alpha",
                "avg_power_watts": 250.0,
                "profile_source": "vendor_spec",
                "used_default_profile": False,
                "avg_latency_seconds": 1.2,
                "execution_count": 200,
                "avg_energy_joules": 300.0,
                "total_energy_joules": 60000.0,
                "total_energy_wh": 16.6667,
            },
            {
                "agent_id": "agent-beta",
                "avg_power_watts": 150.0,
                "profile_source": "estimated",
                "used_default_profile": True,
                "avg_latency_seconds": 0.5,
                "execution_count": 50,
                "avg_energy_joules": 75.0,
                "total_energy_joules": 3750.0,
                "total_energy_wh": 1.0417,
            },
        ],
        "totals": {
            "agents": 2,
            "total_executions": 250,
            "total_energy_joules": 63750.0,
            "total_energy_wh": 17.7083,
            "weighted_avg_power_watts": 230.0,
        },
        "fallback_agents": ["agent-beta"],
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_totals_entries_and_fallbacks(self):
        module = _module()
        text = module._render_ops_energy(_payload())
        assert "=== Ops Energy Report (per agent) ===" in text
        assert "Sort key:         total_energy_joules" in text
        assert "descending=True" in text
        assert "Agents reported:           2" in text
        assert "Total energy (J):          63750.0000" in text
        assert "Weighted avg_power_watts:  230.0000" in text
        assert "Fallback agents (1):" in text
        assert "- agent-beta" in text
        assert "agent-alpha" in text
        assert "watts=250.00" in text
        assert "src=vendor_spec" in text
        assert "(fallback)" in text  # beta row marked

    def test_renders_empty_entries_and_no_fallbacks(self):
        module = _module()
        payload = _payload()
        payload["entries"] = []
        payload["fallback_agents"] = []
        payload["totals"] = {
            "agents": 0,
            "total_executions": 0,
            "total_energy_joules": 0.0,
            "total_energy_wh": 0.0,
            "weighted_avg_power_watts": 0.0,
        }
        text = module._render_ops_energy(payload)
        assert "Fallback agents (0):" in text
        assert "Entries (0):" in text
        assert text.count("(none)") == 2  # both sections render (none)

    def test_renders_error_payload(self):
        module = _module()
        text = module._render_ops_energy(
            {"error": "profiles_unreadable", "detail": "FileNotFoundError: missing.json"}
        )
        assert "Energy report unavailable: profiles_unreadable" in text
        assert "FileNotFoundError" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_energy_delegates_to_services_core_with_defaults(
        self, monkeypatch, capsys
    ):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_energy_report", fake)

        exit_code = module.main(
            [
                "ops",
                "energy",
                "--default-watts",
                "300",
            ]
        )
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "default_watts": 300.0,
            "default_source": "estimated",
            "profiles": None,
            "sort_key": "total_energy_joules",
            "descending": True,
            "min_executions": 0,
            "agent_ids": None,
        }
        assert "Ops Energy Report" in output

    def test_energy_clamps_negative_default_watts(self, monkeypatch):
        module = _module()
        captured: dict = {}

        monkeypatch.setattr(
            "services.core.get_energy_report",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "ops",
                "energy",
                "--default-watts",
                "-50",
                "--json",
            ]
        )
        assert captured["default_watts"] == 0.0

    def test_energy_loads_profiles_json(self, monkeypatch, tmp_path: Path):
        module = _module()
        profiles_path = tmp_path / "profiles.json"
        profiles_path.write_text(
            json.dumps(
                {
                    "agent-alpha": {"avg_power_watts": 250, "source": "vendor_spec"},
                    "agent-beta": {"avg_power_watts": 150},
                }
            )
        )
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_energy_report",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "ops",
                "energy",
                "--default-watts",
                "200",
                "--profiles",
                str(profiles_path),
                "--json",
            ]
        )
        assert captured["profiles"] == {
            "agent-alpha": {"avg_power_watts": 250, "source": "vendor_spec"},
            "agent-beta": {"avg_power_watts": 150},
        }

    def test_energy_profiles_unreadable_surfaces_error_payload(
        self, monkeypatch, capsys
    ):
        module = _module()
        calls: dict = {"n": 0}

        def fake(**_):
            calls["n"] += 1
            return _payload()

        monkeypatch.setattr("services.core.get_energy_report", fake)

        exit_code = module.main(
            [
                "ops",
                "energy",
                "--default-watts",
                "100",
                "--profiles",
                "/tmp/does-not-exist-xyz.json",
            ]
        )
        output = capsys.readouterr().out

        assert exit_code == 0
        assert calls["n"] == 0  # service never reached
        assert "Energy report unavailable: profiles_unreadable" in output

    def test_energy_profiles_schema_invalid_surfaces_error_payload(
        self, monkeypatch, capsys, tmp_path: Path
    ):
        module = _module()
        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps(["not", "an", "object"]))

        calls: dict = {"n": 0}
        monkeypatch.setattr(
            "services.core.get_energy_report",
            lambda **_: calls.update({"n": calls["n"] + 1}) or _payload(),
        )

        exit_code = module.main(
            [
                "ops",
                "energy",
                "--default-watts",
                "100",
                "--profiles",
                str(bad_path),
            ]
        )
        output = capsys.readouterr().out
        assert exit_code == 0
        assert calls["n"] == 0
        assert "profiles_schema_invalid" in output

    def test_energy_sort_key_ascending_agents_and_min_executions(
        self, monkeypatch
    ):
        module = _module()
        captured: dict = {}
        monkeypatch.setattr(
            "services.core.get_energy_report",
            lambda **kw: captured.update(kw) or _payload(),
        )

        module.main(
            [
                "ops",
                "energy",
                "--default-watts",
                "100",
                "--sort-key",
                "avg_power_watts",
                "--ascending",
                "--min-executions",
                "-5",
                "--agents",
                " agent-alpha , ,agent-beta",
                "--json",
            ]
        )
        assert captured["sort_key"] == "avg_power_watts"
        assert captured["descending"] is False
        assert captured["min_executions"] == 0
        assert captured["agent_ids"] == ["agent-alpha", "agent-beta"]

    def test_energy_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_energy_report",
            lambda **_: _payload(),
        )

        exit_code = module.main(
            ["ops", "energy", "--default-watts", "100", "--json"]
        )
        output = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["totals"]["agents"] == 2
        assert parsed["fallback_agents"] == ["agent-beta"]


# ---------------------------------------------------------------------------
# Service integration (no monkeypatch – real PerformanceHistoryStore)
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_composes_estimator_over_real_store(self, monkeypatch):
        from core.decision.performance_history import PerformanceHistoryStore

        store = PerformanceHistoryStore()
        store.record_result(
            agent_id="agent-alpha",
            success=True,
            latency=2.0,
            cost=0.05,
            token_count=200,
        )

        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_learning_state",
            lambda: {"perf_history": store},
        )

        report = core_module.get_energy_report(default_watts=300.0)
        assert report["totals"]["agents"] == 1
        entry = report["entries"][0]
        assert entry["agent_id"] == "agent-alpha"
        assert entry["avg_power_watts"] == 300.0
        assert entry["execution_count"] == 1
        # 300 W * 2.0 s = 600 J avg; total = 600 J * 1 exec = 600 J
        assert entry["total_energy_joules"] == pytest.approx(600.0)
        assert report["fallback_agents"] == ["agent-alpha"]

    def test_service_honours_explicit_profile_override(self, monkeypatch):
        from core.decision.performance_history import PerformanceHistoryStore

        store = PerformanceHistoryStore()
        store.record_result(
            agent_id="agent-alpha",
            success=True,
            latency=1.0,
            cost=0.01,
            token_count=100,
        )

        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_learning_state",
            lambda: {"perf_history": store},
        )

        report = core_module.get_energy_report(
            default_watts=100.0,
            profiles={
                "agent-alpha": {"avg_power_watts": 400.0, "source": "measured"}
            },
        )
        entry = report["entries"][0]
        assert entry["avg_power_watts"] == 400.0
        assert entry["profile_source"] == "measured"
        assert entry["used_default_profile"] is False
        assert report["fallback_agents"] == []
