"""ApprovalStore state-transition tests.

Covers all legal transitions from PENDING to each terminal state, guard conditions
(no PENDING decision, duplicate IDs, unknown IDs), and metadata/rating/comment
preservation.  All tests are unit-level with no file I/O unless explicitly testing
persistence.
"""

from __future__ import annotations

import pytest

from core.approval import ApprovalDecision, ApprovalRequest, ApprovalStatus, ApprovalStore
from core.decision import CapabilityRisk

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(**kwargs) -> ApprovalRequest:
    defaults = {
        "plan_id": "plan-1",
        "step_id": "step-1",
        "task_summary": "Do something",
        "reason": "manual_review",
        "risk": CapabilityRisk.MEDIUM,
        "proposed_action_summary": "Proposed action",
    }
    defaults.update(kwargs)
    return ApprovalRequest.model_validate(defaults)


def _make_decision(approval_id: str, decision: ApprovalStatus, **kwargs) -> ApprovalDecision:
    kwargs.setdefault("decided_by", "reviewer")
    return ApprovalDecision(
        approval_id=approval_id,
        decision=decision,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. All four terminal transitions from PENDING
# ---------------------------------------------------------------------------


def test_pending_to_approved():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    updated = store.record_decision(
        req.approval_id,
        _make_decision(req.approval_id, ApprovalStatus.APPROVED),
    )

    assert updated.status == ApprovalStatus.APPROVED
    assert store.get_request(req.approval_id).status == ApprovalStatus.APPROVED


def test_pending_to_rejected():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    updated = store.record_decision(
        req.approval_id,
        _make_decision(req.approval_id, ApprovalStatus.REJECTED, comment="Not safe"),
    )

    assert updated.status == ApprovalStatus.REJECTED
    assert store.get_request(req.approval_id).status == ApprovalStatus.REJECTED


def test_pending_to_cancelled():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    updated = store.record_decision(
        req.approval_id,
        _make_decision(req.approval_id, ApprovalStatus.CANCELLED),
    )

    assert updated.status == ApprovalStatus.CANCELLED


def test_pending_to_expired():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    updated = store.record_decision(
        req.approval_id,
        _make_decision(req.approval_id, ApprovalStatus.EXPIRED),
    )

    assert updated.status == ApprovalStatus.EXPIRED


# ---------------------------------------------------------------------------
# 2. Initial state is always PENDING
# ---------------------------------------------------------------------------


def test_new_request_starts_as_pending():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    assert req.status == ApprovalStatus.PENDING


def test_created_request_appears_in_list_pending():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    pending = store.list_pending()

    assert len(pending) == 1
    assert pending[0].approval_id == req.approval_id


# ---------------------------------------------------------------------------
# 3. Terminal states removed from list_pending
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "terminal",
    [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED, ApprovalStatus.EXPIRED],
)
def test_terminal_state_not_listed_as_pending(terminal):
    store = ApprovalStore()
    req = store.create_request(_make_request())
    store.record_decision(req.approval_id, _make_decision(req.approval_id, terminal))

    assert store.list_pending() == []


def test_list_pending_returns_only_pending_among_mixed():
    store = ApprovalStore()
    req_a = store.create_request(_make_request(step_id="step-a"))
    req_b = store.create_request(_make_request(step_id="step-b"))
    req_c = store.create_request(_make_request(step_id="step-c"))

    store.record_decision(req_b.approval_id, _make_decision(req_b.approval_id, ApprovalStatus.APPROVED))
    store.record_decision(req_c.approval_id, _make_decision(req_c.approval_id, ApprovalStatus.REJECTED))

    pending = store.list_pending()
    pending_ids = {r.approval_id for r in pending}

    assert pending_ids == {req_a.approval_id}


# ---------------------------------------------------------------------------
# 4. list_pending ordering by requested_at
# ---------------------------------------------------------------------------


def test_list_pending_sorted_by_requested_at():
    from datetime import UTC, datetime, timedelta

    t0 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=1)
    t2 = t0 + timedelta(minutes=2)

    store = ApprovalStore()
    req_latest = store.create_request(ApprovalRequest(
        plan_id="p1", step_id="latest",
        task_summary="latest", reason="r", risk=CapabilityRisk.LOW,
        proposed_action_summary="a", requested_at=t2,
    ))
    req_earliest = store.create_request(ApprovalRequest(
        plan_id="p1", step_id="earliest",
        task_summary="earliest", reason="r", risk=CapabilityRisk.LOW,
        proposed_action_summary="a", requested_at=t0,
    ))
    req_middle = store.create_request(ApprovalRequest(
        plan_id="p1", step_id="middle",
        task_summary="middle", reason="r", risk=CapabilityRisk.LOW,
        proposed_action_summary="a", requested_at=t1,
    ))

    pending = store.list_pending()

    assert [r.approval_id for r in pending] == [
        req_earliest.approval_id,
        req_middle.approval_id,
        req_latest.approval_id,
    ]


# ---------------------------------------------------------------------------
# 5. Guard conditions — duplicate ID, unknown ID
# ---------------------------------------------------------------------------


def test_duplicate_approval_id_raises_value_error():
    store = ApprovalStore()
    req = _make_request()
    store.create_request(req)

    with pytest.raises(ValueError, match="duplicate approval_id"):
        store.create_request(req)


def test_record_decision_unknown_id_raises_key_error():
    store = ApprovalStore()

    with pytest.raises(KeyError):
        store.record_decision(
            "nonexistent-id",
            _make_decision("nonexistent-id", ApprovalStatus.APPROVED),
        )


def test_get_request_returns_none_for_unknown_id():
    store = ApprovalStore()
    assert store.get_request("not-here") is None


# ---------------------------------------------------------------------------
# 6. ApprovalDecision validation — PENDING not allowed as a decision
# ---------------------------------------------------------------------------


def test_approval_decision_rejects_pending_status():
    with pytest.raises(Exception, match="terminal"):
        ApprovalDecision(
            approval_id="some-id",
            decision=ApprovalStatus.PENDING,
            decided_by="reviewer",
        )


def test_approval_decision_accepts_all_terminal_statuses():
    for status in [
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.CANCELLED,
        ApprovalStatus.EXPIRED,
    ]:
        decision = ApprovalDecision(
            approval_id="some-id",
            decision=status,
            decided_by="reviewer",
        )
        assert decision.decision == status


# ---------------------------------------------------------------------------
# 7. Metadata, comment, and rating preservation
# ---------------------------------------------------------------------------


def test_comment_preserved_in_updated_request_metadata():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    updated = store.record_decision(
        req.approval_id,
        _make_decision(
            req.approval_id,
            ApprovalStatus.REJECTED,
            comment="This action is too risky",
        ),
    )

    decision_meta = updated.metadata.get("decision", {})
    assert decision_meta.get("comment") == "This action is too risky"


def test_rating_preserved_in_updated_request_metadata():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    updated = store.record_decision(
        req.approval_id,
        _make_decision(
            req.approval_id,
            ApprovalStatus.APPROVED,
            rating=0.9,
        ),
    )

    decision_meta = updated.metadata.get("decision", {})
    assert decision_meta.get("rating") == pytest.approx(0.9)


def test_existing_request_metadata_preserved_after_decision():
    store = ApprovalStore()
    req = _make_request()
    req = req.model_copy(update={"metadata": {"source": "integration-test", "priority": 3}})
    store.create_request(req)

    updated = store.record_decision(
        req.approval_id,
        _make_decision(req.approval_id, ApprovalStatus.APPROVED),
    )

    assert updated.metadata.get("source") == "integration-test"
    assert updated.metadata.get("priority") == 3


def test_decided_by_recorded_in_decision_metadata():
    store = ApprovalStore()
    req = store.create_request(_make_request())

    updated = store.record_decision(
        req.approval_id,
        _make_decision(req.approval_id, ApprovalStatus.APPROVED, decided_by="ops-team"),
    )

    decision_meta = updated.metadata.get("decision", {})
    assert decision_meta.get("decided_by") == "ops-team"


# ---------------------------------------------------------------------------
# 8. Second decision overwrites first (no guard — store allows re-decision)
# ---------------------------------------------------------------------------


def test_second_decision_overwrites_first():
    """record_decision does not guard against a second decision — last write wins."""
    store = ApprovalStore()
    req = store.create_request(_make_request())

    store.record_decision(req.approval_id, _make_decision(req.approval_id, ApprovalStatus.APPROVED))
    updated = store.record_decision(
        req.approval_id, _make_decision(req.approval_id, ApprovalStatus.REJECTED, comment="Changed mind")
    )

    assert updated.status == ApprovalStatus.REJECTED


# ---------------------------------------------------------------------------
# 9. Persistence round-trip
# ---------------------------------------------------------------------------


def test_store_persists_terminal_decision_to_json(tmp_path):
    path = tmp_path / "approvals.json"
    store = ApprovalStore(path=path)
    req = store.create_request(_make_request())
    store.record_decision(
        req.approval_id,
        _make_decision(req.approval_id, ApprovalStatus.APPROVED, comment="LGTM"),
    )

    loaded = ApprovalStore.load_json(path)
    loaded_req = loaded.get_request(req.approval_id)

    assert loaded_req is not None
    assert loaded_req.status == ApprovalStatus.APPROVED
    assert loaded_req.metadata["decision"]["comment"] == "LGTM"


def test_store_persists_multiple_requests(tmp_path):
    path = tmp_path / "approvals.json"
    store = ApprovalStore(path=path)
    req_a = store.create_request(_make_request(step_id="a"))
    req_b = store.create_request(_make_request(step_id="b"))
    store.record_decision(req_a.approval_id, _make_decision(req_a.approval_id, ApprovalStatus.APPROVED))

    loaded = ApprovalStore.load_json(path)

    assert loaded.get_request(req_a.approval_id).status == ApprovalStatus.APPROVED
    assert loaded.get_request(req_b.approval_id).status == ApprovalStatus.PENDING


def test_store_save_json_explicit_path(tmp_path):
    alt_path = tmp_path / "backup.json"
    store = ApprovalStore()  # no auto-save path
    req = store.create_request(_make_request())

    store.save_json(alt_path)

    loaded = ApprovalStore.load_json(alt_path)
    assert loaded.get_request(req.approval_id) is not None
