"""Phase 5 / §6.4 — deterministic DatasetSplitter tests."""

from __future__ import annotations

import random

import pytest

from core.decision.learning import (
    DatasetSplit,
    DatasetSplitConfig,
    DatasetSplitter,
    LearningRecord,
    SplitManifest,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    trace_id: str,
    *,
    task_type: str | None = None,
    workflow_name: str = "wf",
) -> LearningRecord:
    return LearningRecord(
        trace_id=trace_id,
        workflow_name=workflow_name,
        task_type=task_type,
    )


def _records(n: int, *, prefix: str = "t", **kwargs) -> list[LearningRecord]:
    return [_record(f"{prefix}-{i:04d}", **kwargs) for i in range(n)]


def _config(**kwargs) -> DatasetSplitConfig:
    defaults = dict(
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
    )
    defaults.update(kwargs)
    return DatasetSplitConfig(**defaults)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


class TestConfig:
    def test_ratios_must_sum_to_one(self):
        with pytest.raises(ValueError):
            DatasetSplitConfig(
                train_ratio=0.6, val_ratio=0.1, test_ratio=0.1, seed=1
            )

    def test_all_train_is_rejected(self):
        # train=1.0 would collapse to identity; val=test=0.0 is rejected too.
        with pytest.raises(ValueError):
            DatasetSplitConfig(
                train_ratio=1.0, val_ratio=0.0, test_ratio=0.0, seed=1
            )

    def test_train_val_only_split_allowed(self):
        cfg = DatasetSplitConfig(
            train_ratio=0.8, val_ratio=0.2, test_ratio=0.0, seed=1
        )
        assert cfg.test_ratio == 0.0

    def test_train_test_only_split_allowed(self):
        cfg = DatasetSplitConfig(
            train_ratio=0.8, val_ratio=0.0, test_ratio=0.2, seed=1
        )
        assert cfg.val_ratio == 0.0

    def test_config_extra_forbid(self):
        with pytest.raises(ValueError):
            DatasetSplitConfig(
                train_ratio=0.7,
                val_ratio=0.15,
                test_ratio=0.15,
                seed=1,
                rogue="x",  # type: ignore[call-arg]
            )

    def test_seed_must_be_non_negative(self):
        with pytest.raises(ValueError):
            DatasetSplitConfig(
                train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=-1
            )


# ---------------------------------------------------------------------------
# Determinism — identical config + identical input → identical output
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_yields_identical_split(self):
        records = _records(500)
        s1, m1 = DatasetSplitter(config=_config(seed=17)).split(records)
        s2, m2 = DatasetSplitter(config=_config(seed=17)).split(records)
        assert [r.trace_id for r in s1.train] == [r.trace_id for r in s2.train]
        assert [r.trace_id for r in s1.val] == [r.trace_id for r in s2.val]
        assert [r.trace_id for r in s1.test] == [r.trace_id for r in s2.test]
        assert m1.dataset_fingerprint == m2.dataset_fingerprint

    def test_different_seed_yields_different_split(self):
        records = _records(500)
        s1, _ = DatasetSplitter(config=_config(seed=1)).split(records)
        s2, _ = DatasetSplitter(config=_config(seed=2)).split(records)
        assert [r.trace_id for r in s1.train] != [r.trace_id for r in s2.train]

    def test_input_order_does_not_affect_bucket_membership(self):
        records = _records(200)
        shuffled = list(records)
        random.Random(0).shuffle(shuffled)

        s_ordered, _ = DatasetSplitter(config=_config(seed=5)).split(records)
        s_shuffled, _ = DatasetSplitter(config=_config(seed=5)).split(shuffled)

        # Same set membership per bucket (order within a bucket reflects
        # input order; bucket assignment does not depend on position).
        assert {r.trace_id for r in s_ordered.train} == {
            r.trace_id for r in s_shuffled.train
        }
        assert {r.trace_id for r in s_ordered.val} == {
            r.trace_id for r in s_shuffled.val
        }
        assert {r.trace_id for r in s_ordered.test} == {
            r.trace_id for r in s_shuffled.test
        }


# ---------------------------------------------------------------------------
# Growth stability — adding records never reshuffles existing ones
# ---------------------------------------------------------------------------


class TestGrowthStability:
    def test_new_records_do_not_reassign_old_ones(self):
        base = _records(300, prefix="base")
        s_before, _ = DatasetSplitter(config=_config(seed=7)).split(base)
        before_labels = _assignment_map(s_before)

        grown = base + _records(100, prefix="new")
        s_after, _ = DatasetSplitter(config=_config(seed=7)).split(grown)
        after_labels = _assignment_map(s_after)

        for trace_id, bucket in before_labels.items():
            assert after_labels[trace_id] == bucket

    def test_removed_records_do_not_reassign_survivors(self):
        full = _records(300)
        s_full, _ = DatasetSplitter(config=_config(seed=7)).split(full)
        full_labels = _assignment_map(s_full)

        # Drop half at random — survivors keep their bucket.
        survivors = full[::2]
        s_partial, _ = DatasetSplitter(config=_config(seed=7)).split(survivors)
        partial_labels = _assignment_map(s_partial)

        for trace_id, bucket in partial_labels.items():
            assert full_labels[trace_id] == bucket


def _assignment_map(split: DatasetSplit) -> dict[str, str]:
    out: dict[str, str] = {}
    for record in split.train:
        out[record.trace_id] = "train"
    for record in split.val:
        out[record.trace_id] = "val"
    for record in split.test:
        out[record.trace_id] = "test"
    return out


# ---------------------------------------------------------------------------
# Grouping — no key leakage across buckets
# ---------------------------------------------------------------------------


class TestGrouping:
    def test_grouping_by_workflow_keeps_workflow_in_single_bucket(self):
        records: list[LearningRecord] = []
        for workflow_index in range(20):
            for trace_index in range(5):
                records.append(
                    _record(
                        f"w{workflow_index}-t{trace_index}",
                        workflow_name=f"wf-{workflow_index}",
                    )
                )
        splitter = DatasetSplitter(
            config=_config(seed=99, group_by="workflow_name")
        )
        split, _ = splitter.split(records)
        assignments = _assignment_map(split)

        # Every workflow's records share a bucket.
        workflow_buckets: dict[str, str] = {}
        for record in records:
            bucket = assignments[record.trace_id]
            if record.workflow_name in workflow_buckets:
                assert workflow_buckets[record.workflow_name] == bucket
            else:
                workflow_buckets[record.workflow_name] = bucket

    def test_grouping_by_task_type_falls_back_to_trace_id_for_none(self):
        records = [
            _record("a", task_type="refactor"),
            _record("b", task_type="refactor"),
            _record("c", task_type=None),
            _record("d", task_type=None),
        ]
        splitter = DatasetSplitter(
            config=_config(seed=3, group_by="task_type")
        )
        _, manifest = splitter.split(records)
        assert manifest.ungrouped_records == 2

    def test_default_group_by_is_trace_id(self):
        cfg = DatasetSplitConfig(
            train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=1
        )
        assert cfg.group_by == "trace_id"


# ---------------------------------------------------------------------------
# Ratio approximation at scale
# ---------------------------------------------------------------------------


class TestRatioApproximation:
    def test_bucket_sizes_approximate_ratios_at_scale(self):
        records = _records(10_000)
        split, manifest = DatasetSplitter(config=_config(seed=1)).split(records)
        n = manifest.total_records
        assert abs(len(split.train) / n - 0.70) < 0.01
        assert abs(len(split.val) / n - 0.15) < 0.01
        assert abs(len(split.test) / n - 0.15) < 0.01


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


class TestManifest:
    def test_manifest_counts_match_split(self):
        records = _records(137)
        split, manifest = DatasetSplitter(config=_config(seed=1)).split(records)
        assert isinstance(manifest, SplitManifest)
        assert manifest.total_records == 137
        assert manifest.train_size == len(split.train)
        assert manifest.val_size == len(split.val)
        assert manifest.test_size == len(split.test)
        assert (
            manifest.train_size + manifest.val_size + manifest.test_size
            == manifest.total_records
        )

    def test_fingerprint_is_order_independent(self):
        records = _records(50)
        shuffled = list(records)
        random.Random(2).shuffle(shuffled)
        _, m1 = DatasetSplitter(config=_config(seed=1)).split(records)
        _, m2 = DatasetSplitter(config=_config(seed=1)).split(shuffled)
        assert m1.dataset_fingerprint == m2.dataset_fingerprint

    def test_fingerprint_changes_when_dataset_changes(self):
        _, m_small = DatasetSplitter(config=_config(seed=1)).split(_records(50))
        _, m_big = DatasetSplitter(config=_config(seed=1)).split(_records(51))
        assert m_small.dataset_fingerprint != m_big.dataset_fingerprint

    def test_group_count_reflects_grouping(self):
        records = [
            _record("a", workflow_name="x"),
            _record("b", workflow_name="x"),
            _record("c", workflow_name="y"),
        ]
        _, m = DatasetSplitter(
            config=_config(seed=1, group_by="workflow_name")
        ).split(records)
        assert m.total_groups == 2


# ---------------------------------------------------------------------------
# Input validation / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_input_yields_empty_split(self):
        split, manifest = DatasetSplitter(config=_config(seed=1)).split([])
        assert split.train == []
        assert split.val == []
        assert split.test == []
        assert manifest.total_records == 0
        assert manifest.total_groups == 0

    def test_duplicate_trace_ids_are_rejected(self):
        records = [_record("same"), _record("same")]
        with pytest.raises(ValueError):
            DatasetSplitter(config=_config(seed=1)).split(records)

    def test_records_are_not_mutated(self):
        records = _records(10)
        frozen = [r.model_dump() for r in records]
        DatasetSplitter(config=_config(seed=1)).split(records)
        assert [r.model_dump() for r in records] == frozen


# ---------------------------------------------------------------------------
# Schema hardening
# ---------------------------------------------------------------------------


class TestSchemaHardening:
    def test_split_extra_forbid(self):
        with pytest.raises(ValueError):
            DatasetSplit(rogue="x")  # type: ignore[call-arg]

    def test_manifest_extra_forbid(self):
        with pytest.raises(ValueError):
            SplitManifest(
                config=_config(seed=1),
                generated_at="2026-04-19T00:00:00+00:00",  # type: ignore[arg-type]
                total_records=0,
                total_groups=0,
                train_size=0,
                val_size=0,
                test_size=0,
                ungrouped_records=0,
                dataset_fingerprint="x",
                rogue="x",  # type: ignore[call-arg]
            )
