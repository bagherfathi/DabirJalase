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
    updated, new_speakers = store.append("s1", segment.segments)
    assert len(updated.segments) == len(segment.segments)
    assert new_speakers


def test_labeling_resolves_speakers():
    store = SessionStore()
    session = store.create("session-labels")
    manifest = server.TranscriptManifest.from_diarized(
        transcript_id=session.session_id,
        language="fa",
        segments=server.diarization.diarize(server.stt.transcribe("salam")),
    )
    session, new_speakers = store.append(session.session_id, manifest.segments)
    assert new_speakers

    speaker_id = new_speakers[0]
    store.label(session.session_id, speaker_id, "Test Speaker")
    serialized = session.serialized_segments()
    assert serialized[0]["speaker_label"] == "Test Speaker"


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


def test_session_export_contains_labels_and_summary():
    store = SessionStore()
    session = store.create("export-demo")
    diarized = server.diarization.diarize(server.stt.transcribe("salam"))
    store.append(session.session_id, diarized)
    speaker_id = diarized[0].speaker
    store.label(session.session_id, speaker_id, "Guest")

    exported = store.export(session.session_id, server.summarizer)
    assert exported.summary.highlight
    assert exported.segments[0].speaker_label == "Guest"
    assert exported.segments[0].speaker == speaker_id


def test_forget_speaker_redacts_segments():
    store = SessionStore()
    session = store.create("privacy")
    diarized = server.diarization.diarize(server.stt.transcribe("salam"))
    store.append(session.session_id, diarized)
    speaker_id = diarized[0].speaker
    store.label(session.session_id, speaker_id, "Temp")

    session, scrubbed = store.forget(session.session_id, speaker_id, "[removed]")

    assert scrubbed == 1
    assert session.serialized_segments()[0]["text"] == "[removed]"
    assert session.serialized_segments()[0]["speaker_label"] is None
