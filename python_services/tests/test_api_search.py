from importlib import reload

from fastapi import TestClient


def _fresh_client():
    import python_services.api.server as server

    reload(server)
    server.sessions.clear()
    return TestClient(server.app)


def test_session_search_returns_matches():
    client = _fresh_client()

    created = client.post("/sessions", json={"session_id": "search", "language": "fa"})
    assert created.status_code == 200

    first = client.post("/sessions/append", json={"session_id": "search", "transcript": "سلام دنیا"})
    assert first.status_code == 200

    second = client.post(
        "/sessions/append", json={"session_id": "search", "transcript": "جلسه درباره برنامه"}
    )
    assert second.status_code == 200

    search = client.get("/sessions/search/search?query=سلام")
    assert search.status_code == 200
    payload = search.json()
    assert payload["total"] == 1
    assert payload["results"][0]["text"] == "سلام دنیا"


def test_session_search_requires_query():
    client = _fresh_client()

    client.post("/sessions", json={"session_id": "search2", "language": "fa"})
    response = client.get("/sessions/search2/search")

    assert response.status_code == 400
    assert "query" in response.json()["detail"]
