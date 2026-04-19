"""§6.5 – `abrain ops cost` CLI surface tests."""

from __future__ import annotations

import importlib
import json

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def _payload() -> dict:
    return {
        "generated_at": "2026-04-19T00:00:00+00:00",
        "sort_key": "avg_cost",
        "descending": True,
        "min_executions": 0,
        "entries": [
            {
                "agent_id": "agent-alpha",
                "success_rate": 0.95,
                "avg_latency": 1.25,
                "avg_cost": 0.08,
                "avg_token_count": 512.0,
                "avg_user_rating": 4.5,
                "recent_failures": 1,
                "execution_count": 200,
                "load_factor": 0.3,
            },
            {
                "agent_id": "agent-beta",
                "success_rate": 0.8,
                "avg_latency": 2.5,
                "avg_cost": 0.02,
                "avg_token_count": 128.0,
                "avg_user_rating": 3.5,
                "recent_failures": 5,
                "execution_count": 50,
                "load_factor": 0.1,
            },
        ],
        "totals": {
            "agents": 2,
            "total_executions": 250,
            "total_recent_failures": 6,
            "weighted_success_rate": 0.92,
            "weighted_avg_latency": 1.5,
            "weighted_avg_cost": 0.068,
        },
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_renders_totals_and_entries(self):
        module = _module()
        text = module._render_ops_cost(_payload())
        assert "=== Ops Cost Report (per agent) ===" in text
        assert "Sort key:         avg_cost" in text
        assert "descending=True" in text
        assert "Agents reported:         2" in text
        assert "Total executions:        250" in text
        assert "Weighted avg_cost:       0.0680" in text
        assert "agent-alpha" in text
        assert "execs=200" in text
        assert "avg_cost=0.0800" in text

    def test_renders_empty_entry_list_as_none(self):
        module = _module()
        payload = _payload()
        payload["entries"] = []
        payload["totals"] = {
            "agents": 0,
            "total_executions": 0,
            "total_recent_failures": 0,
            "weighted_success_rate": 0.0,
            "weighted_avg_latency": 0.0,
            "weighted_avg_cost": 0.0,
        }
        text = module._render_ops_cost(payload)
        assert "Entries (0):" in text
        assert "(none)" in text

    def test_renders_overflow_tail_for_many_entries(self):
        module = _module()
        payload = _payload()
        payload["entries"] = [
            {
                "agent_id": f"agent-{idx}",
                "success_rate": 0.9,
                "avg_latency": 1.0,
                "avg_cost": 0.01,
                "avg_token_count": 10.0,
                "avg_user_rating": 4.0,
                "recent_failures": 0,
                "execution_count": 1,
                "load_factor": 0.0,
            }
            for idx in range(25)
        ]
        text = module._render_ops_cost(payload)
        assert "Entries (25):" in text
        assert "... (5 more)" in text


# ---------------------------------------------------------------------------
# Argument parsing / service wiring
# ---------------------------------------------------------------------------


class TestCliWiring:
    def test_cost_delegates_to_services_core_with_defaults(
        self, monkeypatch, capsys
    ):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_agent_performance_report", fake)

        exit_code = module.main(["ops", "cost"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert captured == {
            "sort_key": "avg_cost",
            "descending": True,
            "min_executions": 0,
            "agent_ids": None,
        }
        assert "Ops Cost Report" in output

    def test_cost_sort_key_and_ascending_flag(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_agent_performance_report", fake)

        module.main(
            [
                "ops",
                "cost",
                "--sort-key",
                "avg_latency",
                "--ascending",
                "--json",
            ]
        )
        assert captured["sort_key"] == "avg_latency"
        assert captured["descending"] is False

    def test_cost_agents_split_and_trim(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_agent_performance_report", fake)

        module.main(
            [
                "ops",
                "cost",
                "--agents",
                " agent-alpha , agent-beta , ,agent-gamma",
                "--json",
            ]
        )
        assert captured["agent_ids"] == ["agent-alpha", "agent-beta", "agent-gamma"]

    def test_cost_clamps_min_executions_negative(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return _payload()

        monkeypatch.setattr("services.core.get_agent_performance_report", fake)

        module.main(
            [
                "ops",
                "cost",
                "--min-executions",
                "-7",
                "--json",
            ]
        )
        assert captured["min_executions"] == 0

    def test_cost_json_mode_emits_dumpable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.get_agent_performance_report",
            lambda **_: _payload(),
        )

        exit_code = module.main(["ops", "cost", "--json"])
        output = capsys.readouterr().out

        assert exit_code == 0
        parsed = json.loads(output)
        assert parsed["totals"]["agents"] == 2
        assert parsed["entries"][0]["agent_id"] == "agent-alpha"


# ---------------------------------------------------------------------------
# Service integration (no monkeypatch – real PerformanceHistoryStore)
# ---------------------------------------------------------------------------


class TestServiceIntegration:
    def test_service_wraps_real_reporter_over_perf_history(self, monkeypatch, tmp_path):
        from core.decision.performance_history import PerformanceHistoryStore

        store = PerformanceHistoryStore()
        store.record_result(
            agent_id="agent-alpha",
            success=True,
            latency=1.0,
            cost=0.05,
            token_count=200,
        )
        store.record_result(
            agent_id="agent-alpha",
            success=True,
            latency=1.5,
            cost=0.07,
            token_count=250,
        )

        import services.core as core_module

        monkeypatch.setattr(
            core_module,
            "_get_learning_state",
            lambda: {"perf_history": store},
        )

        report = core_module.get_agent_performance_report(min_executions=1)
        assert report["totals"]["agents"] == 1
        assert report["entries"][0]["agent_id"] == "agent-alpha"
        assert report["entries"][0]["execution_count"] == 2
