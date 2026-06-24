"""Tests for the FastAPI app lifespan and the /health failure path."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services import redis_client


def test_lifespan_creates_index_on_startup(monkeypatch, fake_redis):
    called = {}
    monkeypatch.setattr(redis_client, "ensure_index", lambda: called.setdefault("ok", True))
    from app.main import app

    with TestClient(app):  # triggers lifespan startup/shutdown
        pass

    assert called.get("ok") is True


def test_lifespan_tolerates_index_error(monkeypatch, fake_redis):
    def boom():
        raise RuntimeError("redis down at startup")

    monkeypatch.setattr(redis_client, "ensure_index", boom)
    from app.main import app

    with TestClient(app):  # must not raise despite the failure
        pass


def test_root_returns_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["docs"] == "/docs"


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "connected"}


def test_health_503_when_redis_down(client, monkeypatch):
    monkeypatch.setattr(redis_client, "ping", lambda: False)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "redis": "disconnected"}


def test_config_local_provider_needs_no_key(client):
    # Defaults: ollama + sentence-transformers (no key required).
    body = client.get("/config").json()
    assert body["requires_api_key"] is False
    assert body["key_providers"] == []
    assert body["supported_llm_providers"] == [
        "openai",
        "anthropic",
        "gemini",
        "ollama",
    ]


def test_config_reports_auth_disabled_by_default(client):
    body = client.get("/config").json()
    assert body["auth_enabled"] is False
    assert body["auth_providers"] == []


def test_config_reports_auth_enabled(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    body = client.get("/config").json()
    assert body["auth_enabled"] is True
    assert body["auth_providers"] == ["google", "github"]


def test_config_reports_key_provider(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    from app.config import get_settings

    get_settings.cache_clear()
    body = client.get("/config").json()
    assert body["requires_api_key"] is True
    assert body["key_providers"] == ["openai"]  # deduplicated


def test_config_reports_multiple_key_providers(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    from app.config import get_settings

    get_settings.cache_clear()
    body = client.get("/config").json()
    assert body["key_providers"] == ["anthropic", "openai"]
