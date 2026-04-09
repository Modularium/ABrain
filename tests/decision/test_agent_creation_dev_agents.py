import pytest

from core.decision import (
    AgentCreationEngine,
    AgentDescriptor,
    AgentExecutionKind,
    AgentSourceType,
    FeedbackLoop,
    OnlineUpdater,
    PerformanceHistoryStore,
)
from core.execution.adapters.base import ExecutionResult
from core.model_context import TaskContext

pytestmark = pytest.mark.unit


def test_agent_creation_prefers_openhands_for_self_hosted_code_tasks():
    engine = AgentCreationEngine()

    descriptor = engine.create_agent_from_task(
        TaskContext(
            task_type="code_refactor",
            description="Refactor this worker",
            preferences={"execution_hints": {"self_hosted_preferred": True}},
        ),
        ["code.refactor", "repo.modify"],
    )

    assert descriptor.source_type == AgentSourceType.OPENHANDS
    assert descriptor.execution_kind == AgentExecutionKind.HTTP_SERVICE


def test_agent_creation_prefers_claude_code_for_policy_driven_headless_tasks():
    engine = AgentCreationEngine()

    descriptor = engine.create_agent_from_task(
        TaskContext(
            task_type="code_review",
            description="Review the patch",
            preferences={
                "execution_hints": {
                    "headless_cli_required": True,
                    "allowed_tools": ["Read"],
                    "permission_mode": "acceptEdits",
                }
            },
        ),
        ["review.code", "code.analyze"],
    )

    assert descriptor.source_type == AgentSourceType.CLAUDE_CODE
    assert descriptor.execution_kind == AgentExecutionKind.LOCAL_PROCESS


def test_agent_creation_prefers_codex_for_large_cloud_code_tasks():
    engine = AgentCreationEngine()

    descriptor = engine.create_agent_from_task(
        TaskContext(
            task_type="code_generate",
            description="Generate a large refactor plan",
            preferences={"execution_hints": {"cloud_preferred": True, "task_scale": "large"}},
        ),
        ["code.generate", "repo.modify", "tests.run"],
    )

    assert descriptor.source_type == AgentSourceType.CODEX
    assert descriptor.execution_kind == AgentExecutionKind.LOCAL_PROCESS


def test_feedback_loop_accepts_native_dev_agent_results_without_special_paths():
    feedback = FeedbackLoop(
        performance_history=PerformanceHistoryStore(),
        online_updater=OnlineUpdater(train_every=100),
    )
    descriptor = AgentDescriptor(
        agent_id="codex-agent",
        display_name="Codex",
        source_type=AgentSourceType.CODEX,
        execution_kind=AgentExecutionKind.LOCAL_PROCESS,
        capabilities=["code.generate", "repo.modify", "tests.run"],
    )

    update = feedback.update_performance(
        "codex-agent",
        ExecutionResult(
            agent_id="codex-agent",
            success=True,
            duration_ms=1200,
            cost=0.03,
            output={"status": "ok"},
            metadata={"adapter": "codex"},
        ),
        task={"task_type": "code_generate", "description": "Generate tests"},
        agent_descriptor=descriptor,
    )

    assert update.performance.execution_count == 1
    assert update.dataset_size == 1
    assert update.reward is not None
    assert update.warnings == []
