from fastapi import TestClient

from python_services.api import server
from python_services.client import MeetingAssistantClient, ServiceError
from python_services.sessions import SessionStore


def _fresh_client(tmp_path):
    # Reset in-memory stores and storage location for isolation.
    server.sessions = SessionStore()
    server.settings.storage_dir = tmp_path.as_posix()
    return MeetingAssistantClient("", http_client=TestClient(server.app))


def test_client_flow_round_trip(tmp_path):
    client = _fresh_client(tmp_path)

    created = client.create_session(title="CLI", agenda=["intro"])
    session_id = created["session_id"]

    client.append_transcript(session_id, "سلام دنیا")
    search = client.search_session(session_id, "سلام")
    assert search["total"] == 1
    summary = client.get_summary(session_id)
    assert summary["metadata"]["title"] == "CLI"

    exported = client.export_session(session_id)
    assert exported["session_id"] == session_id

    stored = client.store_export(session_id)
    assert stored["saved_path"].endswith(f"{session_id}.json")

    downloaded = client.download_export(session_id, format="text")
    assert "سلام" in downloaded

    restored = client.restore_export(session_id)
    assert restored["session_id"] == session_id

    listed = client.list_exports()
    assert session_id in listed["exports"]


def test_client_raises_on_error(tmp_path):
    client = _fresh_client(tmp_path)

    try:
        client.get_summary("missing")
    except ServiceError as exc:
        assert "404" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected ServiceError for missing session")
