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


def test_has_user_id_field_handles_bytes_keys():
    # decode_responses=False -> FT.INFO comes back with bytes keys/values.
    info = {b"attributes": [[b"identifier", b"user_id", b"type", b"TAG"]]}
    assert redis_client._has_user_id_field(info) is True
    info_without = {b"attributes": [[b"identifier", b"content", b"type", b"TEXT"]]}
    assert redis_client._has_user_id_field(info_without) is False
    assert redis_client._has_user_id_field("not-a-dict") is False
    # Scalar (non-list) attribute entries are handled too.
    assert redis_client._has_user_id_field({"attributes": ["user_id"]}) is True


def test_ensure_index_tolerates_dropindex_error():
    # If dropping the outdated index fails, creation still proceeds.
    class _DropFailsFT(_FakeFT):
        def dropindex(self, delete_documents=False):
            raise redis.exceptions.ResponseError("drop failed")

    client = _FakeClient(exists=True, has_user_id=False)
    client._ft = _DropFailsFT(exists=True, has_user_id=False)
    redis_client.set_redis(client)
    redis_client.ensure_index()
    assert client._ft.created is True
    redis_client.set_redis(None)


def test_ensure_index_swallows_already_exists_on_create():
    # If creation races and reports "Index already exists", treat as success.
    class _RacyFT(_FakeFT):
        def create_index(self, schema, definition=None):
            raise redis.exceptions.ResponseError("Index already exists")

    client = _FakeClient(exists=False)
    client._ft = _RacyFT(exists=False)
    redis_client.set_redis(client)
    redis_client.ensure_index()  # must not raise
    redis_client.set_redis(None)


def test_ensure_index_reraises_other_create_errors():
    class _BrokenFT(_FakeFT):
        def create_index(self, schema, definition=None):
            raise redis.exceptions.ResponseError("some other failure")

    client = _FakeClient(exists=False)
    client._ft = _BrokenFT(exists=False)
    redis_client.set_redis(client)
    try:
        raised = False
        try:
            redis_client.ensure_index()
        except redis.exceptions.ResponseError:
            raised = True
        assert raised is True
    finally:
        redis_client.set_redis(None)
