"""Phase 5 – LearningOps L1: LearningRecord schema, DatasetBuilder, DataQualityFilter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.approval.models import ApprovalRequest, ApprovalStatus
from core.approval.store import ApprovalStore
from core.audit.trace_store import TraceStore
from core.audit.trace_models import ExplainabilityRecord
from core.decision.learning.dataset_builder import DatasetBuilder
from core.decision.learning.quality import DataQualityFilter, QualityViolation
from core.decision.learning.record import LearningRecord

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# LearningRecord schema
# ---------------------------------------------------------------------------


class TestLearningRecord:
    def test_minimal_record_valid(self):
        rec = LearningRecord(trace_id="t1", workflow_name="w1")
        assert rec.trace_id == "t1"
        assert rec.workflow_name == "w1"
        assert rec.candidate_agent_ids == []
        assert rec.matched_policy_ids == []
        assert not rec.has_routing_decision
        assert not rec.has_outcome
        assert not rec.has_approval_outcome

    def test_quality_score_no_flags(self):
        rec = LearningRecord(trace_id="t1", workflow_name="w1")
        assert rec.quality_score() == 0.0

    def test_quality_score_all_flags(self):
        rec = LearningRecord(
            trace_id="t1",
            workflow_name="w1",
            has_routing_decision=True,
            has_outcome=True,
            has_approval_outcome=True,
        )
        assert rec.quality_score() == pytest.approx(1.0)

    def test_quality_score_partial(self):
        rec = LearningRecord(
            trace_id="t1",
            workflow_name="w1",
            has_routing_decision=True,
            has_outcome=False,
            has_approval_outcome=False,
        )
        assert rec.quality_score() == pytest.approx(1 / 3)

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            LearningRecord(trace_id="t1", workflow_name="w1", unknown_field="x")  # type: ignore[call-arg]

    def test_full_record(self):
        rec = LearningRecord(
            trace_id="t-abc",
            workflow_name="routing-test",
            task_type="code_review",
            task_id="task-1",
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T00:00:05+00:00",
            trace_status="ok",
            selected_agent_id="agent-1",
            candidate_agent_ids=["agent-1", "agent-2"],
            selected_score=0.87,
            routing_confidence=0.92,
            score_gap=0.15,
            confidence_band="high",
            policy_effect="allow",
            matched_policy_ids=["p-001"],
            approval_required=False,
            approval_id=None,
            approval_decision=None,
            success=True,
            cost_usd=0.003,
            latency_ms=1200.0,
            has_routing_decision=True,
            has_outcome=True,
            has_approval_outcome=False,
        )
        assert rec.selected_agent_id == "agent-1"
        assert rec.success is True
        assert rec.quality_score() == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# DataQualityFilter
# ---------------------------------------------------------------------------


class TestDataQualityFilter:
    def _record(self, **kwargs) -> LearningRecord:
        defaults = dict(
            trace_id="t1",
            workflow_name="w1",
            has_routing_decision=True,
            has_outcome=True,
            has_approval_outcome=False,
        )
        defaults.update(kwargs)
        return LearningRecord(**defaults)

    def test_default_filter_accepts_record_with_routing(self):
        filt = DataQualityFilter()
        rec = self._record(has_routing_decision=True)
        assert filt.validate(rec) == []

    def test_default_filter_rejects_record_without_routing(self):
        filt = DataQualityFilter()
        rec = self._record(has_routing_decision=False)
        violations = filt.validate(rec)
        assert len(violations) == 1
        assert violations[0].field == "has_routing_decision"

    def test_require_outcome_rejects_missing_outcome(self):
        filt = DataQualityFilter(require_outcome=True)
        rec = self._record(has_outcome=False)
        violations = filt.validate(rec)
        assert any(v.field == "has_outcome" for v in violations)

    def test_require_approval_outcome_rejects_unresolved(self):
        filt = DataQualityFilter(require_approval_outcome=True)
        rec = self._record(has_approval_outcome=False)
        violations = filt.validate(rec)
        assert any(v.field == "has_approval_outcome" for v in violations)

    def test_min_quality_score_rejects_low_score(self):
        filt = DataQualityFilter(
            require_routing_decision=False,
            min_quality_score=0.5,
        )
        rec = self._record(
            has_routing_decision=False,
            has_outcome=False,
            has_approval_outcome=False,
        )
        violations = filt.validate(rec)
        assert any(v.field == "quality_score" for v in violations)

    def test_filter_removes_rejected(self):
        filt = DataQualityFilter()
        good = self._record(has_routing_decision=True)
        bad = self._record(has_routing_decision=False)
        result = filt.filter([good, bad])
        assert result == [good]

    def test_filter_with_report_separates(self):
        filt = DataQualityFilter()
        good = self._record(has_routing_decision=True)
        bad = self._record(has_routing_decision=False)
        accepted, rejected = filt.filter_with_report([good, bad])
        assert len(accepted) == 1
        assert len(rejected) == 1
        assert rejected[0][0] is bad
        assert rejected[0][1][0].field == "has_routing_decision"

    def test_quality_violation_is_frozen_dataclass(self):
        v = QualityViolation(field="f", reason="r")
        with pytest.raises(Exception):
            v.field = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DatasetBuilder
# ---------------------------------------------------------------------------


def _make_trace_store(tmp_path: Path) -> TraceStore:
    return TraceStore(str(tmp_path / "traces.sqlite3"))


def _make_approval_store() -> ApprovalStore:
    return ApprovalStore()


class TestDatasetBuilder:
    def test_empty_store_returns_empty_list(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        builder = DatasetBuilder(trace_store=ts)
        records = builder.build()
        assert records == []

    def test_invalid_limit_raises(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        builder = DatasetBuilder(trace_store=ts)
        with pytest.raises(ValueError, match="limit must be positive"):
            builder.build(limit=0)

    def test_trace_without_explainability_yields_record_without_routing(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        ts.create_trace("my-workflow", task_id="task-1")
        builder = DatasetBuilder(trace_store=ts)
        records = builder.build()
        assert len(records) == 1
        rec = records[0]
        assert rec.workflow_name == "my-workflow"
        assert not rec.has_routing_decision
        assert not rec.has_outcome

    def test_trace_with_explainability_yields_routing_fields(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        trace = ts.create_trace("routing-workflow", task_id="t-1")
        ts.store_explainability(
            ExplainabilityRecord(
                trace_id=trace.trace_id,
                step_id="step-1",
                selected_agent_id="agent-A",
                candidate_agent_ids=["agent-A", "agent-B"],
                selected_score=0.85,
                routing_reason_summary="highest score",
                matched_policy_ids=["p-1"],
                approval_required=False,
                routing_confidence=0.9,
                score_gap=0.12,
                confidence_band="high",
                policy_effect="allow",
            )
        )
        builder = DatasetBuilder(trace_store=ts)
        records = builder.build()
        assert len(records) == 1
        rec = records[0]
        assert rec.has_routing_decision
        assert rec.selected_agent_id == "agent-A"
        assert rec.candidate_agent_ids == ["agent-A", "agent-B"]
        assert rec.selected_score == pytest.approx(0.85)
        assert rec.routing_confidence == pytest.approx(0.9)
        assert rec.confidence_band == "high"
        assert rec.policy_effect == "allow"
        assert not rec.approval_required

    def test_trace_with_outcome_metadata(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        ts.create_trace("outcome-workflow", metadata={"success": True, "cost_usd": 0.005, "latency_ms": 800.0})
        builder = DatasetBuilder(trace_store=ts)
        records = builder.build()
        assert len(records) == 1
        rec = records[0]
        assert rec.success is True
        assert rec.cost_usd == pytest.approx(0.005)
        assert rec.latency_ms == pytest.approx(800.0)
        assert rec.has_outcome

    def test_trace_with_approval_joins_store(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        approvals = _make_approval_store()

        from core.decision.capabilities import CapabilityRisk

        approval_req = ApprovalRequest(
            approval_id="appr-001",
            plan_id="plan-1",
            step_id="step-1",
            task_summary="Deploy to production",
            agent_id="agent-A",
            reason="High-risk deployment requires human sign-off",
            risk=CapabilityRisk.HIGH,
            proposed_action_summary="Deploy service v2.0 to prod cluster",
        )
        approvals.create_request(approval_req)
        from core.approval.models import ApprovalDecision

        approvals.record_decision(
            "appr-001",
            ApprovalDecision(
                approval_id="appr-001",
                decision=ApprovalStatus.APPROVED,
                decided_by="human-reviewer",
            ),
        )

        trace = ts.create_trace("approval-workflow")
        ts.store_explainability(
            ExplainabilityRecord(
                trace_id=trace.trace_id,
                step_id="step-1",
                selected_agent_id="agent-A",
                candidate_agent_ids=["agent-A"],
                selected_score=0.9,
                routing_reason_summary="only candidate",
                matched_policy_ids=[],
                approval_required=True,
                approval_id="appr-001",
            )
        )

        builder = DatasetBuilder(trace_store=ts, approval_store=approvals)
        records = builder.build()
        assert len(records) == 1
        rec = records[0]
        assert rec.approval_required
        assert rec.approval_id == "appr-001"
        assert rec.approval_decision == "approved"
        assert rec.has_approval_outcome

    def test_no_approval_store_leaves_approval_fields_empty(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        trace = ts.create_trace("workflow-no-approval")
        ts.store_explainability(
            ExplainabilityRecord(
                trace_id=trace.trace_id,
                step_id="step-1",
                selected_agent_id="agent-X",
                candidate_agent_ids=["agent-X"],
                selected_score=0.75,
                routing_reason_summary="only option",
                matched_policy_ids=[],
                approval_required=True,
                approval_id="appr-xyz",
            )
        )
        builder = DatasetBuilder(trace_store=ts, approval_store=None)
        records = builder.build()
        rec = records[0]
        assert rec.approval_id == "appr-xyz"
        assert rec.approval_decision is None
        assert not rec.has_approval_outcome

    def test_limit_is_respected(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        for i in range(5):
            ts.create_trace(f"workflow-{i}")
        builder = DatasetBuilder(trace_store=ts)
        records = builder.build(limit=3)
        assert len(records) == 3

    def test_builder_is_read_only_on_stores(self, tmp_path):
        ts = _make_trace_store(tmp_path)
        ts.create_trace("w1")
        before = ts.list_recent_traces(10)
        builder = DatasetBuilder(trace_store=ts)
        builder.build()
        after = ts.list_recent_traces(10)
        assert len(before) == len(after)
