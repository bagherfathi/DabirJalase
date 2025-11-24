from python_services.api import server
from python_services.sessions import SessionStore


def test_create_and_append_session():
    store = SessionStore()
    created = store.create("s1", language="fa")
    assert created.session_id == "s1"
    assert created.language == "fa"
    assert created.segments == []

    segment = server.TranscriptManifest.from_diarized(
        transcript_id="s1", language="fa", segments=server.diarization.diarize(server.stt.transcribe("salam"))
    )
    updated = store.append("s1", segment.segments)
    assert len(updated.segments) == len(segment.segments)


def test_session_summary_endpoint(monkeypatch):
    store = server.sessions
    store.clear()
    store.create("s-demo")
    store.append(
        "s-demo",
        server.TranscriptManifest.from_diarized(
            transcript_id="s-demo", language="fa", segments=server.diarization.diarize(server.stt.transcribe("salam"))
        ).segments,
    )
    summary = store.summary("s-demo", server.summarizer)
    assert summary.highlight
    assert summary.bullet_points
