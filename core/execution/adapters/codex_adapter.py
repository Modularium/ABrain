"""Simplified Codex execution adapter."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.models.errors import StructuredError

from .base import BaseExecutionAdapter, ExecutionResult


class CodexExecutionAdapter(BaseExecutionAdapter):
    """Minimal Codex adapter using a CLI-style invocation."""

    adapter_name = "codex"

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def validate(self, task, agent_descriptor: AgentDescriptor) -> None:
        super().validate(task, agent_descriptor)
        if agent_descriptor.source_type != AgentSourceType.CODEX:
            raise ValueError("Codex adapter requires source_type='codex'")
        if agent_descriptor.execution_kind not in {
            AgentExecutionKind.LOCAL_PROCESS,
            AgentExecutionKind.CLOUD_AGENT,
        }:
            raise ValueError("Codex adapter requires execution_kind='local_process'")
        if not self.task_text(task).strip():
            raise ValueError("Codex prompt must not be empty")

    def execute(self, task, agent_descriptor: AgentDescriptor) -> ExecutionResult:
        self.validate(task, agent_descriptor)
        prompt = self.task_text(task).strip()
        command = self._build_command(prompt, agent_descriptor)
        cwd = self._resolve_cwd(agent_descriptor)
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            return ExecutionResult(
                agent_id=agent_descriptor.agent_id,
                success=False,
                error=StructuredError(
                    error_code="adapter_unavailable",
                    message="Codex CLI was not found",
                    details={"adapter": self.adapter_name, "exception": str(exc)},
                ),
                metadata=self._result_metadata(command, cwd, agent_descriptor),
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
                metadata=self._result_metadata(command, cwd, agent_descriptor),
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
                metadata=self._result_metadata(command, cwd, agent_descriptor),
            )
        try:
            data = self._decode_json_output(completed.stdout or "")
        except (json.JSONDecodeError, ValueError) as exc:
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
                metadata=self._result_metadata(command, cwd, agent_descriptor),
            )
        output = data.get("result") or data.get("output") or data
        return ExecutionResult(
            agent_id=agent_descriptor.agent_id,
            success=True,
            output=output,
            raw_output=data,
            duration_ms=duration_ms,
            cost=self._extract_cost(data),
            token_count=self._extract_token_count(data),
            metadata=self._result_metadata(command, cwd, agent_descriptor),
        )

    def _build_command(self, prompt: str, agent_descriptor: AgentDescriptor) -> list[str]:
        command = [str(agent_descriptor.metadata.get("command") or "codex"), "exec", "--json", prompt]
        model = agent_descriptor.metadata.get("model")
        if isinstance(model, str) and model:
            command.extend(["--model", model])
        sandbox = agent_descriptor.metadata.get("sandbox_mode")
        if isinstance(sandbox, str) and sandbox:
            command.extend(["--sandbox", sandbox])
        approval_mode = agent_descriptor.metadata.get("approval_mode")
        if isinstance(approval_mode, str) and approval_mode:
            command.extend(["--approval-mode", approval_mode])
        return command

    def _resolve_cwd(self, agent_descriptor: AgentDescriptor) -> str | None:
        cwd = agent_descriptor.metadata.get("cwd")
        if isinstance(cwd, str) and cwd.strip():
            return str(Path(cwd).expanduser())
        return None

    def _decode_json_output(self, stdout: str) -> Mapping[str, Any]:
        text = stdout.strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if not lines:
                return {}
            data = json.loads(lines[-1])
        if not isinstance(data, Mapping):
            raise ValueError("Codex JSON output must be an object")
        return data

    def _extract_cost(self, data: Mapping[str, Any]) -> float | None:
        for key in ("cost", "cost_usd", "total_cost"):
            value = data.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        usage = data.get("usage")
        if isinstance(usage, Mapping):
            for key in ("cost", "cost_usd", "total_cost"):
                value = usage.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        return None

    def _extract_token_count(self, data: Mapping[str, Any]) -> int | None:
        usage = data.get("usage")
        if isinstance(usage, Mapping):
            input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
            output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                total = input_tokens + output_tokens
                return total if total > 0 else None
        return None

    def _result_metadata(
        self,
        command: list[str],
        cwd: str | None,
        agent_descriptor: AgentDescriptor,
    ) -> dict[str, Any]:
        return {
            "adapter": self.adapter_name,
            "command": command[0],
            "command_mode": "cli_v1",
            "preferred_future_transport": "app_server_json_rpc",
            "cwd": cwd,
            "model": agent_descriptor.metadata.get("model"),
            "approval_mode": agent_descriptor.metadata.get("approval_mode"),
            "sandbox_mode": agent_descriptor.metadata.get("sandbox_mode"),
        }
