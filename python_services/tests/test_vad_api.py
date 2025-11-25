from importlib import reload

from fastapi import TestClient


def reload_server(monkeypatch):
    def _reload():
        import python_services.api.server as server

        monkeypatch.delenv("PY_SERVICES_API_KEY", raising=False)
        reload(server)
        return server

    return _reload


def test_vad_segments_detected(monkeypatch):
    # Samples contain two speech runs above threshold (indexes 1-3 and 6-8)
    server = reload_server(monkeypatch)()

    client = TestClient(server.app)
    response = client.post(
        "/vad",
        json={"samples": [0.0, 0.02, 0.03, 0.025, 0.0, 0.0, 0.04, 0.04, 0.04], "threshold": 0.015, "min_run": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["triggered"] is True
    assert payload["segments"] == [{"start_index": 1, "end_index": 3}, {"start_index": 6, "end_index": 8}]


def test_vad_requires_positive_run_length(monkeypatch):
    server = reload_server(monkeypatch)()

    client = TestClient(server.app)
    response = client.post("/vad", json={"samples": [0.1, 0.1, 0.1], "min_run": 0})

    assert response.status_code == 400
    assert response.json()["detail"] == "min_run must be >= 1"
