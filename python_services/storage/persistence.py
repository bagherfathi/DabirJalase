"""File-backed storage helpers for session exports.

The helpers intentionally keep the serialization deterministic so the scaffold
can be exercised offline while still showing a product-shaped persistence
surface for manifests.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from python_services.storage.manifests import SegmentRecord, SessionExport
from python_services.summarization.summarizer import Summary


def _export_dir(base_dir: str) -> Path:
    return Path(base_dir) / "exports"


def list_exports(base_dir: str) -> List[str]:
    """Return sorted session_ids that have been exported to disk."""

    export_dir = _export_dir(base_dir)
    if not export_dir.exists():
        return []
    return sorted(path.stem for path in export_dir.glob("*.json"))


def save_export(export: SessionExport, base_dir: str) -> Path:
    """Persist a session export manifest to disk and return the file path."""

    export_dir = _export_dir(base_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"{export.session_id}.json"

    payload = {
        "session_id": export.session_id,
        "created_at": export.created_at.isoformat(),
        "language": export.language,
        "segments": [
            {
                "speaker": segment.speaker,
                "text": segment.text,
                "speaker_label": segment.speaker_label,
            }
            for segment in export.segments
        ],
        "summary": {
            "highlight": export.summary.highlight,
            "bullet_points": export.summary.bullet_points,
        },
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def load_export(session_id: str, base_dir: str) -> SessionExport:
    """Load a previously saved session export manifest."""

    export_dir = _export_dir(base_dir)
    path = export_dir / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No export stored for session {session_id}")

    payload = json.loads(path.read_text())
    return SessionExport(
        session_id=payload["session_id"],
        created_at=datetime.fromisoformat(payload["created_at"]),
        language=payload["language"],
        segments=[
            SegmentRecord(
                speaker=segment["speaker"],
                text=segment["text"],
                speaker_label=segment.get("speaker_label"),
            )
            for segment in payload.get("segments", [])
        ],
        summary=Summary(
            highlight=payload["summary"]["highlight"],
            bullet_points=payload["summary"]["bullet_points"],
        ),
    )

