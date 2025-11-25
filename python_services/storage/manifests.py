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
    title: str | None = None
    agenda: List[str] = field(default_factory=list)


def render_markdown(export: SessionExport) -> str:
    """Return a Markdown representation of the session export."""

    header = export.title or f"Session {export.session_id}"
    lines = [f"# {header}"]
    lines.append(f"- Session ID: `{export.session_id}`")
    lines.append(f"- Created: {export.created_at.isoformat()}")
    lines.append(f"- Language: {export.language}")
    if export.agenda:
        lines.append("- Agenda:")
        for item in export.agenda:
            lines.append(f"  - {item}")

    lines.append("\n## Summary")
    lines.append(f"**Highlight:** {export.summary.highlight}")
    if export.summary.bullet_points:
        lines.append("\n**Bullet Points:**")
        for bullet in export.summary.bullet_points:
            lines.append(f"- {bullet}")

    lines.append("\n## Timeline")
    for segment in export.segments:
        speaker = segment.speaker_label or segment.speaker
        lines.append(f"- **{speaker}**: {segment.text}")

    return "\n".join(lines)


def render_text(export: SessionExport) -> str:
    """Return a plain-text representation of the session export."""

    lines = [f"Session: {export.title or export.session_id}"]
    lines.append(f"Session ID: {export.session_id}")
    lines.append(f"Created: {export.created_at.isoformat()}")
    lines.append(f"Language: {export.language}")
    if export.agenda:
        lines.append("Agenda:")
        for item in export.agenda:
            lines.append(f"- {item}")

    lines.append("\nSummary:")
    lines.append(export.summary.highlight)
    for bullet in export.summary.bullet_points:
        lines.append(f"- {bullet}")

    lines.append("\nTimeline:")
    for segment in export.segments:
        speaker = segment.speaker_label or segment.speaker
        lines.append(f"{speaker}: {segment.text}")

    return "\n".join(lines)
