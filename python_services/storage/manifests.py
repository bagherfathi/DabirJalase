"""Manifest helpers for persisted transcripts and syntheses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from python_services.diarization.diarization_service import DiarizedSegment
from python_services.summarization.summarizer import Summary


@dataclass
class SegmentRecord:
    speaker: str
    text: str
    speaker_label: Optional[str] = None


@dataclass
class TranscriptManifest:
    transcript_id: str
    created_at: datetime
    language: str
    segments: List[DiarizedSegment] = field(default_factory=list)

    @classmethod
    def from_diarized(cls, transcript_id: str, language: str, segments: List[DiarizedSegment]) -> "TranscriptManifest":
        return cls(
            transcript_id=transcript_id,
            created_at=datetime.now(timezone.utc),
            language=language,
            segments=segments,
        )


@dataclass
class SessionExport:
    """Serializable view of a full meeting session."""

    session_id: str
    created_at: datetime
    language: str
    segments: List[SegmentRecord]
    summary: Summary
