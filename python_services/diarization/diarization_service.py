"""Speaker diarization scaffold.

Replaces heavy ML diarization with a deterministic placeholder keyed by text
content. Upstream STT should provide timestamps and embeddings in production.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List

from python_services.stt.whisper_service import Transcript


def _hash_speaker(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"speaker-{digest[:8]}"


@dataclass
class DiarizedSegment:
    speaker: str
    text: str


class DiarizationService:
    def diarize(self, transcript: Transcript) -> List[DiarizedSegment]:
        diarized: List[DiarizedSegment] = []
        for segment in transcript.segments:
            speaker = _hash_speaker(segment.text) if segment.text else "unknown"
            diarized.append(DiarizedSegment(speaker=speaker, text=segment.text))
        return diarized
