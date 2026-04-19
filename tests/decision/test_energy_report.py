"""Phase §6.5 Green AI — EnergyEstimator tests."""

from __future__ import annotations

import pytest

from core.decision import (
    AgentEnergyEstimate,
    AgentPerformanceHistory,
    EnergyEstimator,
    EnergyEstimatorConfig,
    EnergyProfile,
    EnergyReport,
    EnergyTotals,
    PerformanceHistoryStore,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _store(**agents: AgentPerformanceHistory) -> PerformanceHistoryStore:
    store = PerformanceHistoryStore()
    for agent_id, history in agents.items():
        store.set(agent_id, history)
    return store


def _config(
    *,
    default_watts: float = 50.0,
    profiles: dict[str, EnergyProfile] | None = None,
) -> EnergyEstimatorConfig:
    return EnergyEstimatorConfig(
        default_profile=EnergyProfile(avg_power_watts=default_watts),
        profiles=profiles or {},
    )


# ---------------------------------------------------------------------------
# Profile + config schema
# ---------------------------------------------------------------------------


class TestEnergyProfile:
    def test_profile_defaults_source_to_estimated(self):
        profile = EnergyProfile(avg_power_watts=100.0)
        assert profile.source == "estimated"

    def test_profile_accepts_known_sources(self):
        for source in ("measured", "vendor_spec", "estimated"):
            profile = EnergyProfile(avg_power_watts=10.0, source=source)
            assert profile.source == source

    def test_profile_rejects_negative_wattage(self):
        with pytest.raises(ValueError):
            EnergyProfile(avg_power_watts=-1.0)

    def test_profile_extra_forbid(self):
        with pytest.raises(ValueError):
            EnergyProfile(avg_power_watts=10.0, rogue="x")  # type: ignore[call-arg]

    def test_config_extra_forbid(self):
        with pytest.raises(ValueError):
            EnergyEstimatorConfig(
                default_profile=EnergyProfile(avg_power_watts=10.0),
                rogue="x",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# Empty store
# ---------------------------------------------------------------------------


class TestEmptyStore:
    def test_empty_store_yields_empty_report(self):
        report = EnergyEstimator(
            store=PerformanceHistoryStore(), config=_config()
        ).generate()
        assert isinstance(report, EnergyReport)
        assert report.entries == []
        assert report.fallback_agents == []
        assert report.totals == EnergyTotals(
            agents=0,
            total_executions=0,
            total_energy_joules=0.0,
            total_energy_wh=0.0,
            weighted_avg_power_watts=0.0,
        )


# ---------------------------------------------------------------------------
# Single-agent calculation
# ---------------------------------------------------------------------------


class TestSingleAgent:
    def test_energy_formula_is_watts_times_seconds_times_executions(self):
        store = _store(
            gpu=AgentPerformanceHistory(
                avg_latency=2.0,
                execution_count=10,
            ),
        )
        config = EnergyEstimatorConfig(
            default_profile=EnergyProfile(
                avg_power_watts=100.0, source="vendor_spec"
            ),
        )
        report = EnergyEstimator(store=store, config=config).generate()

        assert len(report.entries) == 1
        entry = report.entries[0]
        assert isinstance(entry, AgentEnergyEstimate)
        # 100 W * 2 s = 200 J per call
        assert entry.avg_energy_joules == pytest.approx(200.0)
        # 200 J * 10 = 2000 J total
        assert entry.total_energy_joules == pytest.approx(2000.0)
        # 2000 J / 3600 s/h ≈ 0.5556 Wh
        assert entry.total_energy_wh == pytest.approx(2000.0 / 3600.0)
        assert entry.profile_source == "vendor_spec"
        assert entry.used_default_profile is True

    def test_zero_latency_yields_zero_energy(self):
        store = _store(idle=AgentPerformanceHistory(avg_latency=0.0, execution_count=5))
        report = EnergyEstimator(store=store, config=_config()).generate()
        assert report.entries[0].total_energy_joules == 0.0

    def test_zero_executions_yields_zero_total_energy(self):
        store = _store(fresh=AgentPerformanceHistory(avg_latency=1.0, execution_count=0))
        report = EnergyEstimator(store=store, config=_config()).generate()
        assert report.entries[0].total_energy_joules == 0.0
        assert report.entries[0].avg_energy_joules == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Profile overrides + fallback tracking
# ---------------------------------------------------------------------------


class TestProfileResolution:
    def test_override_takes_precedence_over_default(self):
        store = _store(
            small=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
            big=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
        )
        config = _config(
            default_watts=10.0,
            profiles={"big": EnergyProfile(avg_power_watts=500.0, source="measured")},
        )
        report = EnergyEstimator(store=store, config=config).generate(
            sort_key="agent_id", descending=False
        )
        by_id = {e.agent_id: e for e in report.entries}
        assert by_id["small"].avg_power_watts == 10.0
        assert by_id["small"].profile_source == "estimated"
        assert by_id["small"].used_default_profile is True
        assert by_id["big"].avg_power_watts == 500.0
        assert by_id["big"].profile_source == "measured"
        assert by_id["big"].used_default_profile is False

    def test_fallback_agents_lists_agents_using_default_profile(self):
        store = _store(
            a=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
            b=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
            c=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
        )
        config = _config(
            profiles={"b": EnergyProfile(avg_power_watts=100.0, source="measured")},
        )
        report = EnergyEstimator(store=store, config=config).generate()
        assert report.fallback_agents == ["a", "c"]

    def test_fallback_list_is_sorted_for_stable_output(self):
        store = _store(
            z=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
            a=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
            m=AgentPerformanceHistory(avg_latency=1.0, execution_count=1),
        )
        report = EnergyEstimator(store=store, config=_config()).generate()
        assert report.fallback_agents == ["a", "m", "z"]


# ---------------------------------------------------------------------------
# Aggregation totals
# ---------------------------------------------------------------------------


class TestTotals:
    def test_totals_sum_joules_and_convert_to_wh(self):
        # agent A: 100 W * 1 s * 10 runs = 1000 J
        # agent B: 200 W * 2 s * 5 runs  = 2000 J
        store = _store(
            a=AgentPerformanceHistory(avg_latency=1.0, execution_count=10),
            b=AgentPerformanceHistory(avg_latency=2.0, execution_count=5),
        )
        config = _config(
            profiles={
                "a": EnergyProfile(avg_power_watts=100.0),
                "b": EnergyProfile(avg_power_watts=200.0),
            },
        )
        report = EnergyEstimator(store=store, config=config).generate()
        assert report.totals.agents == 2
        assert report.totals.total_executions == 15
        assert report.totals.total_energy_joules == pytest.approx(3000.0)
        assert report.totals.total_energy_wh == pytest.approx(3000.0 / 3600.0)

    def test_weighted_avg_power_is_execution_weighted(self):
        # 100 W (10 runs) + 200 W (30 runs) = (1000 + 6000)/40 = 175 W
        store = _store(
            a=AgentPerformanceHistory(avg_latency=0.1, execution_count=10),
            b=AgentPerformanceHistory(avg_latency=0.1, execution_count=30),
        )
        config = _config(
            profiles={
                "a": EnergyProfile(avg_power_watts=100.0),
                "b": EnergyProfile(avg_power_watts=200.0),
            },
        )
        report = EnergyEstimator(store=store, config=config).generate()
        assert report.totals.weighted_avg_power_watts == pytest.approx(175.0)

    def test_zero_executions_gives_zero_weighted_power(self):
        store = _store(
            a=AgentPerformanceHistory(avg_latency=1.0, execution_count=0),
        )
        report = EnergyEstimator(store=store, config=_config()).generate()
        assert report.totals.weighted_avg_power_watts == 0.0


# ---------------------------------------------------------------------------
# Sorting + filtering
# ---------------------------------------------------------------------------


class TestSortAndFilter:
    def _store_three(self) -> PerformanceHistoryStore:
        return _store(
            tiny=AgentPerformanceHistory(avg_latency=0.1, execution_count=1),
            medium=AgentPerformanceHistory(avg_latency=1.0, execution_count=10),
            huge=AgentPerformanceHistory(avg_latency=5.0, execution_count=100),
        )

    def test_default_sort_is_total_energy_descending(self):
        report = EnergyEstimator(
            store=self._store_three(), config=_config(default_watts=50.0)
        ).generate()
        assert [e.agent_id for e in report.entries] == ["huge", "medium", "tiny"]

    def test_sort_by_agent_id_ascending(self):
        report = EnergyEstimator(
            store=self._store_three(), config=_config()
        ).generate(sort_key="agent_id", descending=False)
        assert [e.agent_id for e in report.entries] == ["huge", "medium", "tiny"]

    def test_min_executions_filter_drops_low_activity_agents(self):
        report = EnergyEstimator(
            store=self._store_three(), config=_config()
        ).generate(min_executions=5)
        ids = {e.agent_id for e in report.entries}
        assert ids == {"medium", "huge"}
        assert report.min_executions == 5

    def test_agent_ids_allow_list_restricts_report(self):
        report = EnergyEstimator(
            store=self._store_three(), config=_config()
        ).generate(agent_ids=["huge"])
        assert [e.agent_id for e in report.entries] == ["huge"]

    def test_agent_ids_missing_from_store_surface_with_defaults(self):
        # Store has nothing for "unknown" — store.get returns the default
        # AgentPerformanceHistory (execution_count=0), so the entry appears
        # with zero energy. This lets operators see coverage gaps.
        report = EnergyEstimator(
            store=PerformanceHistoryStore(), config=_config()
        ).generate(agent_ids=["unknown"])
        assert len(report.entries) == 1
        assert report.entries[0].agent_id == "unknown"
        assert report.entries[0].total_energy_joules == 0.0


# ---------------------------------------------------------------------------
# Read-only behaviour
# ---------------------------------------------------------------------------


class TestReadOnly:
    def test_store_is_not_mutated_by_generate(self):
        store = _store(
            a=AgentPerformanceHistory(avg_latency=1.0, execution_count=3),
        )
        before = store.snapshot()
        EnergyEstimator(store=store, config=_config()).generate()
        EnergyEstimator(store=store, config=_config()).generate()
        after = store.snapshot()
        assert before == after

    def test_report_is_deterministic_for_stable_store(self):
        store = _store(
            a=AgentPerformanceHistory(avg_latency=1.0, execution_count=3),
            b=AgentPerformanceHistory(avg_latency=2.0, execution_count=7),
        )
        estimator = EnergyEstimator(store=store, config=_config())
        first = estimator.generate()
        second = estimator.generate()
        # generated_at differs; the analytical payload does not.
        assert first.entries == second.entries
        assert first.totals == second.totals
        assert first.fallback_agents == second.fallback_agents


# ---------------------------------------------------------------------------
# Schema hardening
# ---------------------------------------------------------------------------


class TestSchemaHardening:
    def test_estimate_extra_forbid(self):
        with pytest.raises(ValueError):
            AgentEnergyEstimate(
                agent_id="a",
                avg_power_watts=1.0,
                profile_source="estimated",
                used_default_profile=True,
                avg_latency_seconds=1.0,
                execution_count=1,
                avg_energy_joules=1.0,
                total_energy_joules=1.0,
                total_energy_wh=0.0,
                rogue="x",  # type: ignore[call-arg]
            )

    def test_totals_extra_forbid(self):
        with pytest.raises(ValueError):
            EnergyTotals(
                agents=0,
                total_executions=0,
                total_energy_joules=0.0,
                total_energy_wh=0.0,
                weighted_avg_power_watts=0.0,
                rogue="x",  # type: ignore[call-arg]
            )

    def test_report_extra_forbid(self):
        with pytest.raises(ValueError):
            EnergyReport(
                generated_at="2026-04-19T00:00:00+00:00",  # type: ignore[arg-type]
                sort_key="total_energy_joules",
                descending=True,
                min_executions=0,
                entries=[],
                totals=EnergyTotals(
                    agents=0,
                    total_executions=0,
                    total_energy_joules=0.0,
                    total_energy_wh=0.0,
                    weighted_avg_power_watts=0.0,
                ),
                rogue="x",  # type: ignore[call-arg]
            )
