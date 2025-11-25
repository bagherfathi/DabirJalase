"""Run a deterministic demo session to showcase the scaffold flow."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Optional

from python_services.diarization.diarization_service import DiarizationService
from python_services.sessions import SessionStore
from python_services.storage.persistence import save_export
from python_services.summarization.summarizer import Summarizer
from python_services.stt.whisper_service import WhisperService


DEFAULT_UTTERANCES = (
    "سلام همه. امروز درباره محصول جدید صحبت می‌کنیم.",
    "من فکر می‌کنم باید روی کیفیت تمرکز کنیم.",
    "موافقم، همچنین باید زمان‌بندی را رعایت کنیم.",
)
DEFAULT_SPEAKER_NAMES = (
    "Ali",
    "Sara",
    "Nima",
)


def run_demo_session(
    *,
    utterances: Iterable[str] = DEFAULT_UTTERANCES,
    speaker_names: Iterable[str] = DEFAULT_SPEAKER_NAMES,
    language: str = "fa",
    storage_dir: Optional[Path] = None,
):
    """Create a demo session, append utterances, label speakers, and return the manifest."""

    stt = WhisperService()
    diarizer = DiarizationService()
    summarizer = Summarizer()
    store = SessionStore()
    session_id = "demo-session"

    store.create(session_id, language=language)

    for content in utterances:
        transcript = stt.transcribe(content, language=language)
        diarized = diarizer.diarize(transcript)
        store.append(session_id, diarized)

    # Deterministically label discovered speakers with provided names
    discovered = sorted({segment.speaker for segment in store.get(session_id).segments})
    for speaker_id, display_name in zip(discovered, speaker_names):
        store.label(session_id, speaker_id, display_name)

    manifest = store.export(session_id, summarizer)

    saved_path = None
    if storage_dir:
        saved_path = save_export(manifest, str(storage_dir))

    return manifest, saved_path


def _format_manifest(manifest):
    return {
        "session_id": manifest.session_id,
        "created_at": manifest.created_at.isoformat(),
        "language": manifest.language,
        "summary": asdict(manifest.summary),
        "segments": [asdict(segment) for segment in manifest.segments],
    }


def main():
    parser = argparse.ArgumentParser(description="Run the scaffolded meeting demo")
    parser.add_argument(
        "--persist",
        type=Path,
        default=None,
        help="Directory to persist the exported manifest (defaults to in-memory only)",
    )
    args = parser.parse_args()

    manifest, saved_path = run_demo_session(storage_dir=args.persist)

    print("Generated demo manifest:")
    print(_format_manifest(manifest))
    if saved_path:
        print(f"Saved manifest to {saved_path}")


if __name__ == "__main__":
    main()
