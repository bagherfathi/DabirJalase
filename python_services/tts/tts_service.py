"""Text-to-speech scaffold that returns deterministic byte payloads."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any


@dataclass
class SynthesizedAudio:
    text: str
    encoding: str
    payload: bytes

    def as_base64(self) -> str:
        return base64.b64encode(self.payload).decode("utf-8")


class TextToSpeechService:
    def synthesize(self, text: str, voice: str = "fa-IR-Standard-A") -> SynthesizedAudio:
        normalized = text.strip()
        payload = normalized.encode("utf-8")
        return SynthesizedAudio(text=normalized, encoding="text/utf-8", payload=payload)
