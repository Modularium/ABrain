"""Simple approval request store with optional JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path

from .models import ApprovalDecision, ApprovalRequest, ApprovalStatus


class ApprovalStore:
    """Small in-memory approval store with optional persistence."""

    def __init__(
        self,
        initial: dict[str, ApprovalRequest] | None = None,
        *,
        path: str | Path | None = None,
    ) -> None:
        self._requests: dict[str, ApprovalRequest] = dict(initial or {})
        self.path = Path(path) if path else None

    def create_request(self, request: ApprovalRequest) -> ApprovalRequest:
        if request.approval_id in self._requests:
            raise ValueError(f"duplicate approval_id: {request.approval_id}")
        self._requests[request.approval_id] = request
        self._auto_save()
        return request

    def get_request(self, approval_id: str) -> ApprovalRequest | None:
        return self._requests.get(approval_id)

    def list_pending(self) -> list[ApprovalRequest]:
        return [
            request
            for request in sorted(self._requests.values(), key=lambda item: item.requested_at)
            if request.status == ApprovalStatus.PENDING
        ]

    def record_decision(
        self,
        approval_id: str,
        decision: ApprovalDecision,
    ) -> ApprovalRequest:
        request = self._requests.get(approval_id)
        if request is None:
            raise KeyError(f"unknown approval_id: {approval_id}")
        updated = request.model_copy(
            update={
                "status": decision.decision,
                "metadata": {
                    **request.metadata,
                    "decision": decision.model_dump(mode="json"),
                },
            }
        )
        self._requests[approval_id] = updated
        self._auto_save()
        return updated

    def save_json(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("save_json requires a target path")
        payload = {
            approval_id: request.model_dump(mode="json")
            for approval_id, request in sorted(self._requests.items())
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load_json(cls, path: str | Path) -> "ApprovalStore":
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls(
            {
                approval_id: ApprovalRequest.model_validate(request)
                for approval_id, request in payload.items()
            },
            path=source,
        )

    def _auto_save(self) -> None:
        if self.path is not None:
            self.save_json(self.path)
