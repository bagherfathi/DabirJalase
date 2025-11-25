"""Deterministic VAD stub used to gate when to ship audio to STT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class SpeechSpan:
    start_index: int
    end_index: int

    def asdict(self) -> dict:
        return {"start_index": self.start_index, "end_index": self.end_index}


def detect_speech(samples: Iterable[float], threshold: float = 0.01, min_run: int = 3) -> List[SpeechSpan]:
    """Return spans where the absolute sample amplitude crosses the threshold.

    This intentionally stays simple/deterministic so the scaffold remains
    runnable without native dependencies. Replace with a real VAD (e.g.
    WebRTC VAD or Silero) during production hardening.
    """

    window = list(samples)
    spans: List[SpeechSpan] = []
    start = None
    run_length = 0

    for index, sample in enumerate(window):
        is_speech = abs(sample) >= threshold
        if is_speech:
            run_length += 1
            if start is None:
                start = index
        else:
            if start is not None and run_length >= min_run:
                spans.append(SpeechSpan(start_index=start, end_index=index - 1))
            start = None
            run_length = 0

    if start is not None and run_length >= min_run:
        spans.append(SpeechSpan(start_index=start, end_index=len(window) - 1))

    return spans
