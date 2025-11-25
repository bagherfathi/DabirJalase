import pytest

from python_services.diarization.diarization_service import DiarizationService
from python_services.stt.whisper_service import WhisperService
from python_services.summarization.summarizer import Summarizer
from python_services.tts.tts_service import TextToSpeechService


@pytest.fixture
def stt():
    return WhisperService()


@pytest.fixture
def diarizer():
    return DiarizationService()


def test_transcribe_and_diarize(stt, diarizer):
    transcript = stt.transcribe("salam chetori")
    diarized = diarizer.diarize(transcript)
    assert diarized[0].speaker.startswith("speaker-")
    assert diarized[0].text == "salam chetori"


def test_summarizer_extracts_highlight():
    summarizer = Summarizer()
    summary = summarizer.summarize("one. two. three.", max_points=2)
    assert summary.highlight == "one"
    assert summary.bullet_points == ["one", "two"]


def test_tts_returns_base64_payload():
    tts = TextToSpeechService()
    audio = tts.synthesize("salam")
    assert audio.payload.decode("utf-8") == "salam"
    assert audio.as_base64() != ""
