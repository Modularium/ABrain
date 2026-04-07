"""Stable runtime wrappers around legacy agent classes."""

from __future__ import annotations

from typing import Any

from agents.chatbot_agent import ChatbotAgent
from agents.supervisor_agent import SupervisorAgent

from core.execution.dispatcher import maybe_await, run_sync


class AgentRuntime:
    """Wrap legacy agents behind consistent sync and async entrypoints."""

    def __init__(
        self,
        supervisor: SupervisorAgent | None = None,
        chatbot: ChatbotAgent | None = None,
    ) -> None:
        self.supervisor = supervisor or SupervisorAgent()
        self.chatbot = chatbot or ChatbotAgent(self.supervisor)

    async def execute_task(self, task_description: str, context: Any | None = None):
        """Execute a task regardless of the legacy method shape."""
        return await maybe_await(self.supervisor.execute_task(task_description, context))

    async def handle_user_message(self, user_message: str):
        """Handle a user message regardless of the legacy method shape."""
        return await maybe_await(self.chatbot.handle_user_message(user_message))

    def execute_task_sync(self, task_description: str, context: Any | None = None):
        """Synchronously execute a task."""
        return run_sync(self.supervisor.execute_task(task_description, context))

    def handle_user_message_sync(self, user_message: str):
        """Synchronously handle a user message."""
        return run_sync(self.chatbot.handle_user_message(user_message))
