"""Lightweight heuristic summarizer for scaffolding purposes.

This is intentionally deterministic and side-effect free so tests can run in
restricted environments without pulling large model dependencies. Replace with
an actual abstractive/qa-aware summarizer once models are wired.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Summary:
    bullet_points: List[str]
    highlight: str


class Summarizer:
    """Extracts simple bullet points and a highlight sentence."""

    def summarize(self, transcript: str, max_points: int = 5) -> Summary:
        cleaned = self._normalize(transcript)
        sentences = [s for s in cleaned.split(".") if s.strip()]
        bullet_points = [sent.strip() for sent in sentences[:max_points]]
        highlight = bullet_points[0] if bullet_points else ""
        return Summary(bullet_points=bullet_points, highlight=highlight)

    def _normalize(self, text: str) -> str:
        """Remove duplicated whitespace and trim."""
        collapsed = " ".join(text.split())
        return collapsed.strip()
