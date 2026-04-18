"""Data-quality rules for LearningRecord filtering.

Defines ``DataQualityFilter`` which validates and filters a list of
``LearningRecord`` instances before they are passed to offline training jobs.

Rules are intentionally conservative: a record is *usable* by default when it
has at least a routing decision.  Stricter criteria (e.g. requiring an
outcome) are opt-in per training job.
"""

from __future__ import annotations

from dataclasses import dataclass

from .record import LearningRecord


@dataclass(frozen=True)
class QualityViolation:
    """One detected quality issue on a single record."""

    field: str
    reason: str


class DataQualityFilter:
    """Filter and validate LearningRecords against configurable quality rules.

    Parameters
    ----------
    require_routing_decision:
        Reject records without a routing decision (default: True).
    require_outcome:
        Reject records where ``success`` is unknown (default: False).
    require_approval_outcome:
        Reject records with an unresolved approval (default: False).
    min_quality_score:
        Reject records whose ``quality_score()`` is below this threshold
        (default: 0.0 — no minimum).
    """

    def __init__(
        self,
        *,
        require_routing_decision: bool = True,
        require_outcome: bool = False,
        require_approval_outcome: bool = False,
        min_quality_score: float = 0.0,
    ) -> None:
        self.require_routing_decision = require_routing_decision
        self.require_outcome = require_outcome
        self.require_approval_outcome = require_approval_outcome
        self.min_quality_score = min_quality_score

    def validate(self, record: LearningRecord) -> list[QualityViolation]:
        """Return all quality violations for *record* (empty list = clean)."""
        issues: list[QualityViolation] = []

        if self.require_routing_decision and not record.has_routing_decision:
            issues.append(
                QualityViolation(
                    field="has_routing_decision",
                    reason="no routing decision recorded for this trace",
                )
            )

        if self.require_outcome and not record.has_outcome:
            issues.append(
                QualityViolation(
                    field="has_outcome",
                    reason="execution outcome (success) is unknown",
                )
            )

        if self.require_approval_outcome and not record.has_approval_outcome:
            issues.append(
                QualityViolation(
                    field="has_approval_outcome",
                    reason="approval outcome is unresolved or missing",
                )
            )

        if record.quality_score() < self.min_quality_score:
            issues.append(
                QualityViolation(
                    field="quality_score",
                    reason=(
                        f"quality score {record.quality_score():.2f} "
                        f"< required {self.min_quality_score:.2f}"
                    ),
                )
            )

        return issues

    def filter(self, records: list[LearningRecord]) -> list[LearningRecord]:
        """Return only records that pass all quality rules."""
        return [r for r in records if not self.validate(r)]

    def filter_with_report(
        self,
        records: list[LearningRecord],
    ) -> tuple[list[LearningRecord], list[tuple[LearningRecord, list[QualityViolation]]]]:
        """Return (accepted, rejected) where rejected carries its violations."""
        accepted: list[LearningRecord] = []
        rejected: list[tuple[LearningRecord, list[QualityViolation]]] = []
        for record in records:
            violations = self.validate(record)
            if violations:
                rejected.append((record, violations))
            else:
                accepted.append(record)
        return accepted, rejected
