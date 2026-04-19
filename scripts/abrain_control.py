"""Internal control-plane bridge used by the canonical Bash CLI.

This module is not a second user-facing CLI. `scripts/abrain` remains the
single entrypoint and delegates selected developer/operator commands here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = REPO_ROOT / ".abrain"
DEFAULT_CONFIG_FILE = DEFAULT_STATE_DIR / "config.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class CliUsageError(ValueError):
    """Raised when CLI input is invalid after argument parsing."""


def _load_core():
    from services import core

    return core


def _json_mode(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False) or os.getenv("ABRAIN_OUTPUT") == "json")


def _emit(payload: Any, renderer, *, json_mode: bool) -> int:
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    text = renderer(payload)
    if text:
        print(text)
    return 0


def _coerce_scalar(value: str) -> Any:
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def _parse_key_values(values: list[str], *, label: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise CliUsageError(f"{label} erwartet KEY=VALUE, erhalten: {item!r}")
        key, raw_value = item.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            raise CliUsageError(f"{label} erwartet KEY=VALUE, erhalten: {item!r}")
        parsed[normalized_key] = _coerce_scalar(raw_value)
    return parsed


def _parse_json_object(raw: str | None, *, label: str) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliUsageError(f"{label} muss valides JSON sein: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise CliUsageError(f"{label} muss ein JSON-Objekt sein")
    return value


def _resolve_description(args: argparse.Namespace) -> str | None:
    positional = getattr(args, "description_text", None)
    explicit = getattr(args, "description", None)
    if positional and explicit and positional != explicit:
        raise CliUsageError("Beschreibung nur einmal angeben: positional oder --description")
    return explicit or positional


def _build_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    input_data = _parse_key_values(list(getattr(args, "input", []) or []), label="--input")
    input_data.update(_parse_json_object(getattr(args, "input_json", None), label="--input-json"))

    options = _parse_key_values(list(getattr(args, "option", []) or []), label="--option")
    options.update(_parse_json_object(getattr(args, "option_json", None), label="--option-json"))

    payload: dict[str, Any] = {
        "task_type": args.task_type,
        "input_data": input_data,
        "options": options,
    }
    description = _resolve_description(args)
    if description:
        payload["description"] = description
    if getattr(args, "task_id", None):
        payload["task_id"] = args.task_id
    return payload


def _runtime_dir() -> Path:
    return DEFAULT_STATE_DIR


def _runtime_config_path() -> Path:
    return DEFAULT_CONFIG_FILE


def _python_entry() -> str:
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _mcp_entry() -> str:
    entrypoint = REPO_ROOT / ".venv" / "bin" / "abrain-mcp"
    if entrypoint.exists():
        return str(entrypoint)
    return f"{_python_entry()} -m interfaces.mcp.server"


def _runtime_overview() -> dict[str, Any]:
    return {
        "repo_root": str(REPO_ROOT),
        "runtime_dir": str(_runtime_dir()),
        "config_file": str(_runtime_config_path()),
        "env_file": str(REPO_ROOT / ".env"),
        "env_present": (REPO_ROOT / ".env").exists(),
        "setup_command": "./scripts/abrain setup",
        "api_start_command": f"{_python_entry()} -m uvicorn api_gateway.main:app --reload",
        "mcp_start_command": _mcp_entry(),
    }


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    rendered = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * widths[index] for index in range(len(headers))),
    ]
    for row in rows:
        rendered.append("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    return "\n".join(rendered)


def _indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in text.splitlines())


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _render_run_result(kind: str, payload: dict[str, Any]) -> str:
    status = payload.get("status") or payload.get("result", {}).get("status") or "unknown"
    trace = payload.get("trace") or {}
    trace_id = trace.get("trace_id") or "n/a"
    decision = payload.get("decision") or {}
    result = payload.get("result") or {}
    execution = payload.get("execution") or {}
    approval = payload.get("approval") or {}

    lines = [
        f"{kind.title()} run",
        f"Status: {status}",
        f"Trace ID: {trace_id}",
    ]
    selected_agent = (
        decision.get("selected_agent_id")
        or execution.get("agent_id")
        or result.get("selected_agent_id")
    )
    if selected_agent:
        lines.append(f"Selected agent: {selected_agent}")
    if kind == "plan":
        plan = payload.get("plan") or {}
        plan_id = result.get("plan_id") or plan.get("task_id")
        if plan_id:
            lines.append(f"Plan ID: {plan_id}")
    if approval:
        approval_id = approval.get("approval_id")
        if approval_id:
            lines.append(f"Pending approval: {approval_id}")

    warnings = payload.get("warnings") or result.get("warnings") or []
    if warnings:
        lines.append(f"Warnings: {', '.join(str(item) for item in warnings)}")

    if execution:
        lines.append(f"Execution success: {execution.get('success')}")
        output = execution.get("output")
        if output not in (None, {}, []):
            lines.append("Execution output:")
            lines.append(_indent(json.dumps(output, indent=2, sort_keys=True)))
        error = execution.get("error")
        if error:
            lines.append("Execution error:")
            lines.append(_indent(json.dumps(error, indent=2, sort_keys=True)))

    if result:
        next_step_id = result.get("next_step_id")
        if next_step_id:
            lines.append(f"Next step: {next_step_id}")
        outputs = result.get("outputs")
        if outputs not in (None, {}, []):
            lines.append("Plan outputs:")
            lines.append(_indent(json.dumps(outputs, indent=2, sort_keys=True)))

    governance = payload.get("governance") or {}
    if governance:
        effect = governance.get("effect")
        if effect:
            lines.append(f"Governance effect: {effect}")
    return "\n".join(lines)


def _render_approval_list(payload: dict[str, Any]) -> str:
    approvals = payload.get("approvals", [])
    if not approvals:
        return "No pending approvals."
    rows = [
        [
            str(item.get("approval_id") or "-"),
            str(item.get("plan_id") or "-"),
            str(item.get("step_id") or "-"),
            str(item.get("risk") or "-"),
            str(item.get("requested_at") or "-"),
        ]
        for item in approvals
    ]
    return "\n".join(
        [
            f"Pending approvals: {len(approvals)}",
            _format_table(["approval_id", "plan_id", "step_id", "risk", "requested_at"], rows),
        ]
    )


def _render_approval_decision(payload: dict[str, Any]) -> str:
    approval = payload.get("approval") or {}
    result = payload.get("result") or {}
    trace = payload.get("trace") or {}
    lines = [
        "Approval decision applied",
        f"Approval ID: {approval.get('approval_id', 'n/a')}",
        f"Decision status: {approval.get('status', 'unknown')}",
        f"Plan result: {result.get('status', 'unknown')}",
        f"Trace ID: {trace.get('trace_id', 'n/a')}",
    ]
    next_step_id = result.get("next_step_id")
    if next_step_id:
        lines.append(f"Next step: {next_step_id}")
    return "\n".join(lines)


def _render_trace_list(payload: dict[str, Any]) -> str:
    traces = payload.get("traces", [])
    if not traces:
        return "No traces found."
    rows = [
        [
            str(item.get("trace_id") or "-"),
            str(item.get("workflow_name") or "-"),
            str(item.get("status") or "-"),
            str(item.get("task_id") or "-"),
            str(item.get("started_at") or "-"),
        ]
        for item in traces
    ]
    return "\n".join(
        [
            f"Recent traces: {len(traces)}",
            _format_table(["trace_id", "workflow", "status", "task_id", "started_at"], rows),
        ]
    )


def _render_trace_show(payload: dict[str, Any]) -> str:
    snapshot = payload.get("trace")
    if not snapshot:
        return "Trace not found."
    trace = snapshot.get("trace") or {}
    spans = snapshot.get("spans") or []
    lines = [
        "Trace snapshot",
        f"Trace ID: {trace.get('trace_id', 'n/a')}",
        f"Workflow: {trace.get('workflow_name', 'n/a')}",
        f"Status: {trace.get('status', 'unknown')}",
        f"Task ID: {trace.get('task_id') or '-'}",
        f"Started: {trace.get('started_at', '-')}",
        f"Ended: {trace.get('ended_at') or '-'}",
    ]
    metadata = trace.get("metadata") or {}
    if metadata:
        lines.append("Metadata:")
        lines.append(_indent(json.dumps(metadata, indent=2, sort_keys=True)))
    if spans:
        rows = [
            [
                str(item.get("name") or "-"),
                str(item.get("span_type") or "-"),
                str(item.get("status") or "-"),
                str(item.get("started_at") or "-"),
                str(item.get("ended_at") or "-"),
            ]
            for item in spans
        ]
        lines.append("Spans:")
        lines.append(_format_table(["name", "type", "status", "started_at", "ended_at"], rows))
    explainability = snapshot.get("explainability") or []
    if explainability:
        lines.append(f"Decision steps ({len(explainability)}):")
        rows = [
            [
                str(item.get("step_id") or "task"),
                str(item.get("selected_agent_id") or "-"),
                _fmt_score(item.get("selected_score")),
                str(item.get("confidence_band") or "-"),
                str(item.get("policy_effect") or "-"),
                "yes" if item.get("approval_required") else "no",
            ]
            for item in explainability
        ]
        lines.append(
            _format_table(
                ["step_id", "selected_agent", "score", "confidence", "policy_effect", "approval"],
                rows,
            )
        )
    replay = snapshot.get("replay_descriptor")
    if replay:
        can = "yes" if replay.get("can_replay") else "no"
        missing = ", ".join(replay.get("missing_inputs") or []) or "-"
        lines.append(f"Replay-readiness: can_replay={can}  missing={missing}")
    return "\n".join(lines)


def _fmt_score(value: Any) -> str:
    """Format a float score for table display."""
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    return "-"


def _render_explainability(payload: dict[str, Any]) -> str:
    records = payload.get("explainability", [])
    if not records:
        return "No explainability records found."
    rows = [
        [
            str(item.get("step_id") or "task"),
            str(item.get("selected_agent_id") or "-"),
            _fmt_score(item.get("selected_score")),
            _fmt_score(item.get("routing_confidence")),
            str(item.get("confidence_band") or "-"),
            _fmt_score(item.get("score_gap")),
            str(item.get("policy_effect") or "-"),
            "yes" if item.get("approval_required") else "no",
        ]
        for item in records
    ]
    sections = [
        f"Explainability records: {len(records)}",
        _format_table(
            ["step_id", "selected_agent", "score", "confidence", "band", "gap", "policy_effect", "approval"],
            rows,
        ),
    ]
    for item in records:
        step_id = item.get("step_id") or "task"
        reason = item.get("routing_reason_summary", "")
        sections.append(f"[{step_id}] {reason}".strip())
        scored = item.get("scored_candidates") or []
        if scored:
            candidate_rows = [
                [
                    str(c.get("agent_id") or "-"),
                    _fmt_score(c.get("score")),
                    _fmt_score(c.get("capability_match_score")),
                ]
                for c in scored
            ]
            sections.append(
                _indent(_format_table(["agent_id", "score", "cap_match"], candidate_rows))
            )
    return "\n".join(sections)


def _render_trace_drilldown(payload: dict[str, Any]) -> str:
    """Forensics drilldown — structured decision reconstruction for a trace."""
    snapshot = payload.get("trace")
    if not snapshot:
        return "Trace not found."
    trace = snapshot.get("trace") or {}
    explainability = snapshot.get("explainability") or []
    replay = snapshot.get("replay_descriptor")

    lines = [
        "=== Trace Forensics Drilldown ===",
        f"Trace ID:   {trace.get('trace_id', 'n/a')}",
        f"Workflow:   {trace.get('workflow_name', 'n/a')}",
        f"Status:     {trace.get('status', 'unknown')}",
        f"Task ID:    {trace.get('task_id') or '-'}",
        f"Started:    {trace.get('started_at', '-')}",
        f"Ended:      {trace.get('ended_at') or '-'}",
        "",
    ]

    if not explainability:
        lines.append("No decision records found.")
    else:
        lines.append(f"Decision path  ({len(explainability)} step(s)):")
        for i, exp in enumerate(explainability, 1):
            step_id = exp.get("step_id") or "task"
            selected = exp.get("selected_agent_id") or "none"
            score = exp.get("selected_score")
            confidence = exp.get("routing_confidence")
            band = exp.get("confidence_band") or "-"
            gap = exp.get("score_gap")
            policy_effect = exp.get("policy_effect") or "allow"
            approval_req = exp.get("approval_required", False)
            approval_id = exp.get("approval_id")

            score_str = f"  score={score:.3f}" if isinstance(score, float) else ""
            conf_str = f"  routing_confidence={confidence:.3f}" if isinstance(confidence, float) else ""
            gap_str = f"  gap={gap:.3f}" if isinstance(gap, float) else ""

            lines.append(f"  Step {i}: [{step_id}]")
            lines.append(f"    Selected:    {selected}{score_str}")
            lines.append(f"    Confidence:  band={band}{conf_str}{gap_str}")
            lines.append(
                f"    Policy:      {policy_effect}"
                + (" [APPROVAL REQUIRED]" if approval_req else "")
            )
            if approval_id:
                lines.append(f"    Approval ID: {approval_id}")

            # Ranked candidate table
            scored_candidates = exp.get("scored_candidates") or []
            if scored_candidates:
                candidate_rows = [
                    [
                        str(c.get("agent_id") or "-"),
                        _fmt_score(c.get("score")),
                        _fmt_score(c.get("capability_match_score")),
                    ]
                    for c in scored_candidates
                ]
                lines.append("    Candidates:")
                lines.append(
                    _indent(
                        _format_table(["agent_id", "score", "cap_match"], candidate_rows),
                        "      ",
                    )
                )
            elif exp.get("candidate_agent_ids"):
                ids = ", ".join(exp["candidate_agent_ids"])
                lines.append(f"    Candidates:  {ids}")

            matched = exp.get("matched_policy_ids") or []
            if matched:
                lines.append(f"    Policies:    {', '.join(matched)}")

            reason = exp.get("routing_reason_summary", "")
            if reason:
                lines.append(f"    Reason:      {reason}")

            lines.append("")

    # Replay-readiness summary
    if replay:
        can_replay = replay.get("can_replay", False)
        task_type = replay.get("task_type") or "-"
        missing = replay.get("missing_inputs") or []
        lines.append("Replay readiness:")
        lines.append(f"  can_replay:  {'yes' if can_replay else 'no'}")
        lines.append(f"  task_type:   {task_type}")
        if missing:
            lines.append(f"  missing:     {', '.join(missing)}")
        meta = replay.get("metadata") or {}
        if meta.get("plan_id"):
            lines.append(f"  plan_id:     {meta['plan_id']}")
        if meta.get("strategy"):
            lines.append(f"  strategy:    {meta['strategy']}")

    return "\n".join(lines)


def _render_trace_replay(payload: dict[str, Any] | None) -> str:
    """Render a TraceEvaluationResult as a human-readable replay report."""
    if payload is None:
        return "Trace not found."

    trace_id = payload.get("trace_id", "n/a")
    workflow = payload.get("workflow_name", "n/a")
    can_replay = payload.get("can_replay", False)
    has_regression = payload.get("has_any_regression", False)

    lines = [
        "=== Trace Replay Report ===",
        f"Trace ID:   {trace_id}",
        f"Workflow:   {workflow}",
        f"Replayable: {'yes' if can_replay else 'no'}",
        f"Regression: {'YES' if has_regression else 'none'}",
        "",
    ]

    step_results = payload.get("step_results") or []
    if not step_results:
        lines.append("No decision steps to evaluate.")
    else:
        lines.append(f"Step results ({len(step_results)}):")
        for step in step_results:
            step_id = step.get("step_id", "?")
            regression_flag = "  [REGRESSION]" if step.get("has_regression") else ""
            lines.append(f"  Step [{step_id}]{regression_flag}")

            r = step.get("routing") or {}
            verdict = r.get("verdict", "n/a")
            stored = r.get("stored_agent_id") or "-"
            current = r.get("current_agent_id") or "-"
            reason = r.get("reason") or r.get("non_replayable_reason") or ""
            lines.append(f"    Routing:  {verdict}  {stored!r} → {current!r}")
            if reason:
                lines.append(f"             {reason}")

            p = step.get("policy")
            if p:
                pv = p.get("verdict", "n/a")
                se = p.get("stored_effect") or "-"
                ce = p.get("current_effect") or "-"
                ap = "approval changed" if not p.get("approval_consistency", True) else ""
                lines.append(f"    Policy:   {pv}  {se!r} → {ce!r}  {ap}".rstrip())

            lines.append("")

    summary = payload.get("summary") or {}
    lines.append(
        f"Summary: steps={summary.get('step_count', 0)}  "
        f"routing_match={payload.get('routing_match_count', 0)}  "
        f"routing_regression={payload.get('routing_regression_count', 0)}  "
        f"policy_compliant={payload.get('policy_compliant_count', 0)}  "
        f"policy_regression={payload.get('policy_regression_count', 0)}"
    )
    return "\n".join(lines)


def _render_compliance_baselines(payload: dict[str, Any]) -> str:
    """Render a BatchEvaluationReport as a human-readable baseline summary."""
    lines = [
        "=== Evaluation Baselines ===",
        f"Computed at:        {payload.get('computed_at', '-')}",
        f"Traces examined:    {payload.get('trace_count', 0)}",
        f"Replayable traces:  {payload.get('replayable_count', 0)}",
        f"Total steps:        {payload.get('evaluated_step_count', 0)}",
        f"Non-replayable:     {payload.get('non_replayable_step_count', 0)}",
        "",
        "Routing:",
    ]

    rmr = payload.get("routing_match_rate")
    lines.append(
        f"  Match rate:        {f'{rmr:.1%}' if rmr is not None else 'n/a'}"
        f"  (exact={payload.get('routing_exact_match_count', 0)}"
        f"  variation={payload.get('routing_acceptable_variation_count', 0)}"
        f"  regression={payload.get('routing_regression_count', 0)})"
    )
    avg_conf = payload.get("avg_routing_confidence")
    lines.append(f"  Avg confidence:    {f'{avg_conf:.3f}' if avg_conf is not None else 'n/a'}")

    band_dist = payload.get("confidence_band_distribution") or {}
    if band_dist:
        dist_str = "  ".join(f"{k}={v}" for k, v in sorted(band_dist.items()))
        lines.append(f"  Band distribution: {dist_str}")

    lines.append("")
    lines.append("Policy compliance:")
    pcr = payload.get("policy_compliance_rate")
    lines.append(
        f"  Compliance rate:   {f'{pcr:.1%}' if pcr is not None else 'n/a'}"
        f"  (compliant={payload.get('policy_compliant_count', 0)}"
        f"  tightened={payload.get('policy_tightened_count', 0)}"
        f"  regression={payload.get('policy_regression_count', 0)})"
    )
    acr = payload.get("approval_consistency_rate")
    lines.append(f"  Approval consistency: {f'{acr:.1%}' if acr is not None else 'n/a'}")

    reg = payload.get("traces_with_regression", 0)
    lines.append("")
    lines.append(f"Traces with any regression: {reg}")

    return "\n".join(lines)


def _render_plan_list(payload: dict[str, Any]) -> str:
    plans = payload.get("plans", [])
    if not plans:
        return "No plans found."
    rows = [
        [
            str(item.get("plan_id") or "-"),
            str(item.get("status") or "-"),
            str(item.get("pending_approval_id") or "-"),
            str(item.get("trace_id") or "-"),
            str(item.get("started_at") or "-"),
        ]
        for item in plans
    ]
    return "\n".join(
        [
            f"Recent plans: {len(plans)}",
            _format_table(["plan_id", "status", "pending_approval", "trace_id", "started_at"], rows),
        ]
    )


def _render_agent_list(payload: dict[str, Any]) -> str:
    agents = payload.get("agents", [])
    if not agents:
        return "No agents found."
    rows = [
        [
            str(item.get("agent_id") or "-"),
            str(item.get("availability") or "-"),
            str(item.get("source_type") or "-"),
            str(item.get("execution_kind") or "-"),
            _format_quality(item.get("quality")),
            _format_exec_protocol(item.get("execution_capabilities")),
            ",".join(str(cap) for cap in item.get("capabilities") or []) or "-",
        ]
        for item in agents
    ]
    return "\n".join(
        [
            f"Registered agents: {len(agents)}",
            _format_table(
                ["agent_id", "availability", "source", "execution", "quality", "protocol", "capabilities"],
                rows,
            ),
        ]
    )


def _format_quality(quality: Any) -> str:
    """Format quality dict as 'band(score)' or '-' when absent."""
    if not isinstance(quality, dict):
        return "-"
    band = quality.get("quality_band") or "-"
    score = quality.get("quality_score")
    if score is not None:
        return f"{band}({score:.2f})"
    return band


def _format_exec_protocol(exec_caps: Any) -> str:
    """Format execution_capabilities dict as 'protocol[net][proc]' or '-'."""
    if not isinstance(exec_caps, dict):
        return "-"
    proto = exec_caps.get("execution_protocol") or "-"
    flags = ""
    if exec_caps.get("requires_network"):
        flags += "N"
    if exec_caps.get("requires_local_process"):
        flags += "L"
    return f"{proto}[{flags}]" if flags else proto


def _render_health(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    system = payload.get("system") or {}
    runtime = payload.get("runtime") or {}
    lines = [
        "ABrain health",
        f"Agents visible: {summary.get('agent_count', 0)}",
        f"Pending approvals: {summary.get('pending_approvals', 0)}",
        f"Recent traces: {summary.get('recent_traces', 0)}",
        f"Recent plans: {summary.get('recent_plans', 0)}",
        f"Recent governance events: {summary.get('recent_governance_events', 0)}",
    ]
    governance = system.get("governance") or {}
    if governance:
        lines.extend(
            [
                f"Policy engine: {governance.get('engine', '-')}",
                f"Policy registry: {governance.get('registry', '-')}",
                f"Policy path: {governance.get('policy_path') or '-'}",
            ]
        )
    warnings = system.get("warnings") or []
    if warnings:
        lines.append(f"Warnings: {', '.join(str(item) for item in warnings)}")
    lines.extend(
        [
            f"Runtime dir: {runtime.get('runtime_dir', '-')}",
            f"Config file: {runtime.get('config_file', '-')}",
            f".env present: {runtime.get('env_present', False)}",
            f"Setup path: {runtime.get('setup_command', '-')}",
            f"API start path: {runtime.get('api_start_command', '-')}",
            f"MCP start path: {runtime.get('mcp_start_command', '-')}",
        ]
    )
    return "\n".join(lines)


def _handle_task_run(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.run_task(_build_run_payload(args))
    return _emit(payload, lambda value: _render_run_result("task", value), json_mode=_json_mode(args))


def _handle_plan_run(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.run_task_plan(_build_run_payload(args))
    return _emit(payload, lambda value: _render_run_result("plan", value), json_mode=_json_mode(args))


def _handle_plan_list(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.list_recent_plans(limit=max(1, args.limit))
    return _emit(payload, _render_plan_list, json_mode=_json_mode(args))


def _handle_approval_list(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.list_pending_approvals()
    payload = {"approvals": payload.get("approvals", [])[: max(0, args.limit)]}
    return _emit(payload, _render_approval_list, json_mode=_json_mode(args))


def _handle_approval_decision(args: argparse.Namespace) -> int:
    core = _load_core()
    handler = core.approve_plan_step if args.action == "approve" else core.reject_plan_step
    payload = handler(
        args.approval_id,
        decided_by=args.decided_by,
        comment=args.comment,
        rating=args.rating,
    )
    return _emit(payload, _render_approval_decision, json_mode=_json_mode(args))


def _handle_trace_list(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.list_recent_traces(limit=max(1, args.limit))
    return _emit(payload, _render_trace_list, json_mode=_json_mode(args))


def _handle_trace_show(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_trace(args.trace_id)
    return _emit(payload, _render_trace_show, json_mode=_json_mode(args))


def _handle_explain(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_explainability(args.trace_id)
    return _emit(payload, _render_explainability, json_mode=_json_mode(args))


def _handle_trace_drilldown(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_trace(args.trace_id)
    return _emit(payload, _render_trace_drilldown, json_mode=_json_mode(args))


def _handle_trace_replay(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.evaluate_trace(args.trace_id)
    return _emit(payload, _render_trace_replay, json_mode=_json_mode(args))


def _handle_compliance_check(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.evaluate_trace(args.trace_id)
    return _emit(payload, _render_trace_replay, json_mode=_json_mode(args))


def _handle_compliance_baselines(args: argparse.Namespace) -> int:
    core = _load_core()
    limit = max(1, getattr(args, "limit", 100))
    payload = core.compute_evaluation_baselines(limit=limit)
    return _emit(payload, _render_compliance_baselines, json_mode=_json_mode(args))


def _handle_agent_list(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.list_agent_catalog()
    payload = {"agents": payload.get("agents", [])[: max(0, args.limit)]}
    return _emit(payload, _render_agent_list, json_mode=_json_mode(args))


def _render_brain_status(payload: dict[str, Any]) -> str:
    """Render a BrainOperationsReport for operator review."""
    if "error" in payload:
        return (
            f"[WARN] Brain status unavailable: {payload['error']}\n"
            f"       trace_store_path={payload.get('trace_store_path', '-')}"
        )

    baseline = payload.get("baseline") or {}
    overall = baseline.get("overall") or {}
    feed = payload.get("suggestion_feed") or {}

    lines = [
        "=== Brain v1 Operations Report ===",
        f"Generated at:       {payload.get('generated_at', '-')}",
        f"Trace limit:        {payload.get('trace_limit', 0)}",
        f"Workflow filter:    {payload.get('workflow_filter') or '(none)'}",
        f"Version filter:     {payload.get('version_filter') or '(none)'}",
        "",
        "Baseline:",
        f"  Recommendation:   {baseline.get('recommendation', '-')}",
        f"  Reason:           {baseline.get('recommendation_reason', '-')}",
        f"  Traces scanned:   {baseline.get('traces_scanned', 0)}",
        f"  Shadow samples:   {baseline.get('samples', 0)}",
    ]
    if overall:
        agreement = overall.get("agreement_rate")
        divergence = overall.get("mean_score_divergence")
        overlap = overall.get("mean_top_k_overlap")
        lines.append(
            f"  Overall:          "
            f"agreement={f'{agreement:.1%}' if agreement is not None else 'n/a'}"
            f"  mean_divergence={f'{divergence:.3f}' if divergence is not None else 'n/a'}"
            f"  mean_top_k_overlap={f'{overlap:.3f}' if overlap is not None else 'n/a'}"
        )

    lines.extend(
        [
            "",
            "Suggestion feed:",
            f"  Gated:            {feed.get('gated', False)}",
            f"  Gate passed:      {feed.get('gate_passed', False)}",
            f"  Gate reason:      {feed.get('gate_reason', '-')}",
            f"  Shadow samples:   {feed.get('shadow_samples', 0)}",
            f"  Disagreements:    {feed.get('disagreement_samples', 0)}",
            f"  Entries returned: {len(feed.get('entries') or [])}",
        ]
    )
    return "\n".join(lines)


def _handle_brain_status(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_brain_operations_snapshot(
        trace_limit=max(1, args.trace_limit),
        workflow_filter=args.workflow,
        version_filter=args.version,
        max_feed_entries=args.max_feed_entries,
    )
    return _emit(payload, _render_brain_status, json_mode=_json_mode(args))


def _render_governance_retention(payload: dict[str, Any]) -> str:
    """Render a RetentionReport for operator review."""
    if "error" in payload:
        return (
            f"[WARN] Retention scan unavailable: {payload['error']}\n"
            f"       trace_store_path={payload.get('trace_store_path', '-')}"
        )

    policy = payload.get("policy") or {}
    totals = payload.get("totals") or {}
    candidates = payload.get("candidates") or []

    lines = [
        "=== Governance Retention Report ===",
        f"Generated at:        {payload.get('generated_at', '-')}",
        f"Evaluation time:     {payload.get('evaluation_time', '-')}",
        f"Trace scan limit:    {payload.get('trace_limit', 0)}",
        "",
        "Policy:",
        f"  trace_retention_days:    {policy.get('trace_retention_days', '-')}",
        f"  approval_retention_days: {policy.get('approval_retention_days', '-')}",
        f"  keep_open_traces:        {policy.get('keep_open_traces', '-')}",
        f"  keep_pending_approvals:  {policy.get('keep_pending_approvals', '-')}",
        "",
        "Totals:",
        f"  Traces scanned:      {totals.get('traces_scanned', 0)}",
        f"  Approvals scanned:   {totals.get('approvals_scanned', 0)}",
        f"  Trace candidates:    {totals.get('trace_candidates', 0)}",
        f"  Approval candidates: {totals.get('approval_candidates', 0)}",
        "",
        f"Candidates ({len(candidates)}):",
    ]
    if not candidates:
        lines.append("  (none)")
    else:
        for entry in candidates[:20]:
            lines.append(
                f"  - [{entry.get('kind', '-')}] {entry.get('record_id', '-')}"
                f"  age={entry.get('age_days', 0):.2f}d"
                f"  retention={entry.get('retention_days', '-')}d"
            )
        if len(candidates) > 20:
            lines.append(f"  ... ({len(candidates) - 20} more)")
    return "\n".join(lines)


def _render_governance_pii(payload: dict[str, Any]) -> str:
    """Render a retention-scoped PII annotation for operator review."""
    if "error" in payload:
        return (
            f"[WARN] PII scan unavailable: {payload['error']}\n"
            f"       trace_store_path={payload.get('trace_store_path', '-')}"
        )

    annotation = payload.get("pii_annotation") or {}
    retention = payload.get("retention_report") or {}
    retention_totals = retention.get("totals") or {}
    policy = payload.get("policy") or {}
    categories = policy.get("enabled_categories") or []
    category_counts = annotation.get("category_counts") or {}
    annotations = annotation.get("annotations") or []

    lines = [
        "=== Governance PII Annotation (over retention candidates) ===",
        f"Generated at:        {retention.get('generated_at', '-')}",
        f"Evaluation time:     {retention.get('evaluation_time', '-')}",
        "",
        "Policy:",
        f"  enabled_categories:  {', '.join(categories) if categories else '(none)'}",
        "",
        "Retention totals:",
        f"  Traces scanned:      {retention_totals.get('traces_scanned', 0)}",
        f"  Approvals scanned:   {retention_totals.get('approvals_scanned', 0)}",
        f"  Trace candidates:    {retention_totals.get('trace_candidates', 0)}",
        f"  Approval candidates: {retention_totals.get('approval_candidates', 0)}",
        "",
        "PII totals:",
        f"  Total candidates:        {annotation.get('total_candidates', 0)}",
        f"  Candidates with findings: {annotation.get('candidates_with_findings', 0)}",
    ]
    if category_counts:
        lines.append("  Category counts:")
        for category in sorted(category_counts):
            lines.append(f"    - {category}: {category_counts[category]}")
    else:
        lines.append("  Category counts:    (none)")

    flagged = [entry for entry in annotations if entry.get("finding_count", 0) > 0]
    lines.extend(["", f"Flagged candidates ({len(flagged)}):"])
    if not flagged:
        lines.append("  (none)")
    else:
        for entry in flagged[:20]:
            cats = sorted(
                {
                    match.get("category", "?")
                    for finding in (entry.get("result") or {}).get("findings", [])
                    for match in finding.get("matches", [])
                }
            )
            lines.append(
                f"  - [{entry.get('kind', '-')}] {entry.get('record_id', '-')}"
                f"  findings={entry.get('finding_count', 0)}"
                f"  categories={','.join(cats) if cats else '-'}"
            )
        if len(flagged) > 20:
            lines.append(f"  ... ({len(flagged) - 20} more)")
    return "\n".join(lines)


def _render_governance_provenance(payload: dict[str, Any]) -> str:
    """Render a ProvenanceReport for operator review."""
    if "error" in payload:
        return (
            f"[WARN] Provenance report unavailable: {payload['error']}\n"
            f"       detail={payload.get('detail', '-')}"
        )

    totals = payload.get("totals") or {}
    statuses = payload.get("statuses") or []
    policy = payload.get("policy") or {}
    registry = payload.get("registry") or {}
    finding_counts = totals.get("finding_counts") or {}

    lines = [
        "=== Governance Provenance Report ===",
        f"Generated at:           {payload.get('generated_at', '-')}",
        "",
        "Registry source:",
        f"  Path:                 {registry.get('path', '-')}",
        f"  File present:         {registry.get('file_present', False)}",
        f"  Load warnings:        {len(registry.get('load_warnings') or [])}",
        f"  Advisory warnings:    {len(registry.get('advisory_warnings') or [])}",
        "",
        "Policy:",
        f"  require_provenance_for:      {', '.join(policy.get('require_provenance_for') or []) or '(none)'}",
        f"  require_license_for:         {', '.join(policy.get('require_license_for') or []) or '(none)'}",
        f"  require_retention_for_pii:   {policy.get('require_retention_for_pii', False)}",
        f"  require_retention_for_all:   {policy.get('require_retention_for_all', False)}",
        "",
        "Totals:",
        f"  Sources scanned:       {totals.get('sources_scanned', 0)}",
        f"  Compliant sources:     {totals.get('compliant_sources', 0)}",
        f"  Sources with findings: {totals.get('sources_with_findings', 0)}",
        "",
        f"Finding counts ({len(finding_counts)}):",
    ]
    if not finding_counts:
        lines.append("  (none)")
    else:
        for kind in sorted(finding_counts):
            lines.append(f"  - {kind}: {finding_counts[kind]}")

    load_warnings = registry.get("load_warnings") or []
    if load_warnings:
        lines.extend(["", f"Load warnings ({len(load_warnings)}):"])
        for warning in load_warnings[:20]:
            lines.append(f"  - {warning}")
        if len(load_warnings) > 20:
            lines.append(f"  ... ({len(load_warnings) - 20} more)")

    lines.extend(["", f"Sources ({len(statuses)}):"])
    if not statuses:
        lines.append("  (none)")
    else:
        for status in statuses[:40]:
            marker = "OK  " if status.get("compliant") else "FAIL"
            lines.append(
                f"  [{marker}] {status.get('source_id', '-')}"
                f"  trust={status.get('trust', '-')}"
                f"  pii={status.get('pii_risk', False)}"
                f"  prov={status.get('has_provenance', False)}"
                f"  lic={status.get('has_license', False)}"
                f"  retention={status.get('retention_days') if status.get('retention_days') is not None else '-'}"
            )
            for finding in status.get("findings") or []:
                lines.append(
                    f"      * {finding.get('kind', '-')}: {finding.get('message', '-')}"
                )
        if len(statuses) > 40:
            lines.append(f"  ... ({len(statuses) - 40} more)")
    return "\n".join(lines)


def _handle_governance_provenance(args: argparse.Namespace) -> int:
    core = _load_core()

    def _split_trust(raw: str | None) -> list[str] | None:
        if raw is None:
            return None
        return [item.strip() for item in raw.split(",") if item.strip()]

    payload = core.get_provenance_report(
        require_provenance_for=_split_trust(args.require_provenance_for),
        require_license_for=_split_trust(args.require_license_for),
        require_retention_for_pii=bool(args.require_retention_for_pii),
        require_retention_for_all=bool(args.require_retention_for_all),
    )
    return _emit(payload, _render_governance_provenance, json_mode=_json_mode(args))


def _handle_governance_pii(args: argparse.Namespace) -> int:
    core = _load_core()
    categories: list[str] | None = None
    if args.categories:
        categories = [item.strip() for item in args.categories.split(",") if item.strip()]
    payload = core.get_retention_pii_annotation(
        trace_retention_days=max(1, args.trace_retention_days),
        approval_retention_days=max(1, args.approval_retention_days),
        trace_limit=max(1, args.trace_limit),
        keep_open_traces=not args.include_open_traces,
        keep_pending_approvals=not args.include_pending_approvals,
        enabled_categories=categories,
    )
    return _emit(payload, _render_governance_pii, json_mode=_json_mode(args))


def _handle_governance_retention(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_retention_scan(
        trace_retention_days=max(1, args.trace_retention_days),
        approval_retention_days=max(1, args.approval_retention_days),
        trace_limit=max(1, args.trace_limit),
        keep_open_traces=not args.include_open_traces,
        keep_pending_approvals=not args.include_pending_approvals,
    )
    return _emit(payload, _render_governance_retention, json_mode=_json_mode(args))


def _render_ops_cost(payload: dict[str, Any]) -> str:
    """Render an AgentPerformanceReport for operator review."""
    entries = payload.get("entries") or []
    totals = payload.get("totals") or {}

    lines = [
        "=== Ops Cost Report (per agent) ===",
        f"Generated at:     {payload.get('generated_at', '-')}",
        f"Sort key:         {payload.get('sort_key', '-')}"
        f"  descending={payload.get('descending', '-')}",
        f"Min executions:   {payload.get('min_executions', 0)}",
        "",
        "Totals:",
        f"  Agents reported:         {totals.get('agents', 0)}",
        f"  Total executions:        {totals.get('total_executions', 0)}",
        f"  Total recent failures:   {totals.get('total_recent_failures', 0)}",
        f"  Weighted success_rate:   {totals.get('weighted_success_rate', 0.0):.4f}",
        f"  Weighted avg_latency:    {totals.get('weighted_avg_latency', 0.0):.4f}",
        f"  Weighted avg_cost:       {totals.get('weighted_avg_cost', 0.0):.4f}",
        "",
        f"Entries ({len(entries)}):",
    ]
    if not entries:
        lines.append("  (none)")
    else:
        for entry in entries[:20]:
            lines.append(
                f"  - {entry.get('agent_id', '-')}"
                f"  execs={entry.get('execution_count', 0)}"
                f"  avg_cost={entry.get('avg_cost', 0.0):.4f}"
                f"  avg_latency={entry.get('avg_latency', 0.0):.4f}"
                f"  success={entry.get('success_rate', 0.0):.4f}"
            )
        if len(entries) > 20:
            lines.append(f"  ... ({len(entries) - 20} more)")
    return "\n".join(lines)


def _render_ops_energy(payload: dict[str, Any]) -> str:
    """Render an EnergyReport for operator review."""
    if "error" in payload:
        return (
            f"[WARN] Energy report unavailable: {payload['error']}\n"
            f"       detail={payload.get('detail', '-')}"
        )

    entries = payload.get("entries") or []
    totals = payload.get("totals") or {}
    fallback = payload.get("fallback_agents") or []

    lines = [
        "=== Ops Energy Report (per agent) ===",
        f"Generated at:     {payload.get('generated_at', '-')}",
        f"Sort key:         {payload.get('sort_key', '-')}"
        f"  descending={payload.get('descending', '-')}",
        f"Min executions:   {payload.get('min_executions', 0)}",
        "",
        "Totals:",
        f"  Agents reported:           {totals.get('agents', 0)}",
        f"  Total executions:          {totals.get('total_executions', 0)}",
        f"  Total energy (J):          {totals.get('total_energy_joules', 0.0):.4f}",
        f"  Total energy (Wh):         {totals.get('total_energy_wh', 0.0):.4f}",
        f"  Weighted avg_power_watts:  {totals.get('weighted_avg_power_watts', 0.0):.4f}",
        "",
        f"Fallback agents ({len(fallback)}):",
    ]
    if not fallback:
        lines.append("  (none)")
    else:
        for agent_id in fallback[:20]:
            lines.append(f"  - {agent_id}")
        if len(fallback) > 20:
            lines.append(f"  ... ({len(fallback) - 20} more)")

    lines.extend(["", f"Entries ({len(entries)}):"])
    if not entries:
        lines.append("  (none)")
    else:
        for entry in entries[:20]:
            lines.append(
                f"  - {entry.get('agent_id', '-')}"
                f"  execs={entry.get('execution_count', 0)}"
                f"  watts={entry.get('avg_power_watts', 0.0):.2f}"
                f"  avg_J={entry.get('avg_energy_joules', 0.0):.4f}"
                f"  total_J={entry.get('total_energy_joules', 0.0):.4f}"
                f"  total_Wh={entry.get('total_energy_wh', 0.0):.4f}"
                f"  src={entry.get('profile_source', '-')}"
                f"{'  (fallback)' if entry.get('used_default_profile') else ''}"
            )
        if len(entries) > 20:
            lines.append(f"  ... ({len(entries) - 20} more)")
    return "\n".join(lines)


def _handle_ops_energy(args: argparse.Namespace) -> int:
    core = _load_core()
    agent_ids: list[str] | None = None
    if args.agents:
        agent_ids = [item.strip() for item in args.agents.split(",") if item.strip()]

    profiles_map: dict[str, dict[str, Any]] | None = None
    if args.profiles:
        try:
            with open(args.profiles, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            payload = {
                "error": "profiles_unreadable",
                "detail": f"{exc.__class__.__name__}: {exc}",
            }
            return _emit(payload, _render_ops_energy, json_mode=_json_mode(args))
        if not isinstance(raw, dict):
            payload = {
                "error": "profiles_schema_invalid",
                "detail": "profiles JSON must be an object mapping agent_id to {avg_power_watts, source?}",
            }
            return _emit(payload, _render_ops_energy, json_mode=_json_mode(args))
        profiles_map = raw

    payload = core.get_energy_report(
        default_watts=max(0.0, args.default_watts),
        default_source=args.default_source,
        profiles=profiles_map,
        sort_key=args.sort_key,
        descending=not args.ascending,
        min_executions=max(0, args.min_executions),
        agent_ids=agent_ids,
    )
    return _emit(payload, _render_ops_energy, json_mode=_json_mode(args))


def _render_learningops_split(payload: dict[str, Any]) -> str:
    """Render a DatasetSplit manifest for operator review."""
    if "error" in payload:
        return (
            f"[WARN] Dataset split unavailable: {payload['error']}\n"
            f"       detail={payload.get('detail', payload.get('trace_store_path', '-'))}"
        )

    manifest = payload.get("manifest") or {}
    sizes = payload.get("sizes") or {}
    config = manifest.get("config") or {}
    sample = payload.get("sample_trace_ids")

    lines = [
        "=== LearningOps Dataset Split ===",
        f"Generated at:        {manifest.get('generated_at', '-')}",
        f"Group by:            {config.get('group_by', '-')}",
        f"Seed:                {config.get('seed', '-')}",
        f"Ratios:              train={config.get('train_ratio', 0.0):.4f}"
        f"  val={config.get('val_ratio', 0.0):.4f}"
        f"  test={config.get('test_ratio', 0.0):.4f}",
        "",
        "Totals:",
        f"  Total records:     {manifest.get('total_records', 0)}",
        f"  Total groups:      {manifest.get('total_groups', 0)}",
        f"  Ungrouped records: {manifest.get('ungrouped_records', 0)}",
        f"  Fingerprint:       {manifest.get('dataset_fingerprint', '-')}",
        "",
        "Split sizes:",
        f"  train:             {sizes.get('train', 0)}",
        f"  val:               {sizes.get('val', 0)}",
        f"  test:              {sizes.get('test', 0)}",
    ]
    if sample is not None:
        lines.extend(["", "Sample trace_ids (first 20 per bucket):"])
        for bucket in ("train", "val", "test"):
            ids = sample.get(bucket) or []
            lines.append(f"  {bucket} ({len(ids)}):")
            if not ids:
                lines.append("    (none)")
            else:
                for trace_id in ids:
                    lines.append(f"    - {trace_id}")
    return "\n".join(lines)


def _render_learningops_filter(payload: dict[str, Any]) -> str:
    """Render a DataQualityFilter preview report for operator review."""
    if "error" in payload:
        return (
            f"[WARN] Quality filter preview unavailable: {payload['error']}\n"
            f"       detail={payload.get('detail', payload.get('trace_store_path', '-'))}"
        )

    policy = payload.get("policy") or {}
    totals = payload.get("totals") or {}
    violations = payload.get("violations_by_field") or {}
    sample = payload.get("rejected_sample") or []

    lines = [
        "=== LearningOps Quality Filter Preview ===",
        f"Generated at:           {payload.get('generated_at', '-')}",
        "",
        "Policy:",
        f"  require_routing_decision: {policy.get('require_routing_decision', False)}",
        f"  require_outcome:          {policy.get('require_outcome', False)}",
        f"  require_approval_outcome: {policy.get('require_approval_outcome', False)}",
        f"  min_quality_score:        {policy.get('min_quality_score', 0.0):.4f}",
        "",
        "Totals:",
        f"  Total records:   {totals.get('total', 0)}",
        f"  Accepted:        {totals.get('accepted', 0)}",
        f"  Rejected:        {totals.get('rejected', 0)}",
        f"  Acceptance rate: {totals.get('acceptance_rate', 0.0):.4f}",
        "",
        f"Violations by field ({len(violations)}):",
    ]
    if not violations:
        lines.append("  (none)")
    else:
        for field in sorted(violations):
            lines.append(f"  - {field}: {violations[field]}")

    lines.extend(["", f"Rejected sample ({len(sample)}):"])
    if not sample:
        lines.append("  (none)")
    else:
        for item in sample:
            lines.append(
                f"  - trace={item.get('trace_id', '-')}"
                f"  wf={item.get('workflow_name', '-')}"
                f"  task={item.get('task_type') or '-'}"
                f"  q={item.get('quality_score', 0.0):.2f}"
            )
            for violation in item.get("violations") or []:
                lines.append(
                    f"      * {violation.get('field', '-')}: {violation.get('reason', '-')}"
                )
    if payload.get("rejected_sample_truncated"):
        rejected_total = totals.get("rejected", 0)
        lines.append(f"  ... ({rejected_total - len(sample)} more rejected, truncated)")
    return "\n".join(lines)


def _handle_learningops_filter(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_dataset_quality_report(
        require_routing_decision=bool(args.require_routing_decision),
        require_outcome=bool(args.require_outcome),
        require_approval_outcome=bool(args.require_approval_outcome),
        min_quality_score=args.min_quality_score,
        limit=max(1, args.limit),
        rejected_sample_size=max(0, args.sample_size),
    )
    return _emit(payload, _render_learningops_filter, json_mode=_json_mode(args))


def _handle_learningops_split(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_dataset_split(
        train_ratio=args.train,
        val_ratio=args.val,
        test_ratio=args.test,
        seed=max(0, args.seed),
        group_by=args.group_by,
        limit=max(1, args.limit),
        include_sample_trace_ids=bool(args.show_trace_ids),
    )
    return _emit(payload, _render_learningops_split, json_mode=_json_mode(args))


def _handle_ops_cost(args: argparse.Namespace) -> int:
    core = _load_core()
    agent_ids: list[str] | None = None
    if args.agents:
        agent_ids = [item.strip() for item in args.agents.split(",") if item.strip()]
    payload = core.get_agent_performance_report(
        sort_key=args.sort_key,
        descending=not args.ascending,
        min_executions=max(0, args.min_executions),
        agent_ids=agent_ids,
    )
    return _emit(payload, _render_ops_cost, json_mode=_json_mode(args))


def _handle_health(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.get_control_plane_overview(
        agent_limit=max(1, args.limit),
        approval_limit=max(1, args.limit),
        trace_limit=max(1, args.limit),
        plan_limit=max(1, args.limit),
        governance_limit=max(1, args.limit),
    )
    payload["runtime"] = _runtime_overview()
    return _emit(payload, _render_health, json_mode=_json_mode(args))


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_type", help="Kanonischer task_type fuer den Kernpfad")
    parser.add_argument("description_text", nargs="?", help="Optionale Kurzbeschreibung")
    parser.add_argument("--description", help="Explizite Beschreibung der Aufgabe")
    parser.add_argument("--task-id", help="Optionale stabile Task-ID")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Input-Feld fuer input_data; VALUE darf JSON sein",
    )
    parser.add_argument(
        "--input-json",
        help="Komplettes JSON-Objekt fuer input_data",
    )
    parser.add_argument(
        "--option",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Execution-Hint fuer options; VALUE darf JSON sein",
    )
    parser.add_argument(
        "--option-json",
        help="Komplettes JSON-Objekt fuer options",
    )
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="abrain",
        description="Interne Control-Plane-Bridge fuer scripts/abrain.",
    )
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    task_parser = subparsers.add_parser("task", help="Tasks ueber den kanonischen Kernpfad starten")
    task_subparsers = task_parser.add_subparsers(dest="action", required=True)
    task_run = task_subparsers.add_parser("run", help="Einen einzelnen Task ausfuehren")
    _add_run_arguments(task_run)
    task_run.set_defaults(handler=_handle_task_run)

    plan_parser = subparsers.add_parser("plan", help="Plan-Pfade ueber den Kern ansprechen")
    plan_subparsers = plan_parser.add_subparsers(dest="action", required=True)
    plan_run = plan_subparsers.add_parser("run", help="Einen Ausfuehrungsplan starten")
    _add_run_arguments(plan_run)
    plan_run.set_defaults(handler=_handle_plan_run)
    plan_list = plan_subparsers.add_parser("list", help="Letzte Plaene anzeigen")
    plan_list.add_argument("--limit", type=int, default=10, help="Maximale Anzahl an Plaenen")
    plan_list.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    plan_list.set_defaults(handler=_handle_plan_list)

    approval_parser = subparsers.add_parser(
        "approval",
        help="Pending approvals einsehen und entscheiden",
    )
    approval_subparsers = approval_parser.add_subparsers(dest="action", required=True)
    approval_list = approval_subparsers.add_parser("list", help="Pending approvals anzeigen")
    approval_list.add_argument("--limit", type=int, default=20, help="Maximale Anzahl an Approvals")
    approval_list.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    approval_list.set_defaults(handler=_handle_approval_list)
    for action in ("approve", "reject"):
        decision_parser = approval_subparsers.add_parser(
            action,
            help=f"Pending approval {action}",
        )
        decision_parser.add_argument("approval_id", help="Approval-ID aus approval list")
        decision_parser.add_argument(
            "--decided-by",
            default="abrain-cli",
            help="Kennung des Entscheidungstraegers",
        )
        decision_parser.add_argument("--comment", help="Optionaler Entscheidungs-Kommentar")
        decision_parser.add_argument(
            "--rating",
            type=float,
            help="Optionales Rating zwischen 0.0 und 1.0",
        )
        decision_parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
        decision_parser.set_defaults(handler=_handle_approval_decision, action=action)

    trace_parser = subparsers.add_parser("trace", help="Trace-Inspect auf dem kanonischen Store")
    trace_subparsers = trace_parser.add_subparsers(dest="action", required=True)
    trace_list = trace_subparsers.add_parser("list", help="Letzte Traces anzeigen")
    trace_list.add_argument("--limit", type=int, default=10, help="Maximale Anzahl an Traces")
    trace_list.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    trace_list.set_defaults(handler=_handle_trace_list)
    trace_show = trace_subparsers.add_parser("show", help="Einzelnen Trace anzeigen")
    trace_show.add_argument("trace_id", help="Trace-ID")
    trace_show.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    trace_show.set_defaults(handler=_handle_trace_show)
    trace_drilldown = trace_subparsers.add_parser(
        "drilldown",
        help="Forensische Entscheidungsrekonstruktion fuer einen Trace",
    )
    trace_drilldown.add_argument("trace_id", help="Trace-ID")
    trace_drilldown.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    trace_drilldown.set_defaults(handler=_handle_trace_drilldown)
    trace_replay = trace_subparsers.add_parser(
        "replay",
        help="Dry-run Routing-Replay: gespeicherten Trace gegen aktuelle Logik pruefen",
    )
    trace_replay.add_argument("trace_id", help="Trace-ID")
    trace_replay.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    trace_replay.set_defaults(handler=_handle_trace_replay)

    compliance_parser = subparsers.add_parser(
        "compliance",
        help="Policy-Compliance-Pruefungen und Baselines",
    )
    compliance_subparsers = compliance_parser.add_subparsers(dest="action", required=True)
    compliance_check = compliance_subparsers.add_parser(
        "check",
        help="Policy-Compliance eines einzelnen Trace pruefen",
    )
    compliance_check.add_argument("trace_id", help="Trace-ID")
    compliance_check.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    compliance_check.set_defaults(handler=_handle_compliance_check)
    compliance_baselines = compliance_subparsers.add_parser(
        "baselines",
        help="Baseline-Metriken ueber zuletzt gespeicherte Traces berechnen",
    )
    compliance_baselines.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximale Anzahl Traces fuer Baseline-Berechnung",
    )
    compliance_baselines.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    compliance_baselines.set_defaults(handler=_handle_compliance_baselines)

    explain_parser = subparsers.add_parser(
        "explain",
        help="Explainability eines Trace anzeigen",
    )
    explain_parser.add_argument("trace_id", help="Trace-ID")
    explain_parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    explain_parser.set_defaults(handler=_handle_explain)

    agent_parser = subparsers.add_parser("agent", help="Agent-Katalog inspizieren")
    agent_subparsers = agent_parser.add_subparsers(dest="action", required=True)
    agent_list = agent_subparsers.add_parser("list", help="Registrierte Agenten anzeigen")
    agent_list.add_argument("--limit", type=int, default=20, help="Maximale Anzahl an Agenten")
    agent_list.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    agent_list.set_defaults(handler=_handle_agent_list)

    brain_parser = subparsers.add_parser(
        "brain",
        help="Phase-6 Brain v1 Operator-Surface (shadow baseline + suggestion feed)",
    )
    brain_subparsers = brain_parser.add_subparsers(dest="action", required=True)
    brain_status = brain_subparsers.add_parser(
        "status",
        help="Baseline-Verdict (promote/observe/reject) und gated Suggestion-Feed anzeigen",
    )
    brain_status.add_argument(
        "--trace-limit",
        type=int,
        default=1000,
        help="Maximale Trace-Anzahl fuer den Baseline- und Feed-Scan (default 1000)",
    )
    brain_status.add_argument(
        "--workflow",
        default=None,
        help="Optionaler Workflow-Filter",
    )
    brain_status.add_argument(
        "--version",
        default=None,
        help="Optionaler Brain-Version-Filter",
    )
    brain_status.add_argument(
        "--max-feed-entries",
        type=int,
        default=None,
        help="Optionales Cap fuer Suggestion-Feed-Eintraege",
    )
    brain_status.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    brain_status.set_defaults(handler=_handle_brain_status)

    governance_parser = subparsers.add_parser(
        "governance",
        help="Phase-6 Daten-Governance Operator-Surface (Retention etc.)",
    )
    governance_subparsers = governance_parser.add_subparsers(dest="action", required=True)
    gov_retention = governance_subparsers.add_parser(
        "retention",
        help="Read-only Retention-Kandidatenreport ueber TraceStore + ApprovalStore",
    )
    gov_retention.add_argument(
        "--trace-retention-days",
        type=int,
        default=90,
        help="Maximale Trace-Aufbewahrung in Tagen (default 90)",
    )
    gov_retention.add_argument(
        "--approval-retention-days",
        type=int,
        default=90,
        help="Maximale Approval-Aufbewahrung in Tagen (default 90)",
    )
    gov_retention.add_argument(
        "--trace-limit",
        type=int,
        default=10_000,
        help="Maximale Trace-Anzahl fuer den Scan (default 10000)",
    )
    gov_retention.add_argument(
        "--include-open-traces",
        action="store_true",
        help="Auch Traces ohne ended_at als Kandidaten zulassen",
    )
    gov_retention.add_argument(
        "--include-pending-approvals",
        action="store_true",
        help="Auch PENDING-Approvals als Kandidaten zulassen",
    )
    gov_retention.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    gov_retention.set_defaults(handler=_handle_governance_retention)

    gov_pii = governance_subparsers.add_parser(
        "pii",
        help="Read-only PII-Annotation ueber den Retention-Kandidatenset",
    )
    gov_pii.add_argument(
        "--trace-retention-days",
        type=int,
        default=90,
        help="Maximale Trace-Aufbewahrung in Tagen (default 90)",
    )
    gov_pii.add_argument(
        "--approval-retention-days",
        type=int,
        default=90,
        help="Maximale Approval-Aufbewahrung in Tagen (default 90)",
    )
    gov_pii.add_argument(
        "--trace-limit",
        type=int,
        default=10_000,
        help="Maximale Trace-Anzahl fuer den Retention-Scan (default 10000)",
    )
    gov_pii.add_argument(
        "--include-open-traces",
        action="store_true",
        help="Auch Traces ohne ended_at als Kandidaten zulassen",
    )
    gov_pii.add_argument(
        "--include-pending-approvals",
        action="store_true",
        help="Auch PENDING-Approvals als Kandidaten zulassen",
    )
    gov_pii.add_argument(
        "--categories",
        default=None,
        help="Komma-Liste aktivierter PII-Kategorien (default: built-in conservative set)",
    )
    gov_pii.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    gov_pii.set_defaults(handler=_handle_governance_pii)

    gov_provenance = governance_subparsers.add_parser(
        "provenance",
        help="Read-only Provenance-/License-/Retention-Report ueber KnowledgeSourceRegistry",
    )
    gov_provenance.add_argument(
        "--require-provenance-for",
        dest="require_provenance_for",
        default=None,
        help="Komma-Liste von Trust-Levels (trusted,internal,external,untrusted)"
        " die eine Provenance verlangen (default external,untrusted)",
    )
    gov_provenance.add_argument(
        "--require-license-for",
        dest="require_license_for",
        default=None,
        help="Komma-Liste von Trust-Levels die eine License verlangen"
        " (default external,untrusted)",
    )
    gov_provenance.add_argument(
        "--require-retention-for-pii",
        dest="require_retention_for_pii",
        action="store_true",
        default=True,
        help="PII-Quellen ohne retention_days flaggen (default: aktiv)",
    )
    gov_provenance.add_argument(
        "--no-require-retention-for-pii",
        dest="require_retention_for_pii",
        action="store_false",
        help="PII-Retention-Check deaktivieren",
    )
    gov_provenance.add_argument(
        "--require-retention-for-all",
        dest="require_retention_for_all",
        action="store_true",
        default=False,
        help="Jede Quelle ohne retention_days flaggen (verschaerfte Policy)",
    )
    gov_provenance.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    gov_provenance.set_defaults(handler=_handle_governance_provenance)

    ops_parser = subparsers.add_parser(
        "ops",
        help="Phase-6.5 Operator-Surface (Kosten, Energie, Performance)",
    )
    ops_subparsers = ops_parser.add_subparsers(dest="action", required=True)
    ops_cost = ops_subparsers.add_parser(
        "cost",
        help="Read-only Kosten-/Latenz-/Success-Report pro Agent aus PerformanceHistoryStore",
    )
    ops_cost.add_argument(
        "--sort-key",
        choices=["avg_cost", "avg_latency", "success_rate", "execution_count", "agent_id"],
        default="avg_cost",
        help="Sortierschluessel fuer die Eintraege (default avg_cost)",
    )
    ops_cost.add_argument(
        "--ascending",
        action="store_true",
        help="Aufsteigend sortieren (default: absteigend)",
    )
    ops_cost.add_argument(
        "--min-executions",
        type=int,
        default=0,
        help="Mindestanzahl Ausfuehrungen je Agent (default 0)",
    )
    ops_cost.add_argument(
        "--agents",
        default=None,
        help="Komma-Liste expliziter Agent-IDs (default: alle registrierten)",
    )
    ops_cost.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    ops_cost.set_defaults(handler=_handle_ops_cost)

    ops_energy = ops_subparsers.add_parser(
        "energy",
        help="Read-only Energie-Report pro Agent aus PerformanceHistoryStore",
    )
    ops_energy.add_argument(
        "--default-watts",
        type=float,
        required=True,
        help="Default-Wattage fuer Agenten ohne expliziten Profileintrag",
    )
    ops_energy.add_argument(
        "--default-source",
        choices=["measured", "vendor_spec", "estimated"],
        default="estimated",
        help="Herkunft der Default-Wattage (default estimated)",
    )
    ops_energy.add_argument(
        "--profiles",
        default=None,
        help="JSON-Datei: {agent_id: {avg_power_watts, source?}}",
    )
    ops_energy.add_argument(
        "--sort-key",
        choices=[
            "total_energy_joules",
            "avg_energy_joules",
            "avg_power_watts",
            "execution_count",
            "agent_id",
        ],
        default="total_energy_joules",
        help="Sortierschluessel fuer die Eintraege (default total_energy_joules)",
    )
    ops_energy.add_argument(
        "--ascending",
        action="store_true",
        help="Aufsteigend sortieren (default: absteigend)",
    )
    ops_energy.add_argument(
        "--min-executions",
        type=int,
        default=0,
        help="Mindestanzahl Ausfuehrungen je Agent (default 0)",
    )
    ops_energy.add_argument(
        "--agents",
        default=None,
        help="Komma-Liste expliziter Agent-IDs (default: alle registrierten)",
    )
    ops_energy.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    ops_energy.set_defaults(handler=_handle_ops_energy)

    learningops_parser = subparsers.add_parser(
        "learningops",
        help="Phase-5 LearningOps-Operator-Surface (Dataset-Splits, Training-Jobs)",
    )
    learningops_subparsers = learningops_parser.add_subparsers(
        dest="action", required=True
    )
    lo_split = learningops_subparsers.add_parser(
        "split",
        help="Deterministischer Train/Val/Test-Split ueber kanonische LearningRecords",
    )
    lo_split.add_argument(
        "--train",
        type=float,
        required=True,
        help="Train-Ratio (exklusiv 0..1)",
    )
    lo_split.add_argument(
        "--val",
        type=float,
        required=True,
        help="Val-Ratio (0..1)",
    )
    lo_split.add_argument(
        "--test",
        type=float,
        required=True,
        help="Test-Ratio (0..1); train+val+test muss 1.0 ergeben",
    )
    lo_split.add_argument(
        "--seed",
        type=int,
        required=True,
        help="Seed fuer die deterministische Bucket-Zuordnung",
    )
    lo_split.add_argument(
        "--group-by",
        choices=["trace_id", "task_type", "workflow_name"],
        default="trace_id",
        help="Gruppierungsschluessel zur Vermeidung von Group-Leakage",
    )
    lo_split.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximale Anzahl Traces, aus denen LearningRecords gebaut werden",
    )
    lo_split.add_argument(
        "--show-trace-ids",
        action="store_true",
        help="Erste 20 trace_ids je Bucket im Payload ausgeben",
    )
    lo_split.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    lo_split.set_defaults(handler=_handle_learningops_split)

    lo_filter = learningops_subparsers.add_parser(
        "filter",
        help="DataQualityFilter-Preview ueber kanonische LearningRecords",
    )
    lo_filter.add_argument(
        "--require-routing-decision",
        dest="require_routing_decision",
        action="store_true",
        default=True,
        help="Records ohne Routing-Entscheidung verwerfen (default: aktiv)",
    )
    lo_filter.add_argument(
        "--no-require-routing-decision",
        dest="require_routing_decision",
        action="store_false",
        help="Auch Records ohne Routing-Entscheidung zulassen",
    )
    lo_filter.add_argument(
        "--require-outcome",
        dest="require_outcome",
        action="store_true",
        default=False,
        help="Nur Records mit bekanntem Ergebnis (success) zulassen",
    )
    lo_filter.add_argument(
        "--require-approval-outcome",
        dest="require_approval_outcome",
        action="store_true",
        default=False,
        help="Nur Records mit aufgeloester Approval zulassen",
    )
    lo_filter.add_argument(
        "--min-quality-score",
        dest="min_quality_score",
        type=float,
        default=0.0,
        help="Minimal geforderter quality_score in [0.0, 1.0] (default 0.0)",
    )
    lo_filter.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximale Anzahl Traces, aus denen LearningRecords gebaut werden",
    )
    lo_filter.add_argument(
        "--sample-size",
        dest="sample_size",
        type=int,
        default=20,
        help="Maximale Anzahl abgelehnter Records im Detail-Sample (default 20)",
    )
    lo_filter.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    lo_filter.set_defaults(handler=_handle_learningops_filter)

    health_parser = subparsers.add_parser("health", help="Kernstatus, Governance und Startpfade anzeigen")
    health_parser.add_argument("--limit", type=int, default=5, help="Maximale Anzahl fuer Listenabschnitte")
    health_parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    health_parser.set_defaults(handler=_handle_health)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    try:
        return int(handler(args))
    except CliUsageError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive operator output
        print(f"[ERROR] {exc.__class__.__name__}: {exc}", file=sys.stderr)
        if os.getenv("DEBUG") == "1":
            raise
        return 1


if __name__ == "__main__":  # pragma: no cover - script
    raise SystemExit(main())
