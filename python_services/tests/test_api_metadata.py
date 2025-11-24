from importlib import reload

from fastapi import TestClient


def test_session_metadata_update_and_fetch():
    import python_services.api.server as server

    reload(server)
    server.sessions.clear()

    client = TestClient(server.app)

    created = client.post(
        "/sessions",
        json={"session_id": "meta", "language": "fa", "title": "Kickoff", "agenda": ["Intro"]},
    )
    assert created.status_code == 200
    assert created.json()["metadata"]["agenda"] == ["Intro"]

    update = client.patch(
        "/sessions/meta/metadata",
        json={"title": "Kickoff updated", "agenda": ["Intro", "Plan"]},
    )
    assert update.status_code == 200
    payload = update.json()
    assert payload["metadata"]["title"] == "Kickoff updated"
    assert payload["metadata"]["agenda"] == ["Intro", "Plan"]

    fetched = client.get("/sessions/meta")
    assert fetched.status_code == 200
    metadata = fetched.json()["metadata"]
    assert metadata["title"] == "Kickoff updated"
    assert metadata["agenda"] == ["Intro", "Plan"]
