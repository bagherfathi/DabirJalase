import io
import json
import zipfile
from importlib import reload

from fastapi import TestClient


def test_support_bundle_captures_exports(tmp_path, monkeypatch):
    import python_services.api.server as server

    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", str(tmp_path))
    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post("/sessions", json={"session_id": "support", "language": "fa"})
    assert created.status_code == 200

    appended = client.post("/sessions/append", json={"session_id": "support", "transcript": "salam"})
    assert appended.status_code == 200

    stored = client.post("/sessions/support/export/store")
    assert stored.status_code == 200

    bundle = client.get("/support/bundle")
    assert bundle.status_code == 200
    assert bundle.headers.get("Content-Type") == "application/zip"

    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        names = archive.namelist()
        assert "settings.json" in names
        assert "metrics.json" in names
        assert "sessions.json" in names
        assert "exports/index.json" in names

        exports_index = json.loads(archive.read("exports/index.json"))
        assert exports_index["export_ids"] == ["support"]
        assert "support" in exports_index
        support_export = exports_index["support"]
        assert support_export["session_id"] == "support"
