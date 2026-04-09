"""Simplified Codex execution adapter."""

from __future__ import annotations

import json
import subprocess
import time

from core.decision.agent_descriptor import AgentDescriptor
from core.models.errors import StructuredError

from .base import BaseExecutionAdapter, ExecutionResult


class CodexExecutionAdapter(BaseExecutionAdapter):
    """Minimal Codex adapter using a CLI-style invocation."""

    adapter_name = "codex"

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(self, task, agent_descriptor: AgentDescriptor) -> ExecutionResult:
        self.validate(task, agent_descriptor)
        prompt = self.task_text(task).strip()
        if not prompt:
            raise ValueError("Codex prompt must not be empty")
        command = [
            str(agent_descriptor.metadata.get("command") or "codex"),
            "exec",
            "--json",
            prompt,
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                error=StructuredError(
                    error_code="adapter_timeout",
                    message="Codex CLI timed out",
                    details={"adapter": self.adapter_name},
                ),
                metadata={"adapter": self.adapter_name, "command": command[0]},
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if completed.returncode != 0:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                raw_output=completed.stdout,
                error=StructuredError(
                    error_code="adapter_process_error",
                    message="Codex CLI failed",
                    details={
                        "adapter": self.adapter_name,
                        "returncode": completed.returncode,
                        "stderr": completed.stderr.strip(),
                    },
                ),
                duration_ms=duration_ms,
                metadata={"adapter": self.adapter_name, "command": command[0]},
            )
        try:
            data = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                raw_output=completed.stdout,
                error=StructuredError(
                    error_code="adapter_protocol_error",
                    message="Codex CLI returned invalid JSON",
                    details={"adapter": self.adapter_name, "exception": str(exc)},
                ),
                duration_ms=duration_ms,
                metadata={"adapter": self.adapter_name, "command": command[0]},
            )
        output = data.get("result") or data.get("output") or data
        return ExecutionResult(
            agent_id=agent_descriptor.agent_id,
            success=True,
            output=output,
            raw_output=data,
            duration_ms=duration_ms,
            metadata={"adapter": self.adapter_name, "command": command[0]},
        )

