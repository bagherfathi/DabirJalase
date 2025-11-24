from python_services.diarization.diarization_service import DiarizationService
from python_services.sessions import SessionStore
from python_services.stt.whisper_service import WhisperService
from python_services.vad.simple_vad import SpeechSpan


def test_append_and_trim_audio_buffer():
    store = SessionStore()
    store.create("s1")

    session = store.append_audio("s1", [0.1, 0.2, 0.3])
    assert session.audio_buffer == [0.1, 0.2, 0.3]

    store.append_audio("s1", [0.4, 0.5], trim_to=4)
    assert session.audio_buffer == [0.2, 0.3, 0.4, 0.5]

    snapshot = store.audio_samples("s1", max_samples=2)
    assert snapshot == [0.4, 0.5]


def test_audio_buffer_requires_session():
    store = SessionStore()
    try:
        store.append_audio("missing", [0.1])
    except KeyError as exc:
        assert "Unknown session" in str(exc)
    else:  # pragma: no cover - defensively ensure exceptions propagate
        raise AssertionError("append_audio should raise for unknown session")


def test_process_audio_buffer_appends_and_optionally_clears():
    store = SessionStore()
    stt = WhisperService()
    diarization = DiarizationService()

    store.create("s2")
    store.append_audio("s2", [0.0, 0.02, 0.03, 0.0])

    session, spans, new_speakers = store.process_audio_buffer(
        "s2", stt, diarization, threshold=0.02, min_run=2, transcript_hint="buffer processing", clear_buffer=True
    )

    assert spans == [SpeechSpan(start_index=1, end_index=2)]
    assert len(session.segments) >= 1
    assert new_speakers
    assert session.audio_buffer == []
