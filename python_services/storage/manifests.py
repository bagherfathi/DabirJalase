"""Manifest helpers for persisted transcripts and syntheses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from python_services.diarization.diarization_service import DiarizedSegment


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
