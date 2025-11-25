from importlib import reload
from pathlib import Path

from fastapi import TestClient


def test_export_endpoint_returns_summary_and_labels():
    import python_services.api.server as server

    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post(
        "/sessions",
        json={"session_id": "api-export", "language": "fa", "title": "Weekly sync", "agenda": ["Updates"]},
    )
    assert created.status_code == 200
    assert created.json()["metadata"]["title"] == "Weekly sync"

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
    assert payload["metadata"]["title"] == "Weekly sync"


def test_export_store_and_fetch(tmp_path, monkeypatch):
    import python_services.api.server as server

    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", str(tmp_path))
    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post(
        "/sessions",
        json={"session_id": "persist", "language": "fa", "title": "Persisted"},
    )
    assert created.status_code == 200

    appended = client.post("/sessions/append", json={"session_id": "persist", "transcript": "salam"})
    assert appended.status_code == 200

    stored = client.post("/sessions/persist/export/store")
    assert stored.status_code == 200
    saved_path = stored.json()["saved_path"]
    assert str(tmp_path) in saved_path

    listing = client.get("/exports")
    assert listing.status_code == 200
    assert listing.json()["exports"] == ["persist"]

    fetched = client.get("/exports/persist")
    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["session_id"] == "persist"
    assert payload["summary"]["highlight"]
    assert payload["metadata"]["title"] == "Persisted"


def test_retention_sweep_removes_old_exports(tmp_path, monkeypatch):
    import json
    import python_services.api.server as server

    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", str(tmp_path))
    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post("/sessions", json={"session_id": "cleanup", "language": "fa"})
    assert created.status_code == 200

    appended = client.post("/sessions/append", json={"session_id": "cleanup", "transcript": "salam"})
    assert appended.status_code == 200

    stored = client.post("/sessions/cleanup/export/store")
    assert stored.status_code == 200

    export_path = Path(stored.json()["saved_path"])
    payload = json.loads(export_path.read_text())
    payload["created_at"] = "2023-01-01T00:00:00+00:00"
    export_path.write_text(json.dumps(payload))

    sweep = client.post("/exports/retention/sweep", json={"retention_days": 30})
    assert sweep.status_code == 200
    assert sweep.json()["removed"] == ["cleanup"]


def test_restore_endpoint_rehydrates_session(tmp_path, monkeypatch):
    import python_services.api.server as server

    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", str(tmp_path))
    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post("/sessions", json={"session_id": "restore-me", "language": "fa"})
    assert created.status_code == 200

    appended = client.post("/sessions/append", json={"session_id": "restore-me", "transcript": "salam"})
    assert appended.status_code == 200
    speaker_id = appended.json()["new_speakers"][0]

    labeled = client.post(
        "/sessions/restore-me/speakers", json={"speaker_id": speaker_id, "display_name": "Guest"}
    )
    assert labeled.status_code == 200

    stored = client.post("/sessions/restore-me/export/store")
    assert stored.status_code == 200

    # Simulate a restart that clears in-memory sessions
    server.sessions.clear()

    restored = client.post("/exports/restore-me/restore")
    assert restored.status_code == 200
    payload = restored.json()

    assert payload["session_id"] == "restore-me"
    assert payload["segments"][0]["speaker_label"] == "Guest"
    assert payload["summary"]["highlight"]


def test_export_download_supports_markdown(tmp_path, monkeypatch):
    import python_services.api.server as server

    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", str(tmp_path))
    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post(
        "/sessions", json={"session_id": "dl", "language": "fa", "title": "Review", "agenda": ["Intro"]}
    )
    assert created.status_code == 200

    appended = client.post("/sessions/append", json={"session_id": "dl", "transcript": "salam"})
    assert appended.status_code == 200

    stored = client.post("/sessions/dl/export/store")
    assert stored.status_code == 200

    download = client.get("/exports/dl/download?format=markdown")
    assert download.status_code == 200
    assert download.headers["Content-Type"] == "text/markdown"
    content = download.content
    assert "# Review" in content
    assert "**Highlight:**" in content
    assert "Intro" in content


def test_export_download_rejects_unknown_format(tmp_path, monkeypatch):
    import python_services.api.server as server

    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", str(tmp_path))
    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)
    created = client.post("/sessions", json={"session_id": "badfmt", "language": "fa"})
    assert created.status_code == 200
    stored = client.post("/sessions/badfmt/export/store")
    assert stored.status_code == 200

    download = client.get("/exports/badfmt/download?format=pdf")
    assert download.status_code == 400
    assert "format must be one of" in download.json()["detail"]
