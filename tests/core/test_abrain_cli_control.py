import importlib
import json

import pytest

pytestmark = pytest.mark.unit


def _module():
    return importlib.import_module("scripts.abrain_control")


def test_task_run_delegates_to_canonical_core(monkeypatch, capsys):
    module = _module()
    captured = {}

    def fake_run_task(payload):
        captured["payload"] = payload
        return {
            "status": "completed",
            "decision": {"selected_agent_id": "agent-1"},
            "execution": {"success": True, "output": {"ok": True}},
            "trace": {"trace_id": "trace-task-1"},
            "warnings": [],
        }

    monkeypatch.setattr("services.core.run_task", fake_run_task)

    exit_code = module.main(
        [
            "task",
            "run",
            "system_status",
            "Check system health",
            "--input",
            "path=services/core.py",
            "--option",
            "timeout=5",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert captured["payload"] == {
        "task_type": "system_status",
        "description": "Check system health",
        "input_data": {"path": "services/core.py"},
        "options": {"timeout": 5},
    }
    assert "Status: completed" in output
    assert "Trace ID: trace-task-1" in output


def test_plan_run_json_mode_surfaces_paused_approval(monkeypatch, capsys):
    module = _module()

    monkeypatch.setattr(
        "services.core.run_task_plan",
        lambda payload: {
            "plan": {"task_id": "plan-1"},
            "result": {"status": "paused", "next_step_id": "deploy"},
            "trace": {"trace_id": "trace-plan-1"},
            "approval": {"approval_id": "approval-1"},
        },
    )

    exit_code = module.main(["plan", "run", "workflow_automation", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["result"]["status"] == "paused"
    assert payload["approval"]["approval_id"] == "approval-1"


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [("approve", "approved"), ("reject", "rejected")],
)
def test_approval_decisions_delegate_to_canonical_core(monkeypatch, capsys, action, expected_status):
    module = _module()
    captured = {}

    def fake_decision(approval_id, *, decided_by, comment=None, rating=None):
        captured["call"] = {
            "approval_id": approval_id,
            "decided_by": decided_by,
            "comment": comment,
            "rating": rating,
        }
        return {
            "approval": {"approval_id": approval_id, "status": expected_status},
            "result": {"status": "completed"},
            "trace": {"trace_id": f"trace-{approval_id}"},
        }

    target = "services.core.approve_plan_step" if action == "approve" else "services.core.reject_plan_step"
    monkeypatch.setattr(target, fake_decision)

    exit_code = module.main(
        [
            "approval",
            action,
            "approval-42",
            "--decided-by",
            "tester",
            "--comment",
            "looks good",
            "--rating",
            "0.9",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert captured["call"] == {
        "approval_id": "approval-42",
        "decided_by": "tester",
        "comment": "looks good",
        "rating": pytest.approx(0.9),
    }
    assert f"Decision status: {expected_status}" in output


def test_approval_list_and_plan_list_delegate(monkeypatch, capsys):
    module = _module()
    monkeypatch.setattr(
        "services.core.list_pending_approvals",
        lambda: {
            "approvals": [
                {
                    "approval_id": "approval-1",
                    "plan_id": "plan-1",
                    "step_id": "deploy",
                    "risk": "high",
                    "requested_at": "2026-04-13T10:00:00Z",
                }
            ]
        },
    )
    monkeypatch.setattr(
        "services.core.list_recent_plans",
        lambda limit=10: {
            "plans": [
                {
                    "plan_id": "plan-1",
                    "status": "paused",
                    "pending_approval_id": "approval-1",
                    "trace_id": "trace-1",
                    "started_at": "2026-04-13T10:00:00Z",
                }
            ]
        },
    )

    approval_exit = module.main(["approval", "list"])
    approval_output = capsys.readouterr().out
    plan_exit = module.main(["plan", "list"])
    plan_output = capsys.readouterr().out

    assert approval_exit == 0
    assert "approval-1" in approval_output
    assert plan_exit == 0
    assert "plan-1" in plan_output


def test_trace_show_and_explain_delegate(monkeypatch, capsys):
    module = _module()
    monkeypatch.setattr(
        "services.core.get_trace",
        lambda trace_id: {
            "trace": {
                "trace": {
                    "trace_id": trace_id,
                    "workflow_name": "run_task",
                    "status": "completed",
                    "task_id": "task-1",
                    "started_at": "2026-04-13T10:00:00Z",
                    "ended_at": "2026-04-13T10:00:05Z",
                    "metadata": {"entrypoint": "run_task"},
                },
                "spans": [
                    {
                        "name": "routing",
                        "span_type": "decision",
                        "status": "completed",
                        "started_at": "2026-04-13T10:00:00Z",
                        "ended_at": "2026-04-13T10:00:01Z",
                    }
                ],
                "explainability": [{"trace_id": trace_id}],
            }
        },
    )
    monkeypatch.setattr(
        "services.core.get_explainability",
        lambda trace_id: {
            "explainability": [
                {
                    "trace_id": trace_id,
                    "step_id": "task",
                    "selected_agent_id": "agent-1",
                    "approval_required": False,
                    "approval_id": None,
                    "matched_policy_ids": ["policy-1"],
                    "routing_reason_summary": "Matched system.status capability.",
                    "metadata": {"selected_score": 0.9},
                }
            ]
        },
    )

    trace_exit = module.main(["trace", "show", "trace-1"])
    trace_output = capsys.readouterr().out
    explain_exit = module.main(["explain", "trace-1"])
    explain_output = capsys.readouterr().out

    assert trace_exit == 0
    assert "Trace ID: trace-1" in trace_output
    assert explain_exit == 0
    assert "Matched system.status capability." in explain_output


def test_agent_list_and_health_use_canonical_views(monkeypatch, capsys):
    module = _module()
    monkeypatch.setattr(
        "services.core.list_agent_catalog",
        lambda: {
            "agents": [
                {
                    "agent_id": "agent-1",
                    "availability": "online",
                    "source_type": "native",
                    "execution_kind": "local_process",
                    "capabilities": ["system.status"],
                }
            ]
        },
    )
    monkeypatch.setattr(
        "services.core.get_control_plane_overview",
        lambda **kwargs: {
            "summary": {
                "agent_count": 1,
                "pending_approvals": 0,
                "recent_traces": 1,
                "recent_plans": 1,
                "recent_governance_events": 1,
            },
            "system": {
                "governance": {
                    "engine": "PolicyEngine",
                    "registry": "PolicyRegistry",
                    "policy_path": None,
                },
                "warnings": [],
            },
            "agents": [{"agent_id": "agent-1"}],
            "pending_approvals": [],
            "recent_traces": [{"trace_id": "trace-1"}],
            "recent_plans": [{"plan_id": "plan-1"}],
            "recent_governance": [{"trace_id": "trace-1", "effect": "allow"}],
        },
    )

    agent_exit = module.main(["agent", "list"])
    agent_output = capsys.readouterr().out
    health_exit = module.main(["health", "--json"])
    health_payload = json.loads(capsys.readouterr().out)

    assert agent_exit == 0
    assert "agent-1" in agent_output
    assert health_exit == 0
    assert health_payload["summary"]["agent_count"] == 1
    assert health_payload["runtime"]["setup_command"] == "./scripts/abrain setup"
