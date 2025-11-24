"""Simple in-memory session orchestration for the scaffold.

This keeps the deterministic services (STT, diarization, summarization)
stitchable into a product-like flow without persistence. It is intentionally
minimal and side-effect free so real storage/queue integrations can replace it
later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from python_services.diarization.diarization_service import DiarizedSegment
from python_services.summarization.summarizer import Summary


@dataclass
class Session:
    session_id: str
    language: str = "fa"
    segments: List[DiarizedSegment] = field(default_factory=list)

    def append_segments(self, new_segments: List[DiarizedSegment]) -> None:
        self.segments.extend(new_segments)

    def summary(self, summarizer) -> Summary:
        transcript_text = " ".join(segment.text for segment in self.segments)
        return summarizer.summarize(transcript_text)


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create(self, session_id: str, language: str = "fa") -> Session:
        session = Session(session_id=session_id, language=language)
        self._sessions[session_id] = session
        return session

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def append(self, session_id: str, segments: List[DiarizedSegment]) -> Session:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session {session_id}")
        session = self._sessions[session_id]
        session.append_segments(segments)
        return session

    def get(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session {session_id}")
        return self._sessions[session_id]

    def summary(self, session_id: str, summarizer) -> Summary:
        return self.get(session_id).summary(summarizer)

    def clear(self) -> None:
        self._sessions.clear()
