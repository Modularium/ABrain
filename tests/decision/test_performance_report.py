"""Phase §6.5 Efficiency — AgentPerformanceReporter tests."""

from __future__ import annotations

import pytest

from core.decision import (
    AgentPerformanceEntry,
    AgentPerformanceHistory,
    AgentPerformanceReport,
    AgentPerformanceReporter,
    AgentPerformanceTotals,
    PerformanceHistoryStore,
)

pytestmark = pytest.mark.unit


def _populate(store: PerformanceHistoryStore) -> None:
    store.set(
        "cheap-agent",
        AgentPerformanceHistory(
            success_rate=0.9,
            avg_latency=0.5,
            avg_cost=0.001,
            execution_count=100,
            recent_failures=2,
            load_factor=0.3,
        ),
    )
    store.set(
        "expensive-agent",
        AgentPerformanceHistory(
            success_rate=0.7,
            avg_latency=4.0,
            avg_cost=0.05,
            execution_count=20,
            recent_failures=1,
            load_factor=0.6,
        ),
    )
    store.set(
        "fresh-agent",
        AgentPerformanceHistory(
            success_rate=0.5,
            avg_latency=1.0,
            avg_cost=0.01,
            execution_count=0,
            recent_failures=0,
            load_factor=0.0,
        ),
    )


class TestStoreSnapshot:
    def test_snapshot_returns_independent_copy(self):
        store = PerformanceHistoryStore()
        store.set("a1", AgentPerformanceHistory(execution_count=5))
        snap = store.snapshot()
        assert snap == {"a1": AgentPerformanceHistory(execution_count=5)}
        snap["new"] = AgentPerformanceHistory(execution_count=999)
        assert "new" not in store.snapshot()


class TestReportBasics:
    def test_empty_store_returns_empty_report_with_zero_totals(self):
        reporter = AgentPerformanceReporter(store=PerformanceHistoryStore())
        report = reporter.generate()
        assert isinstance(report, AgentPerformanceReport)
        assert report.entries == []
        assert report.totals == AgentPerformanceTotals(
            agents=0,
            total_executions=0,
            total_recent_failures=0,
            weighted_success_rate=0.0,
            weighted_avg_latency=0.0,
            weighted_avg_cost=0.0,
        )

    def test_all_agents_included_by_default(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate()
        assert {e.agent_id for e in report.entries} == {
            "cheap-agent",
            "expensive-agent",
            "fresh-agent",
        }

    def test_entry_fields_round_trip_from_history(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate(
            sort_key="agent_id", descending=False
        )
        by_id = {e.agent_id: e for e in report.entries}
        cheap = by_id["cheap-agent"]
        assert cheap.success_rate == pytest.approx(0.9)
        assert cheap.avg_latency == pytest.approx(0.5)
        assert cheap.avg_cost == pytest.approx(0.001)
        assert cheap.execution_count == 100
        assert cheap.recent_failures == 2
        assert cheap.load_factor == pytest.approx(0.3)


class TestSorting:
    def test_default_sort_avg_cost_descending(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate()
        assert report.sort_key == "avg_cost"
        assert report.descending is True
        assert [e.agent_id for e in report.entries] == [
            "expensive-agent",
            "fresh-agent",
            "cheap-agent",
        ]

    def test_sort_by_latency_ascending(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate(
            sort_key="avg_latency", descending=False
        )
        assert [e.agent_id for e in report.entries] == [
            "cheap-agent",
            "fresh-agent",
            "expensive-agent",
        ]

    def test_sort_by_success_rate_descending(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate(
            sort_key="success_rate", descending=True
        )
        assert [e.agent_id for e in report.entries] == [
            "cheap-agent",
            "expensive-agent",
            "fresh-agent",
        ]

    def test_sort_by_agent_id(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate(
            sort_key="agent_id", descending=False
        )
        assert [e.agent_id for e in report.entries] == [
            "cheap-agent",
            "expensive-agent",
            "fresh-agent",
        ]


class TestFilters:
    def test_min_executions_filter(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate(min_executions=1)
        ids = {e.agent_id for e in report.entries}
        assert ids == {"cheap-agent", "expensive-agent"}
        assert report.min_executions == 1

    def test_agent_ids_allowlist(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate(
            agent_ids=["cheap-agent", "unknown-agent"]
        )
        ids = {e.agent_id for e in report.entries}
        assert ids == {"cheap-agent", "unknown-agent"}
        # Unknown agent comes in via store defaults (execution_count=0).
        unknown = next(e for e in report.entries if e.agent_id == "unknown-agent")
        assert unknown.execution_count == 0
        assert unknown.success_rate == pytest.approx(0.5)


class TestTotals:
    def test_weighted_totals_scale_by_execution_count(self):
        store = PerformanceHistoryStore()
        _populate(store)
        report = AgentPerformanceReporter(store=store).generate(min_executions=1)
        totals = report.totals
        # cheap-agent: 100 runs; expensive-agent: 20 runs; total = 120.
        assert totals.agents == 2
        assert totals.total_executions == 120
        assert totals.total_recent_failures == 3
        # Weighted success_rate: (0.9 * 100 + 0.7 * 20) / 120 = 104/120 ≈ 0.8667
        assert totals.weighted_success_rate == pytest.approx((0.9 * 100 + 0.7 * 20) / 120)
        # Weighted latency: (0.5 * 100 + 4.0 * 20) / 120 = 130/120 ≈ 1.0833
        assert totals.weighted_avg_latency == pytest.approx((0.5 * 100 + 4.0 * 20) / 120)
        # Weighted cost: (0.001 * 100 + 0.05 * 20) / 120 ≈ 0.00917
        assert totals.weighted_avg_cost == pytest.approx(
            (0.001 * 100 + 0.05 * 20) / 120
        )

    def test_zero_executions_totals_are_zero(self):
        store = PerformanceHistoryStore()
        store.set(
            "fresh",
            AgentPerformanceHistory(execution_count=0, success_rate=0.5, avg_cost=0.1),
        )
        report = AgentPerformanceReporter(store=store).generate()
        totals = report.totals
        assert totals.total_executions == 0
        assert totals.weighted_success_rate == 0.0
        assert totals.weighted_avg_latency == 0.0
        assert totals.weighted_avg_cost == 0.0


class TestSchema:
    def test_entry_extra_forbid(self):
        with pytest.raises(ValueError):
            AgentPerformanceEntry(
                agent_id="a",
                success_rate=0.5,
                avg_latency=1.0,
                avg_cost=0.0,
                avg_token_count=0.0,
                avg_user_rating=0.0,
                recent_failures=0,
                execution_count=0,
                load_factor=0.0,
                rogue="nope",  # type: ignore[call-arg]
            )

    def test_report_extra_forbid(self):
        from datetime import UTC, datetime

        with pytest.raises(ValueError):
            AgentPerformanceReport(
                generated_at=datetime.now(UTC),
                sort_key="avg_cost",
                descending=True,
                min_executions=0,
                entries=[],
                totals=AgentPerformanceTotals(
                    agents=0,
                    total_executions=0,
                    total_recent_failures=0,
                    weighted_success_rate=0.0,
                    weighted_avg_latency=0.0,
                    weighted_avg_cost=0.0,
                ),
                rogue="nope",  # type: ignore[call-arg]
            )
