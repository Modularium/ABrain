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
