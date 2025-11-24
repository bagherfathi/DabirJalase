from importlib import reload

from fastapi import TestClient


def reload_server(monkeypatch):
    def _reload():
        import python_services.api.server as server

        monkeypatch.delenv("PY_SERVICES_API_KEY", raising=False)
        reload(server)
        return server

    return _reload


def test_append_and_fetch_audio(monkeypatch):
    server = reload_server(monkeypatch)()
    client = TestClient(server.app)

    client.post("/sessions", json={"session_id": "s1"})

    append_response = client.post(
        "/sessions/s1/audio",
        json={"samples": [0.1, 0.2, 0.3]},
    )
    assert append_response.status_code == 200
    payload = append_response.json()
    assert payload == {"session_id": "s1", "added": 3, "buffered": 3}

    append_response = client.post(
        "/sessions/s1/audio",
        json={"samples": [0.4, 0.5], "trim_to": 4},
    )
    assert append_response.status_code == 200
    payload = append_response.json()
    assert payload["buffered"] == 4

    fetch_response = client.get("/sessions/s1/audio?max_samples=2")
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()
    assert fetched["samples"] == [0.4, 0.5]
    assert fetched["buffered"] == 4


def test_audio_append_validation(monkeypatch):
    server = reload_server(monkeypatch)()
    client = TestClient(server.app)

    client.post("/sessions", json={"session_id": "s2"})

    invalid_trim = client.post("/sessions/s2/audio", json={"samples": [0.1], "trim_to": 0})
    assert invalid_trim.status_code == 400

    missing_samples = client.post("/sessions/s2/audio", json={"samples": []})
    assert missing_samples.status_code == 400


def test_audio_append_missing_session(monkeypatch):
    server = reload_server(monkeypatch)()
    client = TestClient(server.app)

    response = client.post("/sessions/missing/audio", json={"samples": [0.1]})
    assert response.status_code == 404
