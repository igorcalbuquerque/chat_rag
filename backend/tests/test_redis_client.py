"""Unit tests for the Redis client factory and index management.

These use lightweight fakes (not a real Redis) so the connection, ping and
``ensure_index`` logic is covered without RediSearch.
"""

from __future__ import annotations

import redis

from app.services import redis_client


# --- get_redis ---
def test_get_redis_is_lazy_and_cached(monkeypatch):
    sentinel = object()
    calls = []

    def fake_from_url(url, **kwargs):
        calls.append((url, kwargs))
        return sentinel

    monkeypatch.setattr(redis.Redis, "from_url", fake_from_url)
    redis_client.set_redis(None)

    first = redis_client.get_redis()
    second = redis_client.get_redis()

    assert first is second is sentinel
    assert len(calls) == 1  # built once, then cached
    assert calls[0][1]["protocol"] == 2  # RESP2 forced
    redis_client.set_redis(None)


# --- ping ---
def test_ping_true():
    class Client:
        def ping(self):
            return True

    redis_client.set_redis(Client())
    assert redis_client.ping() is True
    redis_client.set_redis(None)


def test_ping_false_on_error():
    class Client:
        def ping(self):
            raise redis.exceptions.ConnectionError("down")

    redis_client.set_redis(Client())
    assert redis_client.ping() is False
    redis_client.set_redis(None)


# --- ensure_index ---
class _FakeFT:
    def __init__(self, exists: bool, has_user_id: bool = True):
        self._exists = exists
        self._has_user_id = has_user_id
        self.created = False
        self.dropped = False

    def info(self):
        if not self._exists:
            raise redis.exceptions.ResponseError("Unknown index name")
        field = "user_id" if self._has_user_id else "content"
        return {"attributes": [["identifier", field, "attribute", field, "type", "TAG"]]}

    def dropindex(self, delete_documents=False):
        self.dropped = True

    def create_index(self, schema, definition=None):
        self.created = True


class _FakeClient:
    def __init__(self, exists: bool, has_user_id: bool = True):
        self._ft = _FakeFT(exists, has_user_id)

    def ft(self, name):
        return self._ft


def test_ensure_index_creates_when_missing():
    client = _FakeClient(exists=False)
    redis_client.set_redis(client)
    redis_client.ensure_index()
    assert client._ft.created is True
    redis_client.set_redis(None)


def test_ensure_index_is_idempotent_when_present():
    client = _FakeClient(exists=True, has_user_id=True)
    redis_client.set_redis(client)
    redis_client.ensure_index()
    assert client._ft.created is False  # not recreated
    assert client._ft.dropped is False
    redis_client.set_redis(None)


def test_ensure_index_recreates_when_user_id_field_missing():
    # An older index without the user_id field is dropped and rebuilt.
    client = _FakeClient(exists=True, has_user_id=False)
    redis_client.set_redis(client)
    redis_client.ensure_index()
    assert client._ft.dropped is True
    assert client._ft.created is True
    redis_client.set_redis(None)
