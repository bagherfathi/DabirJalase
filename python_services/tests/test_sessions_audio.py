from python_services.sessions import SessionStore


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
