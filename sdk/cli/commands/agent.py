"""Agent management commands."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List

import httpx
import typer

from agentnn.deployment.agent_registry import load_agent_file
from core.agent_evolution import evolve_profile
from core.agent_profile import PROFILE_DIR, AgentIdentity
from core.audit_log import AuditEntry, AuditLog
from core.crypto import generate_keypair
from core.governance import AgentContract
from core.level_evaluator import check_level_up
from core.reputation import aggregate_score
from core.skills import load_skill
from core.trust_evaluator import eligible_for_role
from services import create_agent, list_agents

from ..client import AgentClient
from ..utils import handle_http_error, print_output
from ..utils.formatting import doc_printer

agent_app = typer.Typer(name="agent", help="Agent management")
team_app = typer.Typer(name="team", help="Team management")
training_app = typer.Typer(name="training", help="Training management")
coach_app = typer.Typer(name="coach", help="Coach utilities")
track_app = typer.Typer(name="track", help="Training track info")
mission_app = typer.Typer(name="mission", help="Mission management")
rep_app = typer.Typer(name="rep", help="Reputation utilities")
delegate_app = typer.Typer(name="delegate", help="Delegation management")
feedback_app = typer.Typer(name="feedback", help="Feedback utilities")
openhands_app = typer.Typer(name="openhands", help="OpenHands agent utilities")


@agent_app.command("list")
def agents(
    output: str = typer.Option("table", "--output", help="table|json|markdown")
) -> None:
    """List available agents."""
    try:
        result = list_agents()
    except httpx.HTTPStatusError as err:
        handle_http_error(err)
        return
    print_output(result.get("agents", []), output)


@agent_app.command(
    "register",
    help="Register an agent configuration with the registry.",
    epilog="Beispiel: agentnn agent register config/agent.yaml",
)
def agent_register(
    config: Path | None = None,
    endpoint: str = "http://localhost:8090",
    interactive: bool = typer.Option(False, "--interactive", help="use wizard"),
    docs: bool = typer.Option(
        False,
        "--docs",
        callback=doc_printer("docs/cli.md#agent-registrieren"),
        is_eager=True,
        expose_value=False,
        help="show documentation and exit",
    ),
) -> None:
    if interactive or not config:
        typer.echo("Interactive agent setup")
        name = typer.prompt("Agent name")
        role = typer.prompt("Role", default="assistant")
        tools = typer.prompt("Tools (comma separated)", default="")
        desc = typer.prompt("Description", default="")
        data = {
            "id": name,
            "role": role,
            "description": desc,
            "tools": [t.strip() for t in tools.split(",") if t.strip()],
        }
    else:
        if not config.exists():
            typer.secho(f"file not found: {config}", fg=typer.colors.RED)
            suggestion = Path("config/agent.yaml")
            if suggestion.exists():
                typer.echo(f"Vielleicht meinst du {suggestion}")
            else:
                typer.echo("Nutze --interactive für einen Wizard")
            raise typer.Exit(1)
        data = load_agent_file(config)
    result = create_agent(data, endpoint=endpoint)
    typer.echo(json.dumps(result, indent=2))


@agent_app.command("profile")
def agent_profile(name: str) -> None:
    """Show profile information for an agent."""
    client = AgentClient()
    result = client.get_agent_profile(name)
    typer.echo(json.dumps(result, indent=2))


@agent_app.command("info")
def agent_info(name: str) -> None:
    """Alias for ``profile``."""
    agent_profile(name)


@agent_app.command("update")
def agent_update(name: str, traits: str = "", skills: str = "") -> None:
    """Update an agent profile."""
    client = AgentClient()
    traits_data = json.loads(traits) if traits else None
    skills_list: List[str] | None = (
        [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    )
    result = client.update_agent_profile(name, traits=traits_data, skills=skills_list)
    typer.echo(json.dumps(result, indent=2))


@agent_app.command("status")
def agent_status(name: str) -> None:
    """Show live status for an agent."""
    client = AgentClient()
    result = client.get_agent_status(name)
    typer.echo(json.dumps(result, indent=2))


@agent_app.command("top")
def agent_top(
    metric: str = typer.Option("cost", "--metric", help="Sort metric")
) -> None:
    """List agents sorted by metric."""
    data = list_agents().get("agents", [])
    if metric == "skill":
        data.sort(key=lambda a: len(a.get("skills", [])), reverse=True)
    elif metric == "load":
        data.sort(key=lambda a: a.get("load_factor", 0))
    else:
        data.sort(key=lambda a: a.get("estimated_cost_per_token", 0))
    typer.echo(json.dumps(data, indent=2))


@agent_app.command("evolve")
def agent_evolve(name: str, mode: str = "llm", preview: bool = False) -> None:
    """Evolve an agent profile."""
    profile = AgentIdentity.load(name)
    updated = evolve_profile(profile, [], mode)
    if preview:
        typer.echo(json.dumps(asdict(updated), indent=2))
    else:
        updated.save()
        typer.echo(f"profile updated: {name}")


@agent_app.command("keypair")
def agent_keypair(name: str) -> None:
    """Generate or replace a keypair for an agent."""
    generate_keypair(name)
    typer.echo("keypair generated")


@agent_app.command("role")
def agent_role(name: str, set_role: str = typer.Option(None, "--set")) -> None:
    """Show or update the role for an agent."""
    profile = AgentIdentity.load(name)
    if set_role:
        profile.role = set_role
        profile.save()
        typer.echo("updated")
    else:
        typer.echo(profile.role)


@agent_app.command("elevate")
def agent_elevate(name: str, to: str = typer.Option(..., "--to")) -> None:
    """Grant a new role if trust requirements are met."""
    if not eligible_for_role(name, to):
        typer.echo("not eligible")
        raise typer.Exit(code=1)
    contract = AgentContract.load(name)
    if to not in contract.allowed_roles:
        contract.allowed_roles.append(to)
        contract.save()
    typer.echo("elevated")


@agent_app.command("skill")
def agent_skill(name: str) -> None:
    """Show certified skills for an agent."""
    profile = AgentIdentity.load(name)
    typer.echo(json.dumps(profile.certified_skills, indent=2))


@agent_app.command("certify")
def agent_certify(name: str, skill: str = typer.Option(..., "--skill")) -> None:
    """Grant SKILL certification to AGENT."""
    profile = AgentIdentity.load(name)
    skill_def = load_skill(skill)
    if not skill_def:
        typer.echo("skill not found")
        raise typer.Exit(code=1)
    cert = {
        "id": skill_def.id,
        "granted_at": datetime.utcnow().isoformat() + "Z",
        "expires_at": skill_def.expires_at,
    }
    profile.certified_skills = [
        c for c in profile.certified_skills if c.get("id") != skill_def.id
    ]
    profile.certified_skills.append(cert)
    profile.save()
    log = AuditLog()
    log.write(
        AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            actor="cli",
            action="certification_granted",
            context_id=name,
            detail={"skill": skill_def.id},
        )
    )
    typer.echo("granted")


@agent_app.command("level")
def agent_level(name: str) -> None:
    """Show level information for AGENT."""
    profile = AgentIdentity.load(name)
    typer.echo(
        json.dumps(
            {
                "current_level": profile.current_level,
                "progress": profile.level_progress,
            },
            indent=2,
        )
    )


@agent_app.command("promote")
def agent_promote(name: str) -> None:
    """Manually trigger level evaluation."""
    profile = AgentIdentity.load(name)
    new_level = check_level_up(profile)
    if new_level:
        typer.echo(f"promoted to {new_level}")
    else:
        typer.echo("no change")


@agent_app.command("rep")
def agent_rep(name: str) -> None:
    """Show reputation information for an agent."""
    profile = AgentIdentity.load(name)
    typer.echo(
        json.dumps(
            {
                "agent": name,
                "reputation": profile.reputation_score,
                "feedback": profile.feedback_log,
            },
            indent=2,
        )
    )


@agent_app.command("endorsements")
def agent_endorsements(name: str) -> None:
    """Show received endorsements for AGENT."""
    from core.trust_network import load_recommendations

    recs = load_recommendations(name)
    typer.echo(json.dumps([asdict(r) for r in recs], indent=2))


@agent_app.command("reflect")
def agent_reflect(name: str) -> None:
    """Analyse feedback and suggest adaptations."""
    from core.feedback_loop import load_feedback
    from core.self_reflection import reflect_and_adapt

    profile = AgentIdentity.load(name)
    feedback = load_feedback(name)
    suggestions = reflect_and_adapt(profile, feedback)
    typer.echo(json.dumps(suggestions, indent=2))


@agent_app.command("adapt")
def agent_adapt(name: str) -> None:
    """Apply recommended adaptations."""
    from core.feedback_loop import load_feedback
    from core.self_reflection import reflect_and_adapt

    profile = AgentIdentity.load(name)
    feedback = load_feedback(name)
    result = reflect_and_adapt(profile, feedback)
    profile.traits.update(result.get("traits", {}))
    for skill in result.get("skills", []):
        if skill not in profile.skills:
            profile.skills.append(skill)
    profile.adaptation_history.extend(result.get("notes", []))
    profile.save()
    log = AuditLog()
    log.write(
        AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            actor="cli",
            action="adaptation_applied",
            context_id=name,
            detail={},
        )
    )
    typer.echo("adapted")


@training_app.command("start")
def training_start(agent: str, path: str = typer.Option(..., "--path")) -> None:
    """Start a training path for an agent."""
    profile = AgentIdentity.load(agent)
    profile.training_progress[path] = "in_progress"
    profile.save()
    log = AuditLog()
    log.write(
        AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            actor="cli",
            action="training_started",
            context_id=agent,
            detail={"path": path},
        )
    )
    typer.echo("started")


@training_app.command("progress")
def training_progress(agent: str) -> None:
    """Show training progress for AGENT."""
    profile = AgentIdentity.load(agent)
    typer.echo(json.dumps(profile.training_progress, indent=2))


@mission_app.command("start")
def mission_start(mission_id: str, agent: str = typer.Option(..., "--agent")) -> None:
    """Assign MISSION_ID to AGENT."""
    profile = AgentIdentity.load(agent)
    profile.active_missions.append(mission_id)
    profile.mission_progress[mission_id] = {"step": 0, "status": "in_progress"}
    profile.save()
    log = AuditLog()
    log.write(
        AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            actor="cli",
            action="mission_started",
            context_id=agent,
            detail={"mission": mission_id},
        )
    )
    typer.echo("started")


@mission_app.command("progress")
def mission_progress(agent: str) -> None:
    """Show mission progress for AGENT."""
    profile = AgentIdentity.load(agent)
    typer.echo(json.dumps(profile.mission_progress, indent=2))


@mission_app.command("step")
def mission_step(agent: str) -> None:
    """Display next mission step for AGENT."""
    profile = AgentIdentity.load(agent)
    if not profile.active_missions:
        typer.echo("no mission")
        raise typer.Exit(code=1)
    mid = profile.active_missions[0]
    from core.mission_prompts import render_prompt
    from core.missions import AgentMission

    mission = AgentMission.load(mid)
    if not mission:
        typer.echo("missing mission")
        raise typer.Exit(code=1)
    step_idx = profile.mission_progress.get(mid, {}).get("step", 0)
    if step_idx >= len(mission.steps):
        typer.echo("mission complete")
        return
    prompt = render_prompt(profile, mission.steps[step_idx], {"goal": mission.title})
    typer.echo(prompt)


@mission_app.command("complete")
def mission_complete(agent: str) -> None:
    """Complete active mission if finished."""
    from core.missions import AgentMission
    from core.rewards import grant_rewards

    profile = AgentIdentity.load(agent)
    if not profile.active_missions:
        typer.echo("no mission")
        raise typer.Exit(code=1)
    mid = profile.active_missions[0]
    mission = AgentMission.load(mid)
    progress = profile.mission_progress.get(mid, {"step": 0})
    if progress.get("step", 0) >= len(mission.steps):
        grant_rewards(agent, mission.rewards)
        profile.active_missions.remove(mid)
        progress["status"] = "complete"
        profile.mission_progress[mid] = progress
        profile.save()
        log = AuditLog()
        log.write(
            AuditEntry(
                timestamp=datetime.utcnow().isoformat(),
                actor="cli",
                action="mission_completed",
                context_id=agent,
                detail={"mission": mid},
            )
        )
        log.write(
            AuditEntry(
                timestamp=datetime.utcnow().isoformat(),
                actor="cli",
                action="reward_unlocked",
                context_id=agent,
                detail=mission.rewards,
            )
        )
        typer.echo("completed")
    else:
        typer.echo("not finished")


@track_app.command("show")
def track_show() -> None:
    """List available training paths."""
    from core.training import TRAINING_DIR

    paths = []
    for file in TRAINING_DIR.glob("*.json"):
        with open(file, "r", encoding="utf-8") as fh:
            paths.append(json.load(fh))
    typer.echo(json.dumps(paths, indent=2))


@rep_app.command("leaderboard")
def rep_leaderboard() -> None:
    """Show top agents by reputation."""
    results = []
    for file in PROFILE_DIR.glob("*.json"):
        name = file.stem
        score = aggregate_score(name)
        results.append({"agent": name, "score": round(score, 3)})
    results.sort(key=lambda x: x["score"], reverse=True)
    typer.echo(json.dumps(results, indent=2))


@delegate_app.command("grant")
def delegate_grant(
    from_agent: str,
    to_agent: str,
    role: str = typer.Option(..., "--role"),
    scope: str = typer.Option("task", "--scope"),
    reason: str = typer.Option(None, "--reason"),
    expires_at: str = typer.Option(None, "--expires-at"),
) -> None:
    """Grant delegation from FROM_AGENT to TO_AGENT."""
    from core.delegation import grant_delegation

    grant_delegation(from_agent, to_agent, role, scope, expires_at, reason)
    log = AuditLog()
    log.write(
        AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            actor=from_agent,
            action="delegation_granted",
            context_id=to_agent,
            detail={"role": role, "scope": scope},
        )
    )
    typer.echo("granted")


@delegate_app.command("revoke")
def delegate_revoke(
    from_agent: str, to_agent: str, role: str = typer.Option(..., "--role")
) -> None:
    """Revoke delegation."""
    from core.delegation import revoke_grant

    revoke_grant(from_agent, to_agent, role)
    log = AuditLog()
    log.write(
        AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            actor=from_agent,
            action="delegation_revoked",
            context_id=to_agent,
            detail={"role": role},
        )
    )
    typer.echo("revoked")


@delegate_app.command("list")
def delegate_list(agent: str) -> None:
    """List delegations issued by AGENT."""
    from core.delegation import load_grants

    grants = load_grants(agent)
    typer.echo(json.dumps([asdict(g) for g in grants], indent=2))


@feedback_app.command("submit")
def feedback_submit(
    session: str,
    score: int = typer.Option(..., "--score"),
    comment: str = typer.Option("", "--comment"),
    agent: str = typer.Option(None, "--agent"),
    user: str = typer.Option("default", "--user"),
) -> None:
    """Send feedback for a session entry."""
    client = AgentClient()
    payload = {
        "session_id": session,
        "user_id": user,
        "agent_id": agent or "",
        "score": score,
        "comment": comment or None,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        resp = client.post_feedback(session, payload)
    except httpx.HTTPStatusError as err:
        handle_http_error(err)
        return
    typer.echo(json.dumps(resp, indent=2))


@feedback_app.command("log")
def feedback_log(agent: str) -> None:
    """Show feedback entries for AGENT."""
    from core.feedback_loop import load_feedback

    entries = load_feedback(agent)
    typer.echo(json.dumps([asdict(e) for e in entries], indent=2))


@openhands_app.command("list")
def openhands_list(
    output: str = typer.Option("table", "--output", help="table|json|markdown")
) -> None:
    """List registered OpenHands agents."""
    ports_env = os.getenv("OPENHANDS_AGENT_PORTS", "3001-3016")
    if "-" in ports_env:
        start, end = [int(p) for p in ports_env.split("-")]
        ports = list(range(start, end + 1))
    else:
        ports = [int(p) for p in ports_env.split(",") if p]
    agents = [
        {"name": f"openhands_{i}", "url": f"http://localhost:{p}", "port": p}
        for i, p in enumerate(ports, start=1)
    ]
    print_output(agents, output)


@openhands_app.command("trigger")
def openhands_trigger(task: str, agents: str = "all") -> None:
    """Trigger a task on one or multiple OpenHands agents."""
    ports_env = os.getenv("OPENHANDS_AGENT_PORTS", "3001-3016")
    if "-" in ports_env:
        start, end = [int(p) for p in ports_env.split("-")]
        ports = list(range(start, end + 1))
    else:
        ports = [int(p) for p in ports_env.split(",") if p]
    selected = (
        ports if agents == "all" else [ports[int(a) - 1] for a in agents.split(",")]
    )
    results = {}
    for port in selected:
        try:
            resp = httpx.post(
                f"http://localhost:{port}/api/conversations",
                json={"initial_user_msg": task},
                timeout=5,
            )
            resp.raise_for_status()
            results[port] = resp.json()
        except Exception as exc:  # pragma: no cover - network
            results[port] = {"error": str(exc)}
    typer.echo(json.dumps(results, indent=2))


agent_app.add_typer(team_app)
agent_app.add_typer(training_app)
agent_app.add_typer(coach_app)
agent_app.add_typer(track_app)
agent_app.add_typer(mission_app)
agent_app.add_typer(rep_app)
agent_app.add_typer(delegate_app)
agent_app.add_typer(feedback_app)
agent_app.add_typer(openhands_app)

__all__ = ["agent_app"]
