from pathlib import Path

from python_services.ops.smoke import run_smoke


def test_run_smoke_creates_and_fetches_export(tmp_path, monkeypatch):
    # Ensure API key gating is tolerated when provided.
    monkeypatch.setenv("PY_SERVICES_API_KEY", "test-key")

    status, report = run_smoke(storage_dir=str(tmp_path), api_key="test-key")

    assert status == "ok"
    assert report["session"]["session_id"] == "smoke-session"
    assert report["exports"] == ["smoke-session"]
    assert any(segment.get("speaker_label") == "Ali" for segment in report["segments"])

    saved = Path(report["storage_path"])
    assert saved.exists()
    # Stored manifest should live inside the configured directory.
    assert saved.parent == tmp_path / "exports"
