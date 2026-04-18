"""DatasetExporter – persist filtered LearningRecords to versioned JSONL.

Offline training pipelines need a stable, portable file format.  This module
writes a self-describing JSONL file where the **first line is a manifest** and
every subsequent line is one serialised ``LearningRecord``.

File naming convention::

    learning_records_<YYYYMMDD_HHMMSS>_v<schema_version>.jsonl

Example manifest (line 0)::

    {"__manifest__": true, "schema_version": "1.0", "exported_at": "...",
     "record_count": 42, "has_routing_count": 38, "has_outcome_count": 30,
     "has_approval_count": 12}

No heavy dependencies — stdlib only (``json``, ``pathlib``, ``datetime``).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .record import LearningRecord

SCHEMA_VERSION = "1.0"


class ExportManifest:
    """Summary of one exported dataset file.

    Constructed from the manifest line (line 0) of a JSONL file.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self.schema_version: str = data.get("schema_version", "unknown")
        self.exported_at: str = data.get("exported_at", "")
        self.record_count: int = int(data.get("record_count", 0))
        self.has_routing_count: int = int(data.get("has_routing_count", 0))
        self.has_outcome_count: int = int(data.get("has_outcome_count", 0))
        self.has_approval_count: int = int(data.get("has_approval_count", 0))

    def __repr__(self) -> str:
        return (
            f"ExportManifest(schema_version={self.schema_version!r}, "
            f"records={self.record_count}, "
            f"routing={self.has_routing_count}, "
            f"outcome={self.has_outcome_count})"
        )


class DatasetExporter:
    """Write and read versioned JSONL datasets of ``LearningRecord`` objects.

    Parameters
    ----------
    output_dir:
        Directory where JSONL files are written.  Created if it does not exist.
    schema_version:
        Schema version embedded in every manifest.  Override only in tests or
        when intentionally producing a differently-versioned artefact.
    """

    def __init__(
        self,
        output_dir: str | Path,
        *,
        schema_version: str = SCHEMA_VERSION,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.schema_version = schema_version

    def export(
        self,
        records: list[LearningRecord],
        *,
        filename: str | None = None,
    ) -> Path:
        """Write *records* to a new JSONL file and return the path.

        Parameters
        ----------
        records:
            Pre-filtered list of ``LearningRecord`` objects.  The exporter
            does **not** apply quality filtering; that is the caller's
            responsibility.
        filename:
            Override the auto-generated filename.  Useful in tests.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / (filename or self._default_filename())

        manifest = self._build_manifest(records)
        lines: list[str] = [json.dumps(manifest, sort_keys=True)]
        for record in records:
            lines.append(json.dumps(record.model_dump(mode="json"), sort_keys=True))

        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return target

    def load(self, path: str | Path) -> tuple[ExportManifest, list[LearningRecord]]:
        """Read a JSONL file produced by this exporter.

        Returns
        -------
        (manifest, records)
            The manifest from line 0 and the reconstructed ``LearningRecord``
            list from the remaining lines.

        Raises
        ------
        ValueError
            If the file is empty or the first line is not a manifest.
        """
        source = Path(path)
        raw = source.read_text(encoding="utf-8").splitlines()
        if not raw:
            raise ValueError(f"JSONL file is empty: {source}")

        first = json.loads(raw[0])
        if not first.get("__manifest__"):
            raise ValueError(
                f"first line of {source} is not a manifest "
                f"(missing '__manifest__' key)"
            )
        manifest = ExportManifest(first)

        records: list[LearningRecord] = []
        for line in raw[1:]:
            line = line.strip()
            if not line:
                continue
            records.append(LearningRecord.model_validate(json.loads(line)))

        return manifest, records

    def list_exports(self) -> list[Path]:
        """Return all JSONL files in *output_dir*, newest-first."""
        if not self.output_dir.exists():
            return []
        return sorted(
            self.output_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_manifest(self, records: list[LearningRecord]) -> dict[str, Any]:
        return {
            "__manifest__": True,
            "schema_version": self.schema_version,
            "exported_at": _utcnow_iso(),
            "record_count": len(records),
            "has_routing_count": sum(1 for r in records if r.has_routing_decision),
            "has_outcome_count": sum(1 for r in records if r.has_outcome),
            "has_approval_count": sum(1 for r in records if r.has_approval_outcome),
        }

    def _default_filename(self) -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"learning_records_{ts}_v{self.schema_version}.jsonl"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()
