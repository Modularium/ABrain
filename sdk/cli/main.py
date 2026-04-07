"""Modular command line interface for ABrain."""

from __future__ import annotations

import typer

from .commands.agent import agent_app
from .commands.agentctl import register as register_agentctl
from .commands.config_cmd import register as register_config
from .commands.context import context_app
from .commands.dev import dev_app
from .commands.dispatch import register as register_dispatch
from .commands.feedback import feedback_app
from .commands.governance import register as register_governance
from .commands.mcp import mcp_app
from .commands.model import register as register_model
from .commands.plugins_cmd import plugins_app
from .commands.prompt import prompt_app
from .commands.quickstart import quickstart_app
from .commands.root import app as root_app
from .commands.session import session_app
from .commands.tasks import register as register_tasks
from .commands.tasks import task_app
from .commands.template import template_app
from .commands.tools import tools_app
from .commands.train import train_app

app = typer.Typer()

# root commands
app.add_typer(root_app)

# sub command groups
app.add_typer(session_app, name="session")
app.add_typer(agent_app, name="agent")
app.add_typer(context_app, name="context")
app.add_typer(prompt_app, name="prompt")
app.add_typer(template_app, name="template")
app.add_typer(quickstart_app, name="quickstart")
app.add_typer(feedback_app, name="feedback")
app.add_typer(tools_app, name="tools")
app.add_typer(train_app, name="train")
app.add_typer(dev_app, name="dev")
app.add_typer(mcp_app, name="mcp")
app.add_typer(plugins_app, name="plugins")
register_tasks(app)
register_model(app)
register_config(app)
register_governance(app)

# additional command registrations
register_agentctl(agent_app)
register_dispatch(task_app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
