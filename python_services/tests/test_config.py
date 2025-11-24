from python_services.config import ServiceSettings


def test_default_settings():
    settings = ServiceSettings.from_env()
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.reload is False
    assert settings.log_level == "info"
    assert settings.api_key is None
    assert settings.request_id_header == "x-request-id"
    assert settings.storage_dir == "data"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("PY_SERVICES_HOST", "127.0.0.1")
    monkeypatch.setenv("PY_SERVICES_PORT", "9999")
    monkeypatch.setenv("PY_SERVICES_RELOAD", "true")
    monkeypatch.setenv("PY_SERVICES_LOG_LEVEL", "debug")
    monkeypatch.setenv("PY_SERVICES_API_KEY", "secret")
    monkeypatch.setenv("PY_SERVICES_REQUEST_ID_HEADER", "x-custom-id")
    monkeypatch.setenv("PY_SERVICES_STORAGE_DIR", "/tmp/exports")

    settings = ServiceSettings.from_env()

    assert settings.host == "127.0.0.1"
    assert settings.port == 9999
    assert settings.reload is True
    assert settings.log_level == "debug"
    assert settings.api_key == "secret"
    assert settings.request_id_header == "x-custom-id"
    assert settings.storage_dir == "/tmp/exports"

