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
LEGACY_STATE_DIR = REPO_ROOT / ".agentnn"
DEFAULT_CONFIG_FILE = DEFAULT_STATE_DIR / "config.json"
LEGACY_CONFIG_FILE = LEGACY_STATE_DIR / "config.json"

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
    if DEFAULT_STATE_DIR.exists() or DEFAULT_CONFIG_FILE.exists():
        return DEFAULT_STATE_DIR
    if LEGACY_STATE_DIR.exists() or LEGACY_CONFIG_FILE.exists():
        return LEGACY_STATE_DIR
    return DEFAULT_STATE_DIR


def _runtime_config_path() -> Path:
    if DEFAULT_CONFIG_FILE.exists():
        return DEFAULT_CONFIG_FILE
    if LEGACY_CONFIG_FILE.exists():
        return LEGACY_CONFIG_FILE
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
        lines.append(f"Explainability records: {len(explainability)}")
    return "\n".join(lines)


def _render_explainability(payload: dict[str, Any]) -> str:
    records = payload.get("explainability", [])
    if not records:
        return "No explainability records found."
    rows = [
        [
            str(item.get("step_id") or "task"),
            str(item.get("selected_agent_id") or "-"),
            str(item.get("approval_required")),
            str(item.get("approval_id") or "-"),
            ",".join(str(policy_id) for policy_id in item.get("matched_policy_ids") or []) or "-",
        ]
        for item in records
    ]
    sections = [
        f"Explainability records: {len(records)}",
        _format_table(
            ["step_id", "selected_agent", "approval_required", "approval_id", "matched_policies"],
            rows,
        ),
    ]
    for item in records:
        step_id = item.get("step_id") or "task"
        sections.append(f"[{step_id}] {item.get('routing_reason_summary', '')}".strip())
        metadata = item.get("metadata") or {}
        if metadata:
            sections.append(_indent(_compact_json(metadata)))
    return "\n".join(sections)


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
            ",".join(str(cap) for cap in item.get("capabilities") or []) or "-",
        ]
        for item in agents
    ]
    return "\n".join(
        [
            f"Registered agents: {len(agents)}",
            _format_table(["agent_id", "availability", "source", "execution", "capabilities"], rows),
        ]
    )


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


def _handle_agent_list(args: argparse.Namespace) -> int:
    core = _load_core()
    payload = core.list_agent_catalog()
    payload = {"agents": payload.get("agents", [])[: max(0, args.limit)]}
    return _emit(payload, _render_agent_list, json_mode=_json_mode(args))


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
