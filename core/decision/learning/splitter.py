"""Deterministic, reproducible dataset splitter — §6.4 / Phase 5.

Takes a list of ``LearningRecord`` instances produced by
``DatasetBuilder`` and partitions them into train / val / test subsets
using stable hash-bucketing.

Design invariants
-----------------
- **Deterministic.** Given the same ``DatasetSplitConfig`` and the same
  input records, the split is byte-identical across runs, processes,
  and Python versions — the bucket assignment is a pure function of
  ``seed`` and each record's group key, computed with BLAKE2b (stdlib,
  no PYTHONHASHSEED dependency).
- **Growth-stable.** A record's bucket label depends only on its
  group key and the seed — not on dataset size or position. Adding or
  removing records does not reshuffle existing assignments. This is
  the property that makes a split *reproducible* across weeks as the
  underlying trace store grows.
- **Group-safe.** When ``group_by`` is set, all records sharing a
  group key land in the same bucket. Prevents group leakage (e.g. two
  rows from the same trace ending up in train and test).
- **Read-only.** Records are never mutated. The splitter returns
  shallow lists; ordering of records *within* each bucket preserves
  input order so callers can pair with external indices.
- **No new dependencies.** Stdlib ``hashlib`` + pydantic only.

Composes with the Phase 6 governance surfaces:

- PII filtering is the caller's responsibility — run ``PiiDetector``
  before splitting to drop or redact records. The splitter does not
  re-mix PII-bearing records because identical records (same group
  key) always land in the same bucket.
- Per-source attribution is preserved via ``group_by`` (e.g. grouping
  by ``workflow_name`` keeps a workflow's records together).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .record import LearningRecord

GroupBy = Literal["trace_id", "task_type", "workflow_name"]

_RATIO_TOLERANCE = 1e-9


class DatasetSplitConfig(BaseModel):
    """Frozen split configuration.

    ``train_ratio + val_ratio + test_ratio`` must equal 1.0 within
    ``1e-9`` floating-point tolerance. ``val_ratio`` may be zero
    (train/test-only splits). ``test_ratio`` may be zero (train/val-only
    splits) but at least one of val/test must be non-zero — otherwise
    the config collapses to an identity operation.
    """

    model_config = ConfigDict(extra="forbid")

    train_ratio: float = Field(gt=0.0, lt=1.0)
    val_ratio: float = Field(ge=0.0, lt=1.0)
    test_ratio: float = Field(ge=0.0, lt=1.0)
    seed: int = Field(ge=0, le=2**31 - 1)
    group_by: GroupBy = Field(
        default="trace_id",
        description=(
            "Group key that must not leak across buckets. 'trace_id' treats "
            "each record as its own group (no grouping). 'task_type' / "
            "'workflow_name' group records by the respective LearningRecord "
            "field; records where the field is None fall back to trace_id."
        ),
    )

    @model_validator(mode="after")
    def _ratios_sum_to_one(self) -> "DatasetSplitConfig":
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > _RATIO_TOLERANCE:
            raise ValueError(
                f"train+val+test must sum to 1.0 (got {total!r})"
            )
        if self.val_ratio == 0.0 and self.test_ratio == 0.0:
            raise ValueError(
                "at least one of val_ratio / test_ratio must be > 0"
            )
        return self


class DatasetSplit(BaseModel):
    """Train / val / test subsets produced by :class:`DatasetSplitter`."""

    model_config = ConfigDict(extra="forbid")

    train: list[LearningRecord] = Field(default_factory=list)
    val: list[LearningRecord] = Field(default_factory=list)
    test: list[LearningRecord] = Field(default_factory=list)


class SplitManifest(BaseModel):
    """Reproducibility manifest for a split.

    Persist this alongside exported splits to recover them exactly:
    the same ``config`` applied to the same set of ``trace_id``s will
    reconstruct the same split.

    ``dataset_fingerprint`` is a hash over the sorted ``trace_id`` set,
    so manifests from different input orderings but identical inputs
    compare equal. Checking fingerprint equality between two manifests
    is the canonical way to ask "are these the same dataset?".
    """

    model_config = ConfigDict(extra="forbid")

    config: DatasetSplitConfig
    generated_at: datetime
    total_records: int = Field(ge=0)
    total_groups: int = Field(ge=0)
    train_size: int = Field(ge=0)
    val_size: int = Field(ge=0)
    test_size: int = Field(ge=0)
    ungrouped_records: int = Field(
        ge=0,
        description=(
            "Count of records whose group_by field was None and thus fell "
            "back to trace_id. Non-zero signals that the caller may want "
            "to revisit the group_by choice or clean the upstream data."
        ),
    )
    dataset_fingerprint: str = Field(min_length=1, max_length=128)


class DatasetSplitter:
    """Partition ``LearningRecord``s into train / val / test deterministically."""

    def __init__(self, *, config: DatasetSplitConfig) -> None:
        self.config = config

    def split(
        self,
        records: list[LearningRecord],
    ) -> tuple[DatasetSplit, SplitManifest]:
        """Return ``(split, manifest)``.

        Raises
        ------
        ValueError
            If two records share the same ``trace_id`` (the fingerprint
            relies on trace_id uniqueness for dataset identity).
        """
        trace_ids: list[str] = [r.trace_id for r in records]
        if len(set(trace_ids)) != len(trace_ids):
            raise ValueError(
                "records must have unique trace_ids — duplicate detected"
            )

        train: list[LearningRecord] = []
        val: list[LearningRecord] = []
        test: list[LearningRecord] = []

        ungrouped = 0
        groups_seen: set[str] = set()
        train_cutoff = self.config.train_ratio
        val_cutoff = self.config.train_ratio + self.config.val_ratio

        for record in records:
            group_key, is_fallback = self._group_key(record)
            if is_fallback:
                ungrouped += 1
            groups_seen.add(group_key)
            bucket = self._bucket(group_key, train_cutoff, val_cutoff)
            if bucket == "train":
                train.append(record)
            elif bucket == "val":
                val.append(record)
            else:
                test.append(record)

        manifest = SplitManifest(
            config=self.config,
            generated_at=datetime.now(UTC),
            total_records=len(records),
            total_groups=len(groups_seen),
            train_size=len(train),
            val_size=len(val),
            test_size=len(test),
            ungrouped_records=ungrouped,
            dataset_fingerprint=_fingerprint(trace_ids),
        )
        return DatasetSplit(train=train, val=val, test=test), manifest

    def _group_key(self, record: LearningRecord) -> tuple[str, bool]:
        if self.config.group_by == "trace_id":
            return record.trace_id, False
        if self.config.group_by == "task_type":
            value = record.task_type
        else:
            value = record.workflow_name
        if value is None or value == "":
            return record.trace_id, True
        return value, False

    def _bucket(
        self,
        group_key: str,
        train_cutoff: float,
        val_cutoff: float,
    ) -> Literal["train", "val", "test"]:
        h = _bucket_hash(self.config.seed, group_key)
        if h < train_cutoff:
            return "train"
        if h < val_cutoff:
            return "val"
        return "test"


def _bucket_hash(seed: int, group_key: str) -> float:
    """Stable float in [0, 1) derived from ``seed`` and ``group_key``.

    BLAKE2b is used instead of the builtin ``hash()`` because the latter
    is randomised per-process when ``PYTHONHASHSEED`` is unset — which
    would make splits non-reproducible across runs.
    """
    digest = hashlib.blake2b(
        f"{seed}:{group_key}".encode("utf-8"),
        digest_size=8,
    ).digest()
    value = int.from_bytes(digest, "big")
    return value / float(1 << 64)


def _fingerprint(trace_ids: list[str]) -> str:
    ordered = sorted(trace_ids)
    hasher = hashlib.blake2b(digest_size=16)
    for trace_id in ordered:
        hasher.update(trace_id.encode("utf-8"))
        hasher.update(b"\x00")
    return hasher.hexdigest()


__all__ = [
    "DatasetSplit",
    "DatasetSplitConfig",
    "DatasetSplitter",
    "GroupBy",
    "SplitManifest",
]
