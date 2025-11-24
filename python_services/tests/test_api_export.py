from importlib import reload

from fastapi import TestClient


def test_export_endpoint_returns_summary_and_labels():
    import python_services.api.server as server

    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post("/sessions", json={"session_id": "api-export", "language": "fa"})
    assert created.status_code == 200

    appended = client.post("/sessions/append", json={"session_id": "api-export", "transcript": "salam"})
    assert appended.status_code == 200
    speaker_id = appended.json()["new_speakers"][0]

    label = client.post(
        "/sessions/api-export/speakers",
        json={"speaker_id": speaker_id, "display_name": "Host"},
    )
    assert label.status_code == 200

    exported = client.get("/sessions/api-export/export")
    assert exported.status_code == 200
    payload = exported.json()

    assert payload["summary"]["highlight"]
    assert payload["segments"][0]["speaker"] == speaker_id
    assert payload["segments"][0]["speaker_label"] == "Host"
