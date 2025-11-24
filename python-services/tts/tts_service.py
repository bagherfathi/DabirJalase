"""Stub for TTS playback and caching."""

from typing import Any, Dict


def synthesize(text: str, speaker: str | None = None) -> Dict[str, Any]:
    """Return placeholder audio handle.

    Replace with provider-backed synthesis, pronunciation normalization, and cache lookups.
    """
    return {"audio_path": None, "provider": None}
