"""Rule-based execution plan builder."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.model_context import ModelContext, TaskContext

from .agent_descriptor import AgentExecutionKind, AgentSourceType
from .capabilities import CapabilityRisk
from .plan_models import ExecutionPlan, PlanStep, PlanStrategy
from .planner import Planner
from .task_intent import PlannerResult


class PlanBuilder:
    """Build execution plans from canonical task inputs."""

    def __init__(self, *, planner: Planner | None = None) -> None:
        self.planner = planner or Planner()

    def build(
        self,
        task: TaskContext | ModelContext | Mapping[str, Any],
        *,
        planner_result: PlannerResult | None = None,
    ) -> ExecutionPlan:
        planner_result = planner_result or self.planner.plan(task)
        normalized_task = dict(planner_result.normalized_task)
        task_id = self._extract_task_id(task)
        intent = planner_result.intent
        if self._is_complex_code_task(intent):
            steps = self._build_complex_code_plan(intent)
            strategy = (
                PlanStrategy.PARALLEL_GROUPS
                if any(step.allow_parallel_group for step in steps)
                else PlanStrategy.SEQUENTIAL
            )
        elif self._is_complex_analysis_task(intent):
            steps = self._build_analysis_plan(intent)
            strategy = PlanStrategy.SEQUENTIAL
        else:
            steps = [self._single_step(intent)]
            strategy = PlanStrategy.SINGLE
        return ExecutionPlan(
            task_id=task_id,
            original_task=normalized_task,
            steps=steps,
            strategy=strategy,
            metadata={
                "builder_version": "v1",
                "intent_domain": intent.domain,
                "task_type": intent.task_type,
            },
        )

    def _single_step(self, intent) -> PlanStep:
        return PlanStep(
            step_id="step-1",
            title=intent.task_type.replace("_", " ").title(),
            description=intent.description or f"Execute task {intent.task_type}",
            required_capabilities=list(intent.required_capabilities),
            risk=intent.risk,
            metadata={"task_type": intent.task_type, "domain": intent.domain},
        )

    def _build_complex_code_plan(self, intent) -> list[PlanStep]:
        allow_parallel_quality = bool(intent.execution_hints.get("allow_parallel_quality_checks"))
        steps = [
            PlanStep(
                step_id="analyze",
                title="Analyze Task",
                description="Analyze the requested change and identify constraints.",
                required_capabilities=["analysis.code"],
                preferred_source_types=[AgentSourceType.CLAUDE_CODE, AgentSourceType.CODEX],
                preferred_execution_kinds=[AgentExecutionKind.LOCAL_PROCESS],
                risk=CapabilityRisk.LOW,
                metadata={"task_type": "code_analyze", "domain": "code"},
            ),
            PlanStep(
                step_id="implement",
                title="Implement Change",
                description=intent.description or "Implement the requested code changes.",
                required_capabilities=self._implementation_capabilities(intent),
                preferred_source_types=[
                    AgentSourceType.OPENHANDS,
                    AgentSourceType.CODEX,
                    AgentSourceType.CLAUDE_CODE,
                ],
                preferred_execution_kinds=[
                    AgentExecutionKind.HTTP_SERVICE,
                    AgentExecutionKind.LOCAL_PROCESS,
                ],
                inputs_from_steps=["analyze"],
                risk=intent.risk,
                metadata={"task_type": intent.task_type, "domain": "code"},
            ),
        ]
        quality_group = "quality" if allow_parallel_quality else None
        steps.append(
            PlanStep(
                step_id="test",
                title="Run Tests",
                description="Execute or prepare relevant tests for the change.",
                required_capabilities=["tests.run"],
                preferred_source_types=[AgentSourceType.OPENHANDS, AgentSourceType.CODEX],
                preferred_execution_kinds=[
                    AgentExecutionKind.HTTP_SERVICE,
                    AgentExecutionKind.LOCAL_PROCESS,
                ],
                inputs_from_steps=["implement"],
                risk=CapabilityRisk.LOW,
                allow_parallel_group=quality_group,
                metadata={"task_type": "code_test", "domain": "code"},
            )
        )
        steps.append(
            PlanStep(
                step_id="review",
                title="Review Change",
                description="Review the produced change for correctness and quality.",
                required_capabilities=["review.code"],
                preferred_source_types=[AgentSourceType.CLAUDE_CODE, AgentSourceType.CODEX],
                preferred_execution_kinds=[AgentExecutionKind.LOCAL_PROCESS],
                inputs_from_steps=["implement"] if allow_parallel_quality else ["test"],
                risk=CapabilityRisk.LOW,
                allow_parallel_group=quality_group,
                metadata={"task_type": "code_review", "domain": "code"},
            )
        )
        return steps

    def _build_analysis_plan(self, intent) -> list[PlanStep]:
        return [
            PlanStep(
                step_id="analyze",
                title="Analyze Input",
                description=intent.description or "Analyze the available input.",
                required_capabilities=["analysis.general"],
                risk=CapabilityRisk.LOW,
                metadata={"task_type": "analyze", "domain": intent.domain},
            ),
            PlanStep(
                step_id="transform",
                title="Transform Findings",
                description="Transform the findings into a structured result.",
                required_capabilities=list(intent.required_capabilities),
                inputs_from_steps=["analyze"],
                risk=intent.risk,
                metadata={"task_type": intent.task_type, "domain": intent.domain},
            ),
            PlanStep(
                step_id="document",
                title="Document Output",
                description="Document the result in a concise artifact.",
                required_capabilities=["docs.write"],
                inputs_from_steps=["transform"],
                risk=CapabilityRisk.LOW,
                metadata={"task_type": "docs_generate", "domain": intent.domain},
            ),
        ]

    def _implementation_capabilities(self, intent) -> list[str]:
        capabilities = [capability for capability in intent.required_capabilities if capability != "analysis.code"]
        return capabilities or ["code.generate"]

    def _is_complex_code_task(self, intent) -> bool:
        complexity = str(intent.execution_hints.get("complexity") or "").lower()
        task_scale = str(intent.execution_hints.get("task_scale") or "").lower()
        return intent.domain == "code" and (
            intent.execution_hints.get("multi_step")
            or intent.execution_hints.get("requires_tests")
            or intent.execution_hints.get("requires_review")
            or task_scale in {"large", "xl"}
            or complexity in {"high", "complex"}
            or intent.task_type in {"code_generate", "code_refactor"}
        )

    def _is_complex_analysis_task(self, intent) -> bool:
        return intent.domain == "analysis" and bool(intent.execution_hints.get("multi_step"))

    def _extract_task_id(self, task: TaskContext | ModelContext | Mapping[str, Any]) -> str:
        if isinstance(task, ModelContext):
            if task.task_context is not None:
                return self._extract_task_id(task.task_context)
            return task.uuid
        if isinstance(task, TaskContext):
            return task.task_id
        if isinstance(task, Mapping):
            return str(task.get("task_id") or task.get("id") or task.get("task_type") or "task")
        raise TypeError(f"Unsupported task input for plan building: {type(task)!r}")
