"""Phase 5 – LearningOps L4: Model artefact versioning and rollback.

``ModelRegistry`` tracks every model artefact produced by ``OfflineTrainer``
as a versioned entry.  Exactly one entry is *active* at any time.  Rollback
is a single ``activate(version_id)`` call — it flips the active flag and the
caller reloads the model via ``persistence.load_model()``.

The registry is persisted as a JSON file; no database required.

Typical flow::

    config  = TrainingJobConfig(...)
    result  = OfflineTrainer(config).run()
    registry = ModelRegistry("models/registry.json")
    entry   = registry.register(result, config)

    # Later: rollback to a previous version
    registry.activate(old_version_id)
    model = registry.get_active_model()

No heavy dependencies — stdlib only (``json``, ``hashlib``, ``pathlib``).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..neural_policy import NeuralPolicyModel
from .offline_trainer import OfflineTrainingResult, TrainingJobConfig
from .persistence import load_model
from .trainer import TrainingMetrics


class ModelVersionEntry(BaseModel):
    """Immutable record of one trained model artefact."""

    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(description="Short unique identifier for this entry")
    artifact_path: str = Field(description="Absolute path to the model weights JSON")
    dataset_path: str = Field(description="JSONL dataset used for this training run")
    schema_version: str = Field(description="Feature schema version (from exporter manifest)")
    training_config_hash: str = Field(
        description="SHA-256 hex of hyperparameter-only TrainingJobConfig fields"
    )
    records_accepted: int = Field(ge=0)
    records_rejected: int = Field(ge=0)
    samples_converted: int = Field(ge=0)
    training_metrics: TrainingMetrics
    registered_at: str = Field(description="ISO 8601 registration timestamp")
    is_active: bool = False
    notes: str | None = None


class ModelRegistry:
    """Append-only versioned store of model artefacts with rollback support.

    Parameters
    ----------
    registry_path:
        Path to the JSON file where the registry is persisted.  Created (with
        parent directories) on first ``register()`` call if it does not exist.
    """

    def __init__(self, registry_path: str | Path) -> None:
        self.registry_path = Path(registry_path)
        self._entries: list[ModelVersionEntry] = []
        if self.registry_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def register(
        self,
        result: OfflineTrainingResult,
        config: TrainingJobConfig,
        *,
        notes: str | None = None,
        activate: bool = True,
    ) -> ModelVersionEntry:
        """Add a new entry from the result of one ``OfflineTrainer.run()`` call.

        Parameters
        ----------
        result:
            The ``OfflineTrainingResult`` returned by ``OfflineTrainer.run()``.
        config:
            The ``TrainingJobConfig`` used for that run.  Only hyperparameter
            fields are hashed (paths are excluded).
        activate:
            If ``True`` (default), the new entry becomes the active version and
            all existing entries are deactivated.
        notes:
            Optional free-text annotation (operator comment, experiment label,
            etc.).
        """
        version_id = _short_id()
        entry = ModelVersionEntry(
            version_id=version_id,
            artifact_path=result.artifact_path,
            dataset_path=str(config.dataset_path),
            schema_version=result.manifest_schema_version,
            training_config_hash=_config_hash(config),
            records_accepted=result.records_accepted,
            records_rejected=result.records_rejected,
            samples_converted=result.samples_converted,
            training_metrics=result.training_metrics,
            registered_at=_utcnow_iso(),
            is_active=False,
            notes=notes,
        )
        self._entries.append(entry)
        if activate:
            self._set_active(version_id)
        self._save()
        return self._get_entry(version_id)  # return updated (is_active may have flipped)

    def activate(self, version_id: str) -> ModelVersionEntry:
        """Make *version_id* the active version.

        Raises
        ------
        KeyError
            If no entry with *version_id* exists.
        """
        if not any(e.version_id == version_id for e in self._entries):
            raise KeyError(f"unknown version_id: {version_id!r}")
        self._set_active(version_id)
        self._save()
        return self._get_entry(version_id)

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get_active(self) -> ModelVersionEntry | None:
        """Return the currently active entry, or ``None`` if the registry is empty."""
        for entry in self._entries:
            if entry.is_active:
                return entry
        return None

    def get_active_model(self) -> NeuralPolicyModel | None:
        """Load and return the ``NeuralPolicyModel`` for the active entry.

        Returns ``None`` when the registry has no active entry or the artefact
        file does not exist.
        """
        entry = self.get_active()
        if entry is None:
            return None
        artifact = Path(entry.artifact_path)
        if not artifact.exists():
            return None
        return load_model(artifact)

    def get_version(self, version_id: str) -> ModelVersionEntry | None:
        """Return the entry for *version_id*, or ``None``."""
        for entry in self._entries:
            if entry.version_id == version_id:
                return entry
        return None

    def list_versions(self) -> list[ModelVersionEntry]:
        """Return all entries, newest-first."""
        return list(reversed(self._entries))

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_active(self, version_id: str) -> None:
        updated: list[ModelVersionEntry] = []
        for entry in self._entries:
            if entry.version_id == version_id:
                updated.append(entry.model_copy(update={"is_active": True}))
            else:
                updated.append(
                    entry.model_copy(update={"is_active": False})
                    if entry.is_active
                    else entry
                )
        self._entries = updated

    def _get_entry(self, version_id: str) -> ModelVersionEntry:
        for entry in self._entries:
            if entry.version_id == version_id:
                return entry
        raise KeyError(version_id)

    def _save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload: list[dict[str, Any]] = [
            e.model_dump(mode="json") for e in self._entries
        ]
        self.registry_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _load(self) -> None:
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self._entries = [ModelVersionEntry.model_validate(item) for item in raw]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _short_id() -> str:
    """Return an 8-character hex ID from a fresh UUID4."""
    return uuid4().hex[:8]


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _config_hash(config: TrainingJobConfig) -> str:
    """SHA-256 of the *hyperparameter-only* fields of *config*.

    Paths (dataset_path, output_artifact_path) are excluded so that the same
    hyperparameter configuration run against a different dataset still produces
    the same hash — enabling easy identification of identical training setups.
    """
    hyper: dict[str, Any] = {
        "batch_size": config.batch_size,
        "cost_scale": config.cost_scale,
        "epochs": config.epochs,
        "latency_scale": config.latency_scale,
        "learning_rate": config.learning_rate,
        "min_samples": config.min_samples,
        "require_outcome": config.require_outcome,
        "require_routing_decision": config.require_routing_decision,
    }
    payload = json.dumps(hyper, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
