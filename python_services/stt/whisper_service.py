"""Minimal Whisper-style transcription stub.

The real implementation should call out to Whisper/DeepSpeech and return rich
segment metadata. This stub keeps tests deterministic and demonstrates the
expected shape for downstream components.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class TranscriptSegment:
    speaker: str
    text: str
    start: float = 0.0
    end: float = 0.0


@dataclass
class Transcript:
    language: str
    segments: List[TranscriptSegment] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(segment.text for segment in self.segments)


class WhisperService:
    def transcribe(self, content: str, language: str = "fa") -> Transcript:
        normalized = content.strip()
        segments = [TranscriptSegment(speaker="unknown", text=normalized)] if normalized else []
        return Transcript(language=language, segments=segments)
