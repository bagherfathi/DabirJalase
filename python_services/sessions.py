"""Simple in-memory session orchestration for the scaffold.

This keeps the deterministic services (STT, diarization, summarization)
stitchable into a product-like flow without persistence. It is intentionally
minimal and side-effect free so real storage/queue integrations can replace it
later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from python_services.diarization.diarization_service import DiarizedSegment
from python_services.storage.manifests import SegmentRecord, SessionExport
from python_services.summarization.summarizer import Summary
from python_services.vad.simple_vad import SpeechSpan, detect_speech


@dataclass
class Session:
    session_id: str
    language: str = "fa"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    title: str | None = None
    agenda: List[str] = field(default_factory=list)
    segments: List[DiarizedSegment] = field(default_factory=list)
    speaker_labels: Dict[str, str] = field(default_factory=dict)
    audio_buffer: List[float] = field(default_factory=list)

    def update_metadata(self, title: str | None = None, agenda: List[str] | None = None) -> None:
        if title is not None:
            self.title = title.strip() or None

        if agenda is not None:
            cleaned = [item.strip() for item in agenda if item.strip()]
            self.agenda = cleaned

    def append_segments(self, new_segments: List[DiarizedSegment]) -> List[str]:
        new_speakers = [s.speaker for s in new_segments if s.speaker not in self.speaker_labels]
        self.segments.extend(new_segments)
        return new_speakers

    def label_speaker(self, speaker_id: str, display_name: str) -> None:
        self.speaker_labels[speaker_id] = display_name

    def forget_speaker(self, speaker_id: str, redaction_text: str = "[redacted]") -> int:
        """Remove a speaker label and redact matching segments.

        Returns the number of segments scrubbed. The diarization speaker keys
        remain in place to keep timelines stable for clients, but the text is
        replaced with a deterministic placeholder.
        """

        scrubbed = 0
        self.speaker_labels.pop(speaker_id, None)

        updated_segments: List[DiarizedSegment] = []
        for segment in self.segments:
            if segment.speaker == speaker_id:
                scrubbed += 1
                updated_segments.append(DiarizedSegment(speaker=segment.speaker, text=redaction_text))
            else:
                updated_segments.append(segment)

        self.segments = updated_segments
        return scrubbed

    def summary(self, summarizer) -> Summary:
        transcript_text = " ".join(segment.text for segment in self.segments)
        return summarizer.summarize(transcript_text)

    def append_audio(self, samples: List[float], trim_to: int | None = None) -> int:
        self.audio_buffer.extend(samples)

        if trim_to is not None and trim_to > 0:
            overflow = len(self.audio_buffer) - trim_to
            if overflow > 0:
                self.audio_buffer = self.audio_buffer[overflow:]

        return len(samples)

    def audio_samples(self, max_samples: int | None = None) -> List[float]:
        if max_samples is None or max_samples <= 0:
            return list(self.audio_buffer)

        return self.audio_buffer[-max_samples:]

    def clear_audio(self) -> None:
        self.audio_buffer = []

    def export(self, summarizer) -> SessionExport:
        summary = self.summary(summarizer)
        return SessionExport(
            session_id=self.session_id,
            created_at=self.created_at,
            language=self.language,
            title=self.title,
            agenda=list(self.agenda),
            segments=[
                SegmentRecord(
                    speaker=segment.speaker,
                    speaker_label=self.speaker_labels.get(segment.speaker),
                    text=segment.text,
                )
                for segment in self.segments
            ],
            summary=summary,
        )

    def serialized_segments(self) -> List[Dict[str, str]]:
        return [
            {
                "speaker": segment.speaker,
                "speaker_label": self.speaker_labels.get(segment.speaker),
                "text": segment.text,
            }
            for segment in self.segments
        ]

    def metadata_view(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "agenda": list(self.agenda),
            "created_at": self.created_at.isoformat(),
        }


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create(self, session_id: str, language: str = "fa") -> Session:
        session = Session(session_id=session_id, language=language)
        self._sessions[session_id] = session
        return session

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def append(self, session_id: str, segments: List[DiarizedSegment]) -> Tuple[Session, List[str]]:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session {session_id}")
        session = self._sessions[session_id]
        new_speakers = session.append_segments(segments)
        return session, new_speakers

    def update_metadata(self, session_id: str, *, title: str | None = None, agenda: List[str] | None = None) -> Session:
        session = self.get(session_id)
        session.update_metadata(title=title, agenda=agenda)
        return session

    def append_audio(self, session_id: str, samples: List[float], trim_to: int | None = None) -> Session:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session {session_id}")

        session = self._sessions[session_id]
        session.append_audio(samples, trim_to=trim_to)
        return session

    def get(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session {session_id}")
        return self._sessions[session_id]

    def label(self, session_id: str, speaker_id: str, display_name: str) -> Session:
        session = self.get(session_id)
        session.label_speaker(speaker_id, display_name)
        return session

    def forget(self, session_id: str, speaker_id: str, redaction_text: str = "[redacted]") -> Tuple[Session, int]:
        session = self.get(session_id)
        scrubbed = session.forget_speaker(speaker_id, redaction_text)
        return session, scrubbed

    def summary(self, session_id: str, summarizer) -> Summary:
        return self.get(session_id).summary(summarizer)

    def export(self, session_id: str, summarizer) -> SessionExport:
        return self.get(session_id).export(summarizer)

    def audio_samples(self, session_id: str, max_samples: int | None = None) -> List[float]:
        return self.get(session_id).audio_samples(max_samples=max_samples)

    def process_audio_buffer(
        self,
        session_id: str,
        stt_service,
        diarization_service,
        threshold: float = 0.01,
        min_run: int = 3,
        transcript_hint: str = "buffered audio",
        clear_buffer: bool = False,
    ) -> Tuple[Session, List[SpeechSpan], List[str]]:
        session = self.get(session_id)

        spans = detect_speech(session.audio_buffer, threshold=threshold, min_run=min_run)
        if not spans:
            return session, spans, []

        transcript_text = transcript_hint.strip() or "buffered audio"
        span_descriptions = [f"buffer {span.start_index}-{span.end_index}" for span in spans]
        transcript = stt_service.transcribe(
            f"{transcript_text}: {'; '.join(span_descriptions)}", language=session.language
        )
        diarized = diarization_service.diarize(transcript)
        manifest_segments = [DiarizedSegment(speaker=s.speaker, text=s.text) for s in diarized]

        session, new_speakers = self.append(session_id, manifest_segments)

        if clear_buffer:
            session.clear_audio()

        return session, spans, new_speakers

    def delete(self, session_id: str) -> None:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session {session_id}")
        del self._sessions[session_id]

    def clear(self) -> None:
        self._sessions.clear()

    def restore(self, export: SessionExport) -> Session:
        """Hydrate a session from a persisted export manifest."""

        session = Session(
            session_id=export.session_id,
            language=export.language,
            created_at=export.created_at,
            title=export.title,
            agenda=list(export.agenda),
            segments=[
                DiarizedSegment(speaker=segment.speaker, text=segment.text)
                for segment in export.segments
            ],
            speaker_labels={
                segment.speaker: segment.speaker_label
                for segment in export.segments
                if segment.speaker_label
            },
        )
        self._sessions[session.session_id] = session
        return session
