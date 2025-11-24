from importlib import reload

from fastapi import TestClient


def test_append_unknown_session_returns_404():
    import python_services.api.server as server

    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    response = client.post("/sessions/append", json={"session_id": "missing", "transcript": "salam"})

    assert response.status_code == 404


def test_forget_speaker_endpoint_scrubs_segments():
    import python_services.api.server as server

    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    client.post("/sessions", json={"session_id": "forget", "language": "fa"})
    appended = client.post("/sessions/append", json={"session_id": "forget", "transcript": "salam"})
    speaker_id = appended.json()["new_speakers"][0]

    labeled = client.post(
        "/sessions/forget/speakers",
        json={"speaker_id": speaker_id, "display_name": "Temp"},
    )
    assert labeled.status_code == 200

    forgot = client.post(
        "/sessions/forget/speakers/forget",
        json={"speaker_id": speaker_id, "redaction_text": "[removed]"},
    )

    assert forgot.status_code == 200
    payload = forgot.json()
    assert payload["scrubbed_segments"] == 1
    assert payload["segments"][0]["text"] == "[removed]"
    assert payload["segments"][0]["speaker_label"] is None


def test_delete_session_removes_export_and_session(tmp_path, monkeypatch):
    import python_services.api.server as server

    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", str(tmp_path))
    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    client.post("/sessions", json={"session_id": "cleanup", "language": "fa"})
    client.post("/sessions/append", json={"session_id": "cleanup", "transcript": "salam"})
    stored = client.post("/sessions/cleanup/export/store")
    assert stored.status_code == 200

    deleted = client.delete("/sessions/cleanup")
    assert deleted.status_code == 200
    assert deleted.json()["session_removed"] is True
    assert deleted.json()["export_removed"] is True

    listing = client.get("/exports")
    assert listing.json()["exports"] == []

    missing_session = client.get("/sessions/cleanup")
    assert missing_session.status_code == 404
