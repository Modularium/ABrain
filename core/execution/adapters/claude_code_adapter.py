"""Headless Claude Code execution adapter."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.decision.agent_descriptor import AgentDescriptor, AgentExecutionKind, AgentSourceType
from core.models.errors import StructuredError
from core.execution.provider_capabilities import ExecutionCapabilities
from core.execution.adapters.manifest import AdapterManifest, RiskTier
from core.execution.adapters.budget import AdapterBudget, IsolationRequirements

from .base import BaseExecutionAdapter, ExecutionResult


class ClaudeCodeExecutionAdapter(BaseExecutionAdapter):
    """Execute a task through the Claude CLI in JSON mode."""

    adapter_name = "claude_code"

    capabilities = ExecutionCapabilities(
        execution_protocol="cli_process",
        requires_network=False,
        requires_local_process=True,
        supports_cost_reporting=True,
        supports_token_reporting=True,
        runtime_constraints=["requires_claude_cli"],
    )

    manifest = AdapterManifest(
        adapter_name="claude_code",
        description=(
            "Headless Claude Code CLI adapter. Spawns a local ``claude -p`` "
            "subprocess with full filesystem access in the configured working "
            "directory."
        ),
        capabilities=ExecutionCapabilities(
            execution_protocol="cli_process",
            requires_network=False,
            requires_local_process=True,
            supports_cost_reporting=True,
            supports_token_reporting=True,
            runtime_constraints=["requires_claude_cli"],
        ),
        risk_tier=RiskTier.HIGH,
        required_metadata_keys=[],
        optional_metadata_keys=["command", "cwd", "allowed_tools", "permission_mode"],
        recommended_policy_scope="code_execution",
        budget=AdapterBudget(
            max_cost_usd=5.0,
            max_duration_ms=120_000,
        ),
        isolation=IsolationRequirements(
            network_access_required=True,
            filesystem_write_required=True,
            process_spawn_required=True,
            privileged_operation=False,
        ),
    )

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def validate(self, task, agent_descriptor: AgentDescriptor) -> None:
        super().validate(task, agent_descriptor)
        if agent_descriptor.source_type != AgentSourceType.CLAUDE_CODE:
            raise ValueError("Claude Code adapter requires source_type='claude_code'")
        if agent_descriptor.execution_kind not in {
            AgentExecutionKind.LOCAL_PROCESS,
            AgentExecutionKind.CLOUD_AGENT,
        }:
            raise ValueError("Claude Code adapter requires execution_kind='local_process'")
        if not self.task_text(task).strip():
            raise ValueError("Claude Code prompt must not be empty")

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
                    message="Claude Code CLI was not found",
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
                    message="Claude Code CLI timed out",
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
                    message="Claude Code CLI failed",
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
                    message="Claude Code CLI returned invalid JSON",
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
        command = [str(agent_descriptor.metadata.get("command") or "claude"), "-p", prompt, "--output", "json"]
        allowed_tools = agent_descriptor.metadata.get("allowed_tools")
        if isinstance(allowed_tools, list) and allowed_tools:
            command.extend(["--allowedTools", ",".join(str(tool) for tool in allowed_tools)])
        permission_mode = agent_descriptor.metadata.get("permission_mode")
        if isinstance(permission_mode, str) and permission_mode:
            command.extend(["--permission-mode", permission_mode])
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
            raise ValueError("Claude Code JSON output must be an object")
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
            "command_mode": "headless_cli_v1",
            "cwd": cwd,
            "allowed_tools": list(agent_descriptor.metadata.get("allowed_tools") or []),
            "permission_mode": agent_descriptor.metadata.get("permission_mode"),
        }
