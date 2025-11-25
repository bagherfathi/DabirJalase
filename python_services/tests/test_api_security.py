from importlib import reload

import pytest
from fastapi import TestClient


@pytest.fixture
def reload_server(monkeypatch):
    def _reload():
        import python_services.api.server as server

        reload(server)
        return server

    monkeypatch.delenv("PY_SERVICES_API_KEY", raising=False)
    monkeypatch.delenv("PY_SERVICES_REQUEST_ID_HEADER", raising=False)
    monkeypatch.delenv("PY_SERVICES_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("PY_SERVICES_MAX_REQUESTS_PER_MINUTE", raising=False)
    return _reload


def test_request_id_added_by_default(reload_server):
    server = reload_server()
    client = TestClient(server.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert server.settings.request_id_header in response.headers
    assert response.headers[server.settings.request_id_header]


def test_api_key_required_when_configured(monkeypatch, reload_server):
    monkeypatch.setenv("PY_SERVICES_API_KEY", "secret")
    server = reload_server()
    client = TestClient(server.app)

    unauthorized = client.get("/health")
    assert unauthorized.status_code == 401

    authorized = client.get("/health", headers={"x-api-key": "secret"})
    assert authorized.status_code == 200


def test_cors_headers_applied(monkeypatch, reload_server):
    monkeypatch.setenv("PY_SERVICES_ALLOWED_ORIGINS", "http://example.com")
    server = reload_server()
    client = TestClient(server.app)

    response = client.get("/health", headers={"origin": "http://example.com"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://example.com"
