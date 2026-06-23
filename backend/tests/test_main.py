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


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "connected"}


def test_health_503_when_redis_down(client, monkeypatch):
    monkeypatch.setattr(redis_client, "ping", lambda: False)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "redis": "disconnected"}
