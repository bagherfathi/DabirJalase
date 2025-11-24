"""FastAPI wiring for the meeting assistant services.

Endpoints remain lightweight and deterministic to keep the scaffold runnable
without model downloads. Replace service implementations with real STT/TTS and
diarization pipelines when models are available.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from typing import List

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from python_services.config import ServiceSettings
from python_services.diarization.diarization_service import DiarizationService
from python_services.ops.metrics import MetricsRegistry
from python_services.sessions import SessionStore
from python_services.storage.manifests import TranscriptManifest
from python_services.stt.whisper_service import Transcript, WhisperService
from python_services.summarization.summarizer import Summarizer
from python_services.tts.tts_service import TextToSpeechService

settings = ServiceSettings.from_env()
logger = logging.getLogger("python_services.api")

app = FastAPI(title="Meeting Assistant Services")


@app.middleware("http")
async def enforce_security(request: Request, call_next):
    request_id = request.headers.get(settings.request_id_header) or str(uuid.uuid4())

    if settings.api_key:
        provided = request.headers.get("x-api-key")
        if provided != settings.api_key:
            logger.warning("rejecting request: missing or invalid API key", extra={"path": request.url.path})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")

    response = await call_next(request)
    response.headers[settings.request_id_header] = request_id
    return response

stt = WhisperService()
diarization = DiarizationService()
tts = TextToSpeechService()
summarizer = Summarizer()
sessions = SessionStore()
metrics = MetricsRegistry()


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


class SessionAppendRequest(BaseModel):
    session_id: str
    transcript: str


class SpeakerLabelRequest(BaseModel):
    speaker_id: str
    display_name: str


class TtsRequest(BaseModel):
    text: str
    voice: str = "fa-IR-Standard-A"


@app.get("/health")
def healthcheck():
    return {"status": "ok", "message": "scaffold"}


@app.post("/transcribe")
def transcribe(request: TranscribeRequest):
    transcript: Transcript = stt.transcribe(request.content, language=request.language)
    metrics.counter("transcribe.calls").inc()
    return {"language": transcript.language, "segments": [asdict(s) for s in transcript.segments]}


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
    metrics.counter("sessions.create").inc()
    return {"session_id": session.session_id, "language": session.language, "segments": []}


@app.post("/sessions/append")
def append_to_session(request: SessionAppendRequest):
    transcript = stt.transcribe(request.transcript)
    diarized = diarization.diarize(transcript)
    manifest = TranscriptManifest.from_diarized(
        transcript_id=request.session_id, language=transcript.language, segments=diarized
    )
    session, new_speakers = sessions.append(request.session_id, manifest.segments)
    metrics.counter("sessions.append").inc()
    return {
        "session_id": session.session_id,
        "segments": session.serialized_segments(),
        "new_speakers": new_speakers,
    }


@app.get("/sessions/{session_id}/summary")
def summarize_session(session_id: str):
    summary = sessions.summary(session_id, summarizer)
    metrics.counter("sessions.summary").inc()
    return {"highlight": summary.highlight, "bullet_points": summary.bullet_points}


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = sessions.get(session_id)
    metrics.counter("sessions.get").inc()
    return {"session_id": session.session_id, "segments": session.serialized_segments(), "language": session.language}


@app.post("/sessions/{session_id}/speakers")
def label_speaker(session_id: str, request: SpeakerLabelRequest):
    session = sessions.label(session_id, request.speaker_id, request.display_name)
    metrics.counter("sessions.label").inc()
    return {
        "session_id": session.session_id,
        "speaker": request.speaker_id,
        "display_name": request.display_name,
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
