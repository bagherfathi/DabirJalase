from importlib import reload

from fastapi import TestClient


def reload_server():
    import python_services.api.server as server

    reload(server)
    return server


def test_metrics_snapshot_returns_counters():
    server = reload_server()
    client = TestClient(server.app)

    transcribe = client.post("/transcribe", json={"content": "salam", "language": "fa"})
    summarize = client.post("/summarize", json={"transcript": "hello world"})

    assert transcribe.status_code == 200
    assert summarize.status_code == 200

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()

    assert payload["counters"]["transcribe.calls"] == 1
    assert payload["counters"]["summarize.calls"] == 1
