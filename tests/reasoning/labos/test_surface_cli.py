"""CLI surface tests — `abrain reasoning labos <mode>`.

Pin that the CLI is a pure delegate of `services.core.run_labos_reasoning`:
no mode-specific logic, no second response shape, clean error handling on
invalid input / unknown mode.
"""

from __future__ import annotations

import importlib
import json
import textwrap

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


_SAMPLE_CONTEXT = {
    "reactors": [
        {"reactor_id": "R1", "display_name": "Reactor One", "status": "warning"},
    ],
    "action_catalog": [
        {"action_name": "open_reactor_detail", "requires_approval": False},
    ],
}

_MODES = (
    "reactor_daily_overview",
    "incident_review",
    "maintenance_suggestions",
    "schedule_runtime_review",
    "cross_domain_overview",
    "module_daily_overview",
    "module_incident_review",
    "module_coordination_review",
    "module_capability_risk_review",
    "robotops_cross_domain_overview",
)


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------


class TestCliDelegation:
    @pytest.mark.parametrize("mode", _MODES)
    def test_cli_invokes_service_with_mode_and_context(self, monkeypatch, mode, tmp_path):
        module = _module()
        captured: dict = {}

        def fake(mode_arg, context_arg):
            captured["mode"] = mode_arg
            captured["context"] = context_arg
            return {
                "reasoning_mode": f"labos_{mode_arg}",
                "summary": "x",
                "highlights": [],
                "prioritized_entities": [],
                "recommended_actions": [],
                "recommended_checks": [],
                "approval_required_actions": [],
                "blocked_or_deferred_actions": [],
                "used_context_sections": [],
                "trace_metadata": {},
            }

        monkeypatch.setattr("services.core.run_labos_reasoning", fake)

        ctx_path = tmp_path / "ctx.json"
        ctx_path.write_text(json.dumps(_SAMPLE_CONTEXT), encoding="utf-8")

        exit_code = module.main(
            ["reasoning", "labos", mode, "--input", str(ctx_path), "--json"]
        )

        assert exit_code == 0
        assert captured["mode"] == mode
        assert captured["context"] == _SAMPLE_CONTEXT

    def test_input_json_string_parses_to_dict(self, monkeypatch):
        module = _module()
        captured: dict = {}

        def fake(mode_arg, context_arg):
            captured["context"] = context_arg
            return {"reasoning_mode": "labos_x", "summary": ""}

        monkeypatch.setattr("services.core.run_labos_reasoning", fake)

        module.main(
            [
                "reasoning",
                "labos",
                "reactor_daily_overview",
                "--input-json",
                json.dumps(_SAMPLE_CONTEXT),
                "--json",
            ]
        )
        assert captured["context"] == _SAMPLE_CONTEXT

    def test_stdin_input_parses(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.run_labos_reasoning",
            lambda mode, ctx: {"reasoning_mode": "x", "summary": "", **{
                k: [] for k in [
                    "highlights","prioritized_entities","recommended_actions",
                    "recommended_checks","approval_required_actions",
                    "blocked_or_deferred_actions","used_context_sections",
                ]
            }, "trace_metadata": {}},
        )
        monkeypatch.setattr(
            "sys.stdin",
            __import__("io").StringIO(json.dumps(_SAMPLE_CONTEXT)),
        )
        exit_code = module.main(
            ["reasoning", "labos", "reactor_daily_overview", "--stdin", "--json"]
        )
        assert exit_code == 0


# ---------------------------------------------------------------------------
# Output format + error handling
# ---------------------------------------------------------------------------


class TestCliOutput:
    def test_json_mode_emits_parseable_payload(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.run_labos_reasoning",
            lambda mode, ctx: {
                "reasoning_mode": "labos_reactor_daily_overview",
                "summary": "ok",
                "highlights": ["hi"],
                "prioritized_entities": [],
                "recommended_actions": [],
                "recommended_checks": [],
                "approval_required_actions": [],
                "blocked_or_deferred_actions": [],
                "used_context_sections": ["reactors"],
                "trace_metadata": {},
            },
        )
        exit_code = module.main(
            [
                "reasoning", "labos", "reactor_daily_overview",
                "--input-json", "{}",
                "--json",
            ]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(out)
        assert parsed["reasoning_mode"] == "labos_reactor_daily_overview"
        assert parsed["summary"] == "ok"

    def test_text_mode_renders_summary_and_counts(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.run_labos_reasoning",
            lambda mode, ctx: {
                "reasoning_mode": "labos_incident_review",
                "summary": "2 total open (1 critical, 1 warning)",
                "highlights": ["I-crit: critical"],
                "prioritized_entities": [
                    {
                        "entity_type": "incident",
                        "entity_id": "I-crit",
                        "priority_bucket": "critical",
                        "priority_rank": 1,
                        "priority_reason": "critical severity",
                    }
                ],
                "recommended_actions": [],
                "recommended_checks": [],
                "approval_required_actions": [],
                "blocked_or_deferred_actions": [],
                "used_context_sections": ["incidents"],
                "trace_metadata": {},
            },
        )
        exit_code = module.main(
            ["reasoning", "labos", "incident_review", "--input-json", "{}"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "labos_incident_review" in out
        assert "2 total open" in out
        assert "I-crit" in out

    def test_invalid_context_exits_nonzero(self, monkeypatch, capsys):
        module = _module()
        monkeypatch.setattr(
            "services.core.run_labos_reasoning",
            lambda mode, ctx: {
                "error": "invalid_context",
                "detail": [{"loc": "incidents", "msg": "bad"}],
            },
        )
        exit_code = module.main(
            ["reasoning", "labos", "incident_review", "--input-json", "{}"]
        )
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "invalid_context" in out

    def test_unknown_mode_rejected_by_argparse(self, capsys):
        module = _module()
        with pytest.raises(SystemExit) as exc_info:
            module.main(
                ["reasoning", "labos", "not_a_real_mode", "--input-json", "{}"]
            )
        # argparse exits with code 2 for invalid choice
        assert exc_info.value.code == 2

    def test_multiple_inputs_rejected(self, monkeypatch, capsys):
        module = _module()
        # Must error cleanly even before calling the service.
        called = False

        def never(*a, **k):
            nonlocal called
            called = True
            return {}

        monkeypatch.setattr("services.core.run_labos_reasoning", never)
        exit_code = module.main(
            [
                "reasoning", "labos", "reactor_daily_overview",
                "--input-json", "{}",
                "--stdin",
            ]
        )
        assert exit_code == 2  # CliUsageError path
        assert called is False

    def test_input_json_non_object_rejected(self, monkeypatch):
        module = _module()
        exit_code = module.main(
            [
                "reasoning", "labos", "reactor_daily_overview",
                "--input-json", "[1, 2, 3]",
            ]
        )
        assert exit_code == 2
