from importlib import reload
from itertools import count

from fastapi import TestClient


def reload_server(monkeypatch, max_requests: str | None = None):
    if max_requests:
        monkeypatch.setenv("PY_SERVICES_MAX_REQUESTS_PER_MINUTE", max_requests)
    import python_services.api.server as server

    reload(server)
    return server


def test_rate_limit_enforced(monkeypatch):
    server = reload_server(monkeypatch, "2")
    ticks = count()
    server.rate_limiter = server.RateLimiter(2, now=lambda: next(ticks) * (10**7))

    client = TestClient(server.app)

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    blocked = client.get("/health")
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "rate limit exceeded"
