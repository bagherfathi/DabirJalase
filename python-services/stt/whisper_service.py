"""Stub for Whisper-based STT pipeline with diarization handoff."""

from typing import Any, Dict


def transcribe(audio_bytes: bytes) -> Dict[str, Any]:
    """Return a placeholder transcription payload.

    Replace with batched inference, VAD gating, and confidence outputs.
    """
    return {
        "text": "[placeholder transcript]",
        "language": "fa",
        "segments": [],
        "confidence": 0.0,
    }
