"""FastAPI wiring for the meeting assistant services.

Endpoints remain lightweight and deterministic to keep the scaffold runnable
without model downloads. Replace service implementations with real STT/TTS and
diarization pipelines when models are available.
"""
from __future__ import annotations

import collections
import logging
import uuid
from dataclasses import asdict
from typing import Callable, List

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel

from python_services.config import ServiceSettings
from python_services.diarization.diarization_service import DiarizationService
from python_services.ops.metrics import MetricsRegistry
from python_services.sessions import SessionStore
from python_services.storage import persistence
from python_services.storage import manifests
from python_services.storage.manifests import SessionExport, TranscriptManifest
from python_services.stt.whisper_service import Transcript, WhisperService
from python_services.summarization.summarizer import Summarizer
from python_services.tts.tts_service import TextToSpeechService
from python_services.vad.simple_vad import SpeechSpan, detect_speech

settings = ServiceSettings.from_env()
logger = logging.getLogger("python_services.api")

app = FastAPI(title="Meeting Assistant Services")


class RateLimiter:
    def __init__(self, max_requests_per_minute: int | None, now: Callable[[], float] | None = None):
        self.max_requests_per_minute = max_requests_per_minute
        self._now = now or uuid.uuid1().time  # stable monotonic-ish source without importing time
        self._events: collections.deque[float] = collections.deque()

    def allow(self) -> bool:
        if self.max_requests_per_minute is None:
            return True

        current = self._now()
        cutoff = current - (60 * 10**7)  # uuid time is in 100-ns increments
        while self._events and self._events[0] < cutoff:
            self._events.popleft()

        if len(self._events) >= self.max_requests_per_minute:
            return False

        self._events.append(current)
        return True


@app.middleware("http")
async def enforce_security(request: Request, call_next):
    request_id = request.headers.get(settings.request_id_header) or str(uuid.uuid4())

    if settings.api_key:
        provided = request.headers.get("x-api-key")
        if provided != settings.api_key:
            logger.warning("rejecting request: missing or invalid API key", extra={"path": request.url.path})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")

    if not rate_limiter.allow():
        logger.warning("rejecting request: rate limit exceeded", extra={"path": request.url.path})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit exceeded")

    response = await call_next(request)
    response.headers[settings.request_id_header] = request_id
    return response


@app.middleware("http")
async def apply_cors(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    allow_any = "*" in settings.allowed_origins
    if settings.allowed_origins and (allow_any or (origin and origin in settings.allowed_origins)):
        response.headers["access-control-allow-origin"] = origin if origin and not allow_any else "*"
        response.headers["access-control-allow-headers"] = "*"
        response.headers["access-control-allow-methods"] = "GET,POST,DELETE,OPTIONS"
    return response

stt = WhisperService()
diarization = DiarizationService()
tts = TextToSpeechService()
summarizer = Summarizer()
sessions = SessionStore()
metrics = MetricsRegistry()
rate_limiter = RateLimiter(settings.max_requests_per_minute)


class TranscribeRequest(BaseModel):
    content: str
    language: str = "fa"


class SummarizeRequest(BaseModel):
    transcript: str
    max_points: int = 5


class SpeakerRequest(BaseModel):
    transcript: str


class SessionCreateRequest(BaseModel):
    session_id: str
    language: str = "fa"
    title: str | None = None
    agenda: List[str] | None = None


class SessionAppendRequest(BaseModel):
    session_id: str
    transcript: str


class SpeakerLabelRequest(BaseModel):
    speaker_id: str
    display_name: str


class SessionMetadataRequest(BaseModel):
    title: str | None = None
    agenda: List[str] | None = None


class TtsRequest(BaseModel):
    text: str
    voice: str = "fa-IR-Standard-A"


class RetentionSweepRequest(BaseModel):
    retention_days: int | None = None


class ForgetSpeakerRequest(BaseModel):
    speaker_id: str
    redaction_text: str = "[redacted]"


class VadRequest(BaseModel):
    samples: List[float]
    threshold: float = 0.01
    min_run: int = 3


class SessionIngestRequest(BaseModel):
    samples: List[float]
    threshold: float = 0.01
    min_run: int = 3
    transcript_hint: str = "speech detected"


class SessionAudioAppendRequest(BaseModel):
    samples: List[float]
    trim_to: int | None = None


class ProcessBufferRequest(BaseModel):
    threshold: float = 0.01
    min_run: int = 3
    transcript_hint: str = "buffered audio"
    clear_buffer: bool = False


def _translate_session_error(exc: KeyError):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/health")
def healthcheck():
    return {"status": "ok", "message": "scaffold"}


@app.post("/transcribe")
def transcribe(request: TranscribeRequest):
    transcript: Transcript = stt.transcribe(request.content, language=request.language)
    metrics.counter("transcribe.calls").inc()
    return {"language": transcript.language, "segments": [asdict(s) for s in transcript.segments]}


@app.post("/vad")
def run_vad(request: VadRequest):
    if request.min_run < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_run must be >= 1")

    spans: List[SpeechSpan] = detect_speech(request.samples, threshold=request.threshold, min_run=request.min_run)
    metrics.counter("vad.calls").inc()
    return {"triggered": bool(spans), "segments": [span.asdict() for span in spans]}


@app.post("/sessions/{session_id}/ingest")
def ingest_session_audio(session_id: str, request: SessionIngestRequest):
    if request.min_run < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_run must be >= 1")

    spans: List[SpeechSpan] = detect_speech(request.samples, threshold=request.threshold, min_run=request.min_run)
    metrics.counter("sessions.ingest.calls").inc()

    if not spans:
        return {
            "session_id": session_id,
            "triggered": False,
            "spans": [],
            "segments": [],
            "new_speakers": [],
        }

    try:
        session = sessions.get(session_id)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)

    span_descriptions = [f"speech {span.start_index}-{span.end_index}" for span in spans]
    transcript_text = request.transcript_hint.strip() or "speech detected"
    transcript_text = f"{transcript_text}: {'; '.join(span_descriptions)}"

    transcript = stt.transcribe(transcript_text, language=session.language)
    diarized = diarization.diarize(transcript)
    manifest = TranscriptManifest.from_diarized(
        transcript_id=session_id, language=transcript.language, segments=diarized
    )

    session, new_speakers = sessions.append(session_id, manifest.segments)

    return {
        "session_id": session.session_id,
        "triggered": True,
        "spans": [span.asdict() for span in spans],
        "segments": session.serialized_segments(),
        "new_speakers": new_speakers,
    }


@app.post("/sessions/{session_id}/audio")
def append_session_audio(session_id: str, request: SessionAudioAppendRequest):
    if request.trim_to is not None and request.trim_to < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="trim_to must be >= 1 when provided")

    if not request.samples:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="samples are required")

    try:
        session = sessions.append_audio(session_id, request.samples, trim_to=request.trim_to)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)

    metrics.counter("sessions.audio.append.calls").inc()

    return {
        "session_id": session.session_id,
        "added": len(request.samples),
        "buffered": len(session.audio_buffer),
    }


@app.get("/sessions/{session_id}/audio")
def fetch_session_audio(session_id: str, max_samples: int | None = None):
    try:
        samples = sessions.audio_samples(session_id, max_samples=max_samples)
        session = sessions.get(session_id)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)

    metrics.counter("sessions.audio.fetch.calls").inc()

    return {
        "session_id": session.session_id,
        "samples": samples,
        "returned": len(samples),
        "buffered": len(session.audio_buffer),
    }


@app.post("/sessions/{session_id}/process_buffer")
def process_session_buffer(session_id: str, request: ProcessBufferRequest):
    if request.min_run < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_run must be >= 1")

    try:
        session, spans, new_speakers = sessions.process_audio_buffer(
            session_id,
            stt,
            diarization,
            threshold=request.threshold,
            min_run=request.min_run,
            transcript_hint=request.transcript_hint,
            clear_buffer=request.clear_buffer,
        )
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)

    metrics.counter("sessions.process_buffer.calls").inc()

    return {
        "session_id": session.session_id,
        "triggered": bool(spans),
        "spans": [span.asdict() for span in spans],
        "segments": session.serialized_segments(),
        "new_speakers": new_speakers,
        "buffered": len(session.audio_buffer),
    }


@app.post("/diarize")
def diarize(request: SpeakerRequest):
    transcript = stt.transcribe(request.transcript)
    diarized = diarization.diarize(transcript)
    manifest = TranscriptManifest.from_diarized(
        transcript_id="stub", language=transcript.language, segments=diarized
    )
    metrics.counter("diarize.calls").inc()
    return {"transcript_id": manifest.transcript_id, "segments": [asdict(s) for s in manifest.segments]}


@app.post("/sessions")
def create_session(request: SessionCreateRequest):
    session = sessions.create(request.session_id, language=request.language)
    session.update_metadata(title=request.title, agenda=request.agenda)
    metrics.counter("sessions.create").inc()
    return {
        "session_id": session.session_id,
        "language": session.language,
        "segments": [],
        "metadata": session.metadata_view(),
    }


@app.post("/sessions/append")
def append_to_session(request: SessionAppendRequest):
    transcript = stt.transcribe(request.transcript)
    diarized = diarization.diarize(transcript)
    manifest = TranscriptManifest.from_diarized(
        transcript_id=request.session_id, language=transcript.language, segments=diarized
    )
    try:
        session, new_speakers = sessions.append(request.session_id, manifest.segments)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    metrics.counter("sessions.append").inc()
    return {
        "session_id": session.session_id,
        "segments": session.serialized_segments(),
        "new_speakers": new_speakers,
    }


@app.get("/sessions/{session_id}/summary")
def summarize_session(session_id: str):
    try:
        session = sessions.get(session_id)
        summary = sessions.summary(session_id, summarizer)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    metrics.counter("sessions.summary").inc()
    return {
        "session_id": session.session_id,
        "metadata": session.metadata_view(),
        "highlight": summary.highlight,
        "bullet_points": summary.bullet_points,
    }


@app.get("/sessions/{session_id}/export")
def export_session(session_id: str):
    try:
        exported: SessionExport = sessions.export(session_id, summarizer)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    metrics.counter("sessions.export").inc()
    return {
        "session_id": exported.session_id,
        "created_at": exported.created_at.isoformat(),
        "language": exported.language,
        "metadata": {"title": exported.title, "agenda": exported.agenda, "created_at": exported.created_at.isoformat()},
        "segments": [asdict(segment) for segment in exported.segments],
        "summary": {"highlight": exported.summary.highlight, "bullet_points": exported.summary.bullet_points},
    }


@app.post("/sessions/{session_id}/export/store")
def export_and_store(session_id: str):
    try:
        exported: SessionExport = sessions.export(session_id, summarizer)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    saved_path = persistence.save_export(exported, settings.storage_dir)
    removed = []
    if settings.export_retention_days is not None:
        removed = persistence.prune_exports(settings.storage_dir, settings.export_retention_days)
    metrics.counter("sessions.export.store").inc()
    return {
        "session_id": exported.session_id,
        "metadata": {"title": exported.title, "agenda": exported.agenda, "created_at": exported.created_at.isoformat()},
        "saved_path": str(saved_path),
        "pruned": removed,
    }


@app.get("/exports")
def list_stored_exports():
    session_ids = persistence.list_exports(settings.storage_dir)
    metrics.counter("exports.list").inc()
    return {"exports": session_ids}


@app.get("/exports/{session_id}")
def fetch_stored_export(session_id: str):
    try:
        exported = persistence.load_export(session_id, settings.storage_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    metrics.counter("exports.load").inc()
    return {
        "session_id": exported.session_id,
        "created_at": exported.created_at.isoformat(),
        "language": exported.language,
        "metadata": {"title": exported.title, "agenda": exported.agenda, "created_at": exported.created_at.isoformat()},
        "segments": [asdict(segment) for segment in exported.segments],
        "summary": {"highlight": exported.summary.highlight, "bullet_points": exported.summary.bullet_points},
    }


@app.get("/exports/{session_id}/download")
def download_export(session_id: str, format: str = "markdown"):
    try:
        exported = persistence.load_export(session_id, settings.storage_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    fmt = (format or "markdown").lower()
    if fmt not in {"markdown", "text"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format must be one of: markdown, text",
        )

    if fmt == "markdown":
        body = manifests.render_markdown(exported)
        content_type = "text/markdown"
        extension = "md"
    else:
        body = manifests.render_text(exported)
        content_type = "text/plain"
        extension = "txt"

    metrics.counter("exports.download").inc()
    headers = {
        "Content-Type": content_type,
        "Content-Disposition": f'attachment; filename="{session_id}.{extension}"',
    }
    return Response(body, headers=headers)


@app.post("/exports/{session_id}/restore")
def restore_export(session_id: str):
    try:
        exported = persistence.load_export(session_id, settings.storage_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    restored_session = sessions.restore(exported)
    metrics.counter("exports.restore").inc()

    return {
        "session_id": restored_session.session_id,
        "created_at": restored_session.created_at.isoformat(),
        "language": restored_session.language,
        "metadata": restored_session.metadata_view(),
        "segments": restored_session.serialized_segments(),
        "summary": {
            "highlight": exported.summary.highlight,
            "bullet_points": exported.summary.bullet_points,
        },
    }


@app.post("/exports/retention/sweep")
def sweep_exports(request: RetentionSweepRequest):
    retention_days = request.retention_days or settings.export_retention_days
    if retention_days is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="retention sweeping disabled; set retention_days to enable",
        )

    removed = persistence.prune_exports(settings.storage_dir, retention_days)
    metrics.counter("exports.prune").inc()
    return {"removed": removed, "retention_days": retention_days}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    session_present = sessions.exists(session_id)
    if session_present:
        sessions.delete(session_id)
    export_removed = persistence.delete_export(session_id, settings.storage_dir)
    metrics.counter("sessions.delete").inc()
    return {
        "session_id": session_id,
        "session_removed": session_present,
        "export_removed": export_removed,
    }


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    try:
        session = sessions.get(session_id)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    metrics.counter("sessions.get").inc()
    return {
        "session_id": session.session_id,
        "segments": session.serialized_segments(),
        "language": session.language,
        "metadata": session.metadata_view(),
    }


@app.get("/sessions/{session_id}/search")
def search_session(session_id: str, query: str | None = None):
    term = (query or "").strip()
    if not term:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")

    try:
        results = sessions.search(session_id, term)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)

    metrics.counter("sessions.search").inc()
    return {
        "session_id": session_id,
        "query": term,
        "results": results,
        "total": len(results),
    }


@app.patch("/sessions/{session_id}/metadata")
def update_session_metadata(session_id: str, request: SessionMetadataRequest):
    try:
        session = sessions.update_metadata(session_id, title=request.title, agenda=request.agenda)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    metrics.counter("sessions.metadata").inc()
    return {
        "session_id": session.session_id,
        "metadata": session.metadata_view(),
        "segments": session.serialized_segments(),
    }


@app.post("/sessions/{session_id}/speakers")
def label_speaker(session_id: str, request: SpeakerLabelRequest):
    try:
        session = sessions.label(session_id, request.speaker_id, request.display_name)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    metrics.counter("sessions.label").inc()
    return {
        "session_id": session.session_id,
        "speaker": request.speaker_id,
        "display_name": request.display_name,
        "segments": session.serialized_segments(),
    }


@app.post("/sessions/{session_id}/speakers/forget")
def forget_speaker(session_id: str, request: ForgetSpeakerRequest):
    try:
        session, scrubbed = sessions.forget(session_id, request.speaker_id, request.redaction_text)
    except KeyError as exc:  # pragma: no cover - exercised via API tests
        _translate_session_error(exc)
    metrics.counter("sessions.forget").inc()
    return {
        "session_id": session.session_id,
        "speaker": request.speaker_id,
        "scrubbed_segments": scrubbed,
        "segments": session.serialized_segments(),
    }


@app.post("/summarize")
def summarize(request: SummarizeRequest):
    summary = summarizer.summarize(request.transcript, max_points=request.max_points)
    metrics.counter("summarize.calls").inc()
    return {"highlight": summary.highlight, "bullet_points": summary.bullet_points}


@app.post("/tts")
def synthesize(request: TtsRequest):
    audio = tts.synthesize(request.text, voice=request.voice)
    metrics.counter("tts.calls").inc()
    return {"encoding": audio.encoding, "payload_b64": audio.as_base64()}


@app.get("/metrics")
def metric_snapshot():
    """Expose collected counters for lightweight observability."""

    return {"counters": metrics.snapshot()}
