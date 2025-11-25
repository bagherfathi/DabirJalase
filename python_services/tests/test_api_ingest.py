from importlib import reload

from fastapi import TestClient


def reload_server(monkeypatch):
    def _reload():
        import python_services.api.server as server

        monkeypatch.delenv("PY_SERVICES_API_KEY", raising=False)
        reload(server)
        return server

    return _reload


def test_ingest_appends_on_vad_trigger(monkeypatch):
    server = reload_server(monkeypatch)()
    client = TestClient(server.app)

    create_response = client.post("/sessions", json={"session_id": "s1"})
    assert create_response.status_code == 200

    ingest_response = client.post(
        "/sessions/s1/ingest",
        json={
            "samples": [0.0, 0.0, 0.03, 0.04, 0.03, 0.0],
            "threshold": 0.02,
            "min_run": 2,
            "transcript_hint": "hello audio",
        },
    )

    assert ingest_response.status_code == 200
    payload = ingest_response.json()
    assert payload["triggered"] is True
    assert payload["spans"] == [{"start_index": 2, "end_index": 4}]
    assert payload["segments"]
    assert payload["segments"][0]["text"] == "hello audio: speech 2-4"
    assert payload["session_id"] == "s1"

    session_response = client.get("/sessions/s1")
    assert session_response.status_code == 200
    assert session_response.json()["segments"] == payload["segments"]


def test_ingest_skips_when_no_speech(monkeypatch):
    server = reload_server(monkeypatch)()
    client = TestClient(server.app)

    client.post("/sessions", json={"session_id": "s2"})

    ingest_response = client.post(
        "/sessions/s2/ingest",
        json={"samples": [0.0, 0.0, 0.0], "threshold": 0.05, "min_run": 2},
    )

    assert ingest_response.status_code == 200
    payload = ingest_response.json()
    assert payload["triggered"] is False
    assert payload["segments"] == []

    session_response = client.get("/sessions/s2")
    assert session_response.status_code == 200
    assert session_response.json()["segments"] == []
